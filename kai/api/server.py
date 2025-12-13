"""
FastAPI server for KAI

Endpoints (v1):
Auth:
- POST /api/v1/auth/signup              # Sign up new user, get JWT token
- POST /api/v1/auth/login               # Login existing user, get JWT token

Food Logging:
- POST /api/v1/food-logging-upload      # Full pipeline: Vision → Knowledge → Coaching (FILE UPLOAD)

Chat:
- POST /api/v1/chat                     # Chat with Coaching Agent

Meals:
- POST /api/v1/meals/log                # Save meal to database
- GET  /api/v1/meals/history            # Get meal history (user_id from JWT)

Users:
- GET  /api/v1/users/profile             # Get user profile + health + RDV (user_id from JWT)
- PUT  /api/v1/users/profile             # Update user profile (user_id from JWT)
- GET  /api/v1/users/stats               # Get daily nutrition stats (user_id from JWT)
"""

import time
import uuid
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import base64

logger = logging.getLogger(__name__)

from kai.models.agent_models import (
    FoodLoggingResponse,
    ChatRequest,
    ChatResponse,
    KnowledgeResult,
    LogMealRequest,
    LogMealResponse,
    MealHistoryResponse,
    UserProfileResponse,
    UpdateUserProfileRequest,
    UserStatsResponse,
)
from kai.orchestrator import handle_user_request
from kai.auth import create_access_token, get_current_user_id
from kai.database import (
    initialize_database,
    get_user,
    create_user,
    get_user_by_email,
    update_user,
    update_user_health,
    get_user_health_profile,
    log_meal as db_log_meal,
    get_user_meals,
    get_daily_nutrition_totals,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    await initialize_database()
    print("✅ Database initialized")
    yield
    # Shutdown (if needed, add cleanup code here)
    # For example: await close_database_connections()


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
    name: str = Form(None),
    gender: str = Form("female"),
    age: int = Form(25)
):
    """Sign up new user and return JWT token"""
    user_id = str(uuid.uuid4())  # Generate UUID as user_id

    # Validate and normalize gender
    gender_normalized = gender.lower().strip() if gender else "female"
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
# Food Logging Endpoints
# ============================================================================

@app.post("/api/v1/food-logging-upload", response_model=FoodLoggingResponse)
async def food_logging_upload(
    image: UploadFile = File(...),
    user_description: str = Form(None),
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Food logging with direct file upload (Full pipeline: Vision → Knowledge → Coaching)"""
    start = time.time()
    try:
        # Read image file and convert to base64
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        result = await handle_user_request(
            user_message=user_description or "Analyze this food",
            image_base64=image_base64,
            image_url=None,
            user_id=user_id,
            conversation_history=[],
        )

        knowledge: KnowledgeResult | None = result.get("nutrition")

        # Extract ALL 8 NUTRIENTS from knowledge result
        total_calories = getattr(knowledge, "total_calories", 0.0) if knowledge else 0.0
        total_protein = getattr(knowledge, "total_protein", 0.0) if knowledge else 0.0
        total_carbohydrates = getattr(knowledge, "total_carbohydrates", 0.0) if knowledge else 0.0
        total_fat = getattr(knowledge, "total_fat", 0.0) if knowledge else 0.0
        total_iron = getattr(knowledge, "total_iron", 0.0) if knowledge else 0.0
        total_calcium = getattr(knowledge, "total_calcium", 0.0) if knowledge else 0.0
        total_vitamin_a = getattr(knowledge, "total_vitamin_a", 0.0) if knowledge else 0.0
        total_zinc = getattr(knowledge, "total_zinc", 0.0) if knowledge else 0.0

        return FoodLoggingResponse(
            success=True,
            message="Meal analyzed",
            detected_foods=result.get("vision").detected_foods if result.get("vision") else [],
            nutrition_data=knowledge,
            coaching=result.get("coaching"),
            midas_used=result.get('vision').midas_used if result.get('vision') else False,
            # Return ALL 8 nutrients
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbohydrates=total_carbohydrates,
            total_fat=total_fat,
            total_iron=total_iron,
            total_calcium=total_calcium,
            total_vitamin_a=total_vitamin_a,
            total_zinc=total_zinc,
            processing_time_ms=int((time.time() - start) * 1000),
            workflow_path=result.get("workflow", "food_logging"),
        )
    except Exception as e:
        # Log full error traceback for debugging
        error_traceback = traceback.format_exc()
        logger.error(f"❌ Food logging upload failed: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Food logging failed: {str(e)}")


# ============================================================================
# Chat Endpoints
# ============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Chat with Coaching Agent"""
    start = time.time()
    try:
        result = await handle_user_request(
            user_message=request.message,
            image_base64=None,
            image_url=None,
            user_id=user_id,  # Use JWT user_id instead of request.user_id
            conversation_history=request.conversation_history,
        )

        coaching = result.get("coaching")
        knowledge = result.get("nutrition")
        message = getattr(coaching, "personalized_message", "") if coaching else ""
        suggestions = getattr(coaching, "next_steps", []) if coaching else []

        # Get sources from knowledge result if available
        sources = []
        if knowledge:
            sources = getattr(knowledge, "sources_used", [])

        # Get Tavily sources from orchestrator result and merge with knowledge sources
        tavily_sources = result.get("tavily_sources", [])
        if tavily_sources:
            sources = sources + tavily_sources  # Merge both source lists

        # Get tavily_used flag from orchestrator result
        tavily_used = result.get("tavily_used", False)

        return ChatResponse(
            success=True,
            message=message,
            nutrition_data=knowledge,  # ✅ Include full nutrition data!
            coaching=coaching,  # ✅ Include full coaching data!
            sources=sources,  # ✅ Include sources!
            follow_up_suggestions=suggestions,
            processing_time_ms=int((time.time() - start) * 1000),
            workflow_path=result.get("workflow", "general_chat"),  # ✅ Show workflow!
            tavily_used=tavily_used,  # ✅ Track if Tavily was used!
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Meal Endpoints
# ============================================================================

@app.post("/api/v1/meals/log", response_model=LogMealResponse)
async def log_meal(
    request: LogMealRequest,
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Save a meal to the database"""
    start = time.time()
    try:
        # Ensure user exists
        user = await get_user(user_id)
        if not user:
            # Create user if doesn't exist
            await create_user(user_id=user_id)

        # Save meal to database
        meal_result = await db_log_meal(
            user_id=user_id,
            meal_type=request.meal_type,
            foods=request.foods,
            meal_date=request.meal_date,
            image_url=request.image_url,
            user_description=request.user_description,
        )

        # Get updated daily totals
        daily_totals = await get_daily_nutrition_totals(user_id)

        return LogMealResponse(
            success=True,
            message="Meal logged successfully",
            meal_id=meal_result["meal_id"],
            meal_date=meal_result["meal_date"],
            meal_time=meal_result["meal_time"],
            foods_count=meal_result["foods_count"],
            totals=meal_result["totals"],
            daily_totals=daily_totals,
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """Get user profile with health info and RDV values"""
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
            is_pregnant=profile["is_pregnant"],
            is_lactating=profile["is_lactating"],
            has_anemia=profile["has_anemia"],
            weight_kg=profile.get("weight_kg"),
            height_cm=profile.get("height_cm"),
            activity_level=profile.get("activity_level"),
            health_goals=profile.get("health_goals"),
            dietary_restrictions=profile.get("dietary_restrictions"),
            rdv=profile["rdv"],
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/users/profile", response_model=UserProfileResponse)
async def update_user_profile_endpoint(
    request: UpdateUserProfileRequest,
    user_id: str = Depends(get_current_user_id),  # Extract from JWT token
):
    """Update user profile and health information"""
    start = time.time()
    try:
        # Update user basic info
        if any([request.email, request.name, request.gender, request.age]):
            await update_user(
                user_id=user_id,
                email=request.email,
                name=request.name,
                gender=request.gender,
                age=request.age,
            )

        # Update health info
        if any([
            request.is_pregnant is not None,
            request.is_lactating is not None,
            request.has_anemia is not None,
            request.weight_kg,
            request.height_cm,
            request.activity_level,
            request.health_goals,
            request.dietary_restrictions,
        ]):
            await update_user_health(
                user_id=user_id,
                is_pregnant=request.is_pregnant,
                is_lactating=request.is_lactating,
                has_anemia=request.has_anemia,
                weight_kg=request.weight_kg,
                height_cm=request.height_cm,
                activity_level=request.activity_level,
                health_goals=request.health_goals,
                dietary_restrictions=request.dietary_restrictions,
            )

        # Return updated profile
        profile = await get_user_health_profile(user_id)

        return UserProfileResponse(
            success=True,
            message="User profile updated",
            user_id=profile["user_id"],
            email=profile.get("email"),
            name=profile.get("name"),
            gender=profile["gender"],
            age=profile["age"],
            is_pregnant=profile["is_pregnant"],
            is_lactating=profile["is_lactating"],
            has_anemia=profile["has_anemia"],
            weight_kg=profile.get("weight_kg"),
            height_cm=profile.get("height_cm"),
            activity_level=profile.get("activity_level"),
            health_goals=profile.get("health_goals"),
            dietary_restrictions=profile.get("dietary_restrictions"),
            rdv=profile["rdv"],
            processing_time_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
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

    uvicorn.run(
        "kai.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


