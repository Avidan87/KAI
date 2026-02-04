"""
KAI Orchestrator

Simplified workflow for food logging: Vision → Knowledge → Save to DB

Chat is now handled separately by ChatAgent.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from kai.agents.vision_agent import VisionAgent
from kai.agents.knowledge_agent import KnowledgeAgent
from kai.models.agent_models import VisionResult, KnowledgeResult
from kai.database import (
    create_user,
    get_user,
    log_meal,
)
from kai.jobs import calculate_and_update_user_stats


logger = logging.getLogger(__name__)


VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


def _infer_meal_type_from_time() -> str:
    """
    Infer meal type based on current time of day.

    Returns:
        'breakfast' (5-11am), 'lunch' (11am-4pm),
        'dinner' (4-9pm), or 'snack' (9pm-5am)
    """
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 16:
        return "lunch"
    elif 16 <= hour < 21:
        return "dinner"
    else:
        return "snack"


def _normalize_meal_type(meal_type: Optional[str]) -> str:
    """
    Normalize and validate meal_type, falling back to time-based inference.

    Args:
        meal_type: Raw meal type from API (could be None, empty, or invalid)

    Returns:
        Valid meal type: 'breakfast', 'lunch', 'dinner', or 'snack'
    """
    if meal_type:
        normalized = meal_type.strip().lower()
        if normalized in VALID_MEAL_TYPES:
            return normalized
    # Fall back to time-based inference
    return _infer_meal_type_from_time()


# ============================================================================
# Singleton Agent Instances
# ============================================================================

_agent_instances = {
    "vision": None,
    "knowledge": None,
}


def _get_agent(agent_type: str):
    """Get or create singleton agent instance."""
    if _agent_instances[agent_type] is None:
        if agent_type == "vision":
            _agent_instances[agent_type] = VisionAgent()
            logger.info("✓ Initialized Vision Agent (GPT-4o)")
        elif agent_type == "knowledge":
            _agent_instances[agent_type] = KnowledgeAgent()
            logger.info("✓ Initialized Knowledge Agent (ChromaDB RAG)")

    return _agent_instances[agent_type]


def _extract_foods_from_vision(vision_result: VisionResult) -> Tuple[List[str], List[float]]:
    """Extract food names and estimated grams from VisionResult."""
    names: List[str] = []
    grams: List[float] = []
    for item in vision_result.detected_foods:
        names.append(item.name)
        grams.append(float(item.estimated_grams) if item.estimated_grams and item.estimated_grams > 0 else 200.0)
    return names, grams


async def handle_user_request(
    user_message: str,
    *,
    image_base64: Optional[str] = None,
    image_url: Optional[str] = None,
    user_id: str = "",
    user_gender: str = "female",
    user_age: int = 25,
    meal_type: Optional[str] = None,
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Food logging orchestrator: Vision → Knowledge → Save to DB

    For chat/conversations, use ChatAgent directly.

    Args:
        meal_type: Optional meal type (breakfast, lunch, dinner, snack).
                   Used for meal-type aware portion estimation.

    Returns dict with:
    - vision: VisionResult
    - nutrition: KnowledgeResult
    - meal_id: saved meal ID
    """
    logger.info(f"🚀 Orchestrator: Food logging for user {user_id}, meal_type={meal_type}")

    # Step 1: Vision - Detect foods from image
    vision = _get_agent("vision")
    vision_result: VisionResult = await asyncio.wait_for(
        vision.analyze_image(
            image_base64=image_base64 or "",
            image_url=image_url,
            meal_type=meal_type,  # Pass meal_type for portion estimation
        ),
        timeout=200.0,
    )
    logger.info(f"   → Detected: {len(vision_result.detected_foods)} foods")

    # Step 2: Knowledge - Retrieve nutrition data
    food_names, portions_grams = _extract_foods_from_vision(vision_result)
    knowledge = _get_agent("knowledge")

    knowledge_result: KnowledgeResult = await asyncio.wait_for(
        knowledge.retrieve_nutrition(food_names=food_names, portions_grams=portions_grams),
        timeout=45.0,
    )
    logger.info(
        f"   → Nutrition: {knowledge_result.total_calories:.0f} cal, "
        f"{knowledge_result.total_protein:.1f}g protein"
    )

    # Step 3: Save meal to database
    meal_id = None
    if user_id:
        try:
            # Ensure user exists
            user = await get_user(user_id)
            if not user:
                logger.info(f"   → Creating new user: {user_id}")
                await create_user(
                    user_id=user_id,
                    gender=user_gender,
                    age=user_age
                )

            # Prepare foods for database - ALL 16 NUTRIENTS
            foods_for_db = []
            for food in knowledge_result.foods:
                nutrients = food.total_nutrients
                foods_for_db.append({
                    "food_name": food.name,
                    "food_id": food.food_id,
                    "portion_grams": food.portion_consumed_grams,
                    # Macros (5)
                    "calories": nutrients.calories,
                    "protein": nutrients.protein,
                    "carbohydrates": nutrients.carbohydrates,
                    "fat": nutrients.fat,
                    "fiber": nutrients.fiber,
                    # Minerals (6)
                    "iron": nutrients.iron,
                    "calcium": nutrients.calcium,
                    "zinc": nutrients.zinc,
                    "potassium": nutrients.potassium,
                    "sodium": nutrients.sodium,
                    "magnesium": nutrients.magnesium,
                    # Vitamins (5)
                    "vitamin_a": nutrients.vitamin_a,
                    "vitamin_c": nutrients.vitamin_c,
                    "vitamin_d": nutrients.vitamin_d,
                    "vitamin_b12": nutrients.vitamin_b12,
                    "folate": nutrients.folate,
                    "confidence": food.similarity_score,
                })

            # Log meal with validated meal_type (normalizes and falls back to time-based)
            actual_meal_type = _normalize_meal_type(meal_type)
            meal_record = await log_meal(
                user_id=user_id,
                meal_type=actual_meal_type,
                foods=foods_for_db,
                image_url=image_url,
            )
            meal_id = meal_record['meal_id']
            logger.info(f"   → Saved meal: {meal_id}")

            # Update user stats (async, don't wait)
            asyncio.create_task(calculate_and_update_user_stats(user_id))

        except Exception as db_error:
            logger.error(f"Database error: {db_error}")

    return {
        "workflow": "food_logging",
        "vision": vision_result,
        "nutrition": knowledge_result,
        "meal_id": meal_id,
    }


def handle_user_request_sync(**kwargs: Any) -> Dict[str, Any]:
    """Synchronous wrapper."""
    return asyncio.run(handle_user_request(**kwargs))
