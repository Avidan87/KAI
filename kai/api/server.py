"""
FastAPI server for KAI

Endpoints (v1):
Auth:
- POST /api/v1/auth/signup              # Sign up new user, get JWT token
- POST /api/v1/auth/login               # Login existing user, get JWT token

Chat:
- POST /api/v1/chat                     # Chat with KAI (nutrition questions, progress, feedback)

Food Logging:
- POST /api/v1/food-logging-upload      # Vision → Knowledge → Save (returns facts, feedback in chat)

Meals:
- GET  /api/v1/meals/history            # Get meal history (user_id from JWT)

Users:
- GET  /api/v1/users/profile            # Get user profile + health + RDV (user_id from JWT)
- PUT  /api/v1/users/health-profile     # Update health profile with BMR/TDEE calculations
- GET  /api/v1/users/nutrition-plan     # Get goal-driven nutrition plan with priority nutrients
- GET  /api/v1/users/stats              # Get daily nutrition stats (user_id from JWT)
"""

import os
import time
import uuid
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import base64

logger = logging.getLogger(__name__)

from kai.models.agent_models import (
    ChatRequest,
    ChatResponse,
    FoodLoggingResponse,
    KnowledgeResult,
    MealHistoryResponse,
    UserProfileResponse,
    UserStatsResponse,
)
from kai.agents.chat_agent import get_chat_agent
from kai.orchestrator import handle_user_request
from kai.auth import create_access_token, get_current_user_id
from kai.database import (
    initialize_database,
    get_user,
    create_user,
    get_user_by_email,
    update_user_health,
    get_user_health_profile,
    get_user_meals,
    get_daily_nutrition_totals,
)
from kai.services.railway_keepalive import start_keepalive, stop_keepalive
from kai.services import get_priority_nutrients, get_priority_rdvs, get_nutrient_emoji, get_goal_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    await initialize_database()
    print("✅ Database initialized")

    # Start Railway keepalive service (prevents 60-90s cold starts)
    start_keepalive()
    print("✅ Railway keepalive service started")

    yield

    # Shutdown
    stop_keepalive()
    print("✅ Railway keepalive service stopped")


app = FastAPI(
    title="KAI Nutrition Intelligence API",
    description="Nigerian nutrition coaching with AI-powered agents",
    version="2.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}  # Keep auth token in Swagger
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "KAI Backend", "version": "2.0.0"}


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/v1/auth/signup")
async def signup(
    email: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    age: int = Form(...)
):
    """
    Sign up new user and return JWT token.

    All fields are required for signup. Health profile (weight, height, activity, goals)
    can be completed later via /api/v1/users/health-profile endpoint.
    """
    user_id = str(uuid.uuid4())  # Generate UUID as user_id

    # Validate name
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required and cannot be empty")

    # Validate and normalize gender
    gender_normalized = gender.lower().strip()
    if gender_normalized not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    # Validate age
    if age < 13 or age > 120:
        raise HTTPException(status_code=400, detail="Age must be between 13 and 120")

    try:
        # Create user in database
        user = await create_user(
            user_id=user_id,
            email=email,
            name=name,
            gender=gender_normalized,
            age=age
        )
        
        # Create JWT token with user_id
        access_token = create_access_token(data={"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "user": user
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/login")
async def login(email: str = Form(...)):
    """Login existing user and return JWT token"""
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    access_token = create_access_token(data={"sub": user["user_id"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["user_id"]
    }


# ============================================================================
# Chat Endpoints
# ============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Chat with KAI - your Nigerian nutrition assistant.

    Use for:
    - Nutrition questions ("What foods are high in iron?")
    - Progress checks ("How am I doing today?")
    - Meal feedback ("How was my last meal?")
    - General health questions
    """
    start = time.time()
    try:
        chat_agent = get_chat_agent()

        result = await chat_agent.chat(
            user_id=user_id,
            message=request.message,
            conversation_history=request.conversation_history,
        )

        return ChatResponse(
            success=result.get("success", True),
            message=result.get("message", ""),
            suggestions=result.get("suggestions", []),
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        logger.error(f"❌ Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ============================================================================
# Food Logging Endpoints
# ============================================================================

@app.post("/api/v1/food-logging-upload", response_model=FoodLoggingResponse)
async def food_logging_upload(
    image: UploadFile = File(...),
    user_description: str = Form(None),
    meal_type: str = Form(None),  # Optional: breakfast, lunch, dinner, snack
    user_id: str = Depends(get_current_user_id),
):
    """
    Food logging with image upload.

    Pipeline: Vision → Knowledge → Save to DB
    Returns nutrition facts only. For feedback, use /chat endpoint.

    Args:
        meal_type: Optional meal type (breakfast, lunch, dinner, snack).
                   If not provided, will be inferred from time of day.
                   Used for more accurate portion estimation.
    """
    start = time.time()
    try:
        # Read image and convert to base64
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        result = await handle_user_request(
            user_message=user_description or "Analyze this food",
            image_base64=image_base64,
            image_url=None,
            user_id=user_id,
            meal_type=meal_type,  # Pass meal_type for portion estimation
            conversation_history=[],
        )

        knowledge: KnowledgeResult | None = result.get("nutrition")

        # Get user's health goal for goal-driven nutrient tracking
        profile = await get_user_health_profile(user_id)
        health_goal = profile.get("health_goals", "general_wellness") if profile else "general_wellness"
        gender = profile.get("gender") if profile else None
        age = profile.get("age") if profile else None
        custom_calorie_goal = profile.get("custom_calorie_goal") if profile else None

        # Get goal context - single source of truth for goal-driven nutrition
        goal_context = get_goal_context(health_goal, gender, age, custom_calorie_goal)

        # Extract only PRIORITY NUTRIENTS for this goal
        def get_nutrient(name: str) -> float:
            attr_name = f"total_{name}" if not name.startswith("total_") else name
            return getattr(knowledge, attr_name, 0.0) if knowledge else 0.0

        # Build priority nutrients dict with only goal-relevant nutrients (6-8)
        priority_nutrients = {}
        for nutrient in goal_context["priority_nutrients"]:
            priority_nutrients[nutrient] = get_nutrient(nutrient)

        return FoodLoggingResponse(
            success=True,
            message="Meal logged! Ask me in chat for feedback.",
            detected_foods=result.get("vision").detected_foods if result.get("vision") else [],
            priority_nutrients=priority_nutrients,
            meal_id=result.get("meal_id"),
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"❌ Food logging failed: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Food logging failed: {str(e)}")


# ============================================================================
# Meal Endpoints
# ============================================================================

@app.get("/api/v1/meals/history", response_model=MealHistoryResponse)
async def get_meal_history(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Get user's meal history"""
    start = time.time()
    try:
        meals = await get_user_meals(user_id=user_id, limit=limit, offset=offset)

        return MealHistoryResponse(
            success=True,
            message=f"Retrieved {len(meals)} meals",
            meals=meals,
            total_count=len(meals),
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# User Profile Endpoints
# ============================================================================

@app.get("/api/v1/users/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """
    Get user profile with health info and RDV values.

    Returns profile_complete flag indicating if weight/height/activity/goals are set.
    """
    start = time.time()
    try:
        profile = await get_user_health_profile(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        return UserProfileResponse(
            success=True,
            message="User profile retrieved",
            user_id=profile["user_id"],
            email=profile.get("email"),
            name=profile.get("name"),
            gender=profile["gender"],
            age=profile["age"],
            weight_kg=profile.get("weight_kg"),
            height_cm=profile.get("height_cm"),
            activity_level=profile.get("activity_level"),
            health_goals=profile.get("health_goals"),
            dietary_restrictions=profile.get("dietary_restrictions"),
            target_weight_kg=profile.get("target_weight_kg"),
            calculated_calorie_goal=profile.get("calculated_calorie_goal"),
            custom_calorie_goal=profile.get("custom_calorie_goal"),
            active_calorie_goal=profile.get("active_calorie_goal"),
            profile_complete=profile.get("profile_complete", False),
            rdv=profile["rdv"],
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/users/health-profile")
async def update_health_profile(
    weight_kg: float = Form(..., description="Current weight in kilograms (30-300 kg)"),
    height_cm: float = Form(..., description="Height in centimeters (100-250 cm)"),
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] = Form(
        ...,
        description="Activity level: sedentary (little/no exercise), light (1-3 days/week), moderate (3-5 days/week), active (6-7 days/week), very_active (physical job/athlete)"
    ),
    health_goals: Literal[
        "lose_weight", "gain_muscle", "maintain_weight", "general_wellness",
        "pregnancy", "heart_health", "energy_boost", "bone_health"
    ] = Form(
        ...,
        description="Health goal: lose_weight, gain_muscle, maintain_weight, general_wellness, pregnancy, heart_health, energy_boost, or bone_health"
    ),
    target_weight_kg: float = Form(None, description="Goal weight for weight loss/gain tracking (optional)"),
    custom_calorie_goal: float = Form(None, description="Override KAI's calculated calorie recommendation (optional)"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Complete or update user's health profile for full personalization.

    This endpoint enables BMR/TDEE-based calorie calculations and goal-specific coaching.

    Required fields:
        - weight_kg: Current weight (30-300 kg)
        - height_cm: Height (100-250 cm)
        - activity_level: Select from dropdown (sedentary, light, moderate, active, very_active)
        - health_goals: Select from dropdown (8 options: lose_weight, gain_muscle, maintain_weight, general_wellness, pregnancy, heart_health, energy_boost, bone_health)

    Optional fields:
        - target_weight_kg: Goal weight for weight loss/gain tracking
        - custom_calorie_goal: Override KAI's calculated calorie recommendation
    """
    start = time.time()

    try:
        # Validate required fields
        if not all([weight_kg, height_cm, activity_level, health_goals]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: weight_kg, height_cm, activity_level, health_goals"
            )

        # Validate weight range
        if weight_kg < 30 or weight_kg > 300:
            raise HTTPException(
                status_code=400,
                detail="Weight must be between 30 and 300 kg"
            )

        # Validate height range
        if height_cm < 100 or height_cm > 250:
            raise HTTPException(
                status_code=400,
                detail="Height must be between 100 and 250 cm"
            )

        # Validate activity level
        valid_activity_levels = ["sedentary", "light", "moderate", "active", "very_active"]
        if activity_level not in valid_activity_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_level. Must be one of: {', '.join(valid_activity_levels)}"
            )

        # Validate health goals (all 8 supported goals)
        valid_health_goals = [
            "lose_weight", "gain_muscle", "maintain_weight", "general_wellness",
            "pregnancy", "heart_health", "energy_boost", "bone_health"
        ]
        if health_goals not in valid_health_goals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid health_goals. Must be one of: {', '.join(valid_health_goals)}"
            )

        # Get user profile first (needed for validation and RDV calculation)
        user = await get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found. Please ensure you are logged in with a valid account."
            )

        # Treat 0 as None (user didn't provide custom goal)
        if custom_calorie_goal == 0:
            custom_calorie_goal = None

        # Validate custom calorie goal if provided
        if custom_calorie_goal is not None:
            min_calories = 1200 if user.get("gender") == "female" else 1500

            if custom_calorie_goal < min_calories:
                raise HTTPException(
                    status_code=400,
                    detail=f"Custom calorie goal is dangerously low. Minimum: {min_calories} kcal/day for {user.get('gender')}s. "
                           f"Very low calorie diets should be medically supervised."
                )

            if custom_calorie_goal > 5000:
                raise HTTPException(
                    status_code=400,
                    detail="Custom calorie goal exceeds safe maximum (5000 kcal/day)"
                )

        # Import the new RDV calculation function
        from kai.utils.nutrition_rdv import calculate_user_rdv_v2

        # Build user profile for calculation
        user_profile = {
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "age": user.get("age"),
            "gender": user.get("gender"),
            "activity_level": activity_level,
            "health_goals": health_goals,
            "target_weight_kg": target_weight_kg,
            "custom_calorie_goal": custom_calorie_goal
        }

        # Calculate personalized RDV using BMR/TDEE method
        rdv_result = calculate_user_rdv_v2(user_profile)

        # Update user_health table with new values
        await update_user_health(
            user_id=user_id,
            weight_kg=weight_kg,
            height_cm=height_cm,
            activity_level=activity_level,
            health_goals=health_goals,
            target_weight_kg=target_weight_kg,
            calculated_calorie_goal=rdv_result["recommended_calories"],
            custom_calorie_goal=custom_calorie_goal,
            active_calorie_goal=rdv_result["active_calories"],
        )

        # Build response
        response = {
            "success": True,
            "message": "Health profile updated successfully",
            "profile_complete": True,
            "calculated_rdv": {
                "bmr": rdv_result["bmr"],
                "tdee": rdv_result["tdee"],
                "recommended_calories": rdv_result["recommended_calories"],
                "active_calories": rdv_result["active_calories"]
            },
            "processing_time_ms": int((time.time() - start) * 1000)
        }

        # Add weight projection if available
        if "weight_projection" in rdv_result:
            response["weight_projection"] = rdv_result["weight_projection"]

        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating health profile: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/users/nutrition-plan")
async def get_nutrition_plan(
    user_id: str = Depends(get_current_user_id),
):
    """
    Get the user's personalized nutrition plan based on their health goal.

    Returns the priority nutrients (6-8) for the user's goal with:
    - Emoji for visual display
    - Daily target value
    - Personalized explanation of why this nutrient matters

    Call this after completing health profile to show the user their plan.
    """
    start = time.time()

    try:
        # Get user profile
        profile = await get_user_health_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        # Check if profile is complete
        if not profile.get("profile_complete", False):
            raise HTTPException(
                status_code=400,
                detail="Health profile not complete. Please update your health profile first."
            )

        health_goal = profile.get("health_goals")
        gender = profile.get("gender")
        age = profile.get("age")
        custom_calorie_goal = profile.get("custom_calorie_goal")

        # Get priority nutrients for this goal
        priority_nutrients = get_priority_nutrients(health_goal)
        priority_rdvs = get_priority_rdvs(
            health_goal,
            gender=gender,
            age=age,
            custom_calorie_goal=custom_calorie_goal
        )

        # Goal-specific explanations for WHY each nutrient matters
        nutrient_explanations = {
            "lose_weight": {
                "calories": "Track to maintain your calorie deficit",
                "protein": "Keeps you full & preserves muscle while losing fat",
                "fiber": "Increases satiety and supports gut health",
                "carbohydrates": "Manage for steady energy balance",
                "fat": "Essential but controlled for deficit",
                "sodium": "Reduce water retention and bloating",
            },
            "gain_muscle": {
                "calories": "Fuel your gains with a calorie surplus",
                "protein": "Builds and repairs muscle tissue",
                "carbohydrates": "Powers your workouts and recovery",
                "fat": "Supports hormone production for growth",
                "zinc": "Essential for protein synthesis and testosterone",
                "magnesium": "Muscle function and recovery",
                "vitamin_b12": "Energy metabolism and red blood cells",
            },
            "maintain_weight": {
                "calories": "Maintain energy balance",
                "protein": "Preserve your muscle mass",
                "carbohydrates": "Sustained daily energy",
                "fat": "Essential fatty acids for health",
                "fiber": "Digestive health and satiety",
                "iron": "Energy and vitality",
            },
            "general_wellness": {
                "calories": "Overall energy balance",
                "protein": "Body maintenance and repair",
                "fiber": "Gut health and digestion",
                "iron": "Energy and immune function",
                "vitamin_c": "Immunity and antioxidant protection",
                "calcium": "Bone and muscle function",
            },
            "pregnancy": {
                "calories": "Support growing baby (+300 kcal/day)",
                "protein": "Fetal tissue growth",
                "folate": "CRITICAL for neural tube development",
                "iron": "Prevent anemia, support blood volume",
                "calcium": "Baby's bone development",
                "vitamin_d": "Calcium absorption and immunity",
                "zinc": "Cell division and immune function",
                "vitamin_b12": "Neurological development",
            },
            "heart_health": {
                "calories": "Maintain healthy weight",
                "sodium": "Blood pressure control (limit intake)",
                "potassium": "Balances sodium for BP health",
                "fiber": "Cholesterol management",
                "fat": "Limit saturated fats",
                "magnesium": "Heart rhythm and blood pressure",
                "vitamin_c": "Vascular health and antioxidant",
            },
            "energy_boost": {
                "calories": "Adequate energy intake",
                "iron": "Oxygen transport, prevents fatigue",
                "vitamin_b12": "Energy metabolism",
                "carbohydrates": "Primary energy source",
                "magnesium": "ATP energy production",
                "vitamin_c": "Enhances iron absorption",
            },
            "bone_health": {
                "calories": "Maintain healthy weight for bones",
                "calcium": "Primary bone mineral",
                "vitamin_d": "Calcium absorption",
                "protein": "Bone matrix structure",
                "magnesium": "Bone mineral structure",
                "zinc": "Bone formation enzymes",
                "potassium": "Reduces calcium loss",
            },
        }

        goal_explanations = nutrient_explanations.get(
            health_goal,
            nutrient_explanations["general_wellness"]
        )

        # Build nutrient list with emojis
        nutrients = []
        for nutrient in priority_nutrients:
            rdv_obj = priority_rdvs.get(nutrient)
            if rdv_obj:
                nutrients.append({
                    "name": nutrient,
                    "display_name": rdv_obj.display_name,
                    "emoji": get_nutrient_emoji(nutrient),
                    "daily_target": rdv_obj.amount,
                    "unit": rdv_obj.unit,
                    "why": goal_explanations.get(nutrient, "Important for your goal"),
                })

        return {
            "success": True,
            "message": "Nutrition plan retrieved",
            "goal": health_goal,
            "nutrient_count": len(nutrients),
            "nutrients": nutrients,
            "processing_time_ms": int((time.time() - start) * 1000)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nutrition plan: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/users/stats", response_model=UserStatsResponse)
async def get_user_stats(
    date: str = None,
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Get user's daily nutrition statistics"""
    start = time.time()
    try:
        from datetime import datetime as dt

        # Get daily totals
        daily_totals = await get_daily_nutrition_totals(user_id, date)

        if not daily_totals:
            # Return empty stats if no data
            return UserStatsResponse(
                success=True,
                message="No meals logged for this date",
                user_id=user_id,
                date=date or dt.today().date().isoformat(),
                daily_totals=None,
                rdv_percentages={},
                meal_count=0,
                processing_time_ms=int((time.time() - start) * 1000),
            )

        # Get user profile for RDV calculation
        profile = await get_user_health_profile(user_id)
        rdv = profile["rdv"]

        # Calculate percentages
        rdv_percentages = {
            "calories": (daily_totals["total_calories"] / rdv["calories"]) * 100 if rdv["calories"] > 0 else 0,
            "protein": (daily_totals["total_protein"] / rdv["protein"]) * 100 if rdv["protein"] > 0 else 0,
            "iron": (daily_totals["total_iron"] / rdv["iron"]) * 100 if rdv["iron"] > 0 else 0,
            "calcium": (daily_totals["total_calcium"] / rdv["calcium"]) * 100 if rdv["calcium"] > 0 else 0,
        }

        return UserStatsResponse(
            success=True,
            message="User statistics retrieved",
            user_id=user_id,
            date=daily_totals["date"],
            daily_totals=daily_totals,
            rdv_percentages=rdv_percentages,
            meal_count=daily_totals["meal_count"],
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "kai.api.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )


