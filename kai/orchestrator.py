"""
KAI Orchestrator

Simplified workflow for food logging: Vision → Knowledge → Save to DB

Chat is now handled separately by ChatAgent.
"""

import asyncio
import logging
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
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Food logging orchestrator: Vision → Knowledge → Save to DB

    For chat/conversations, use ChatAgent directly.

    Returns dict with:
    - vision: VisionResult
    - nutrition: KnowledgeResult
    - meal_id: saved meal ID
    """
    logger.info(f"🚀 Orchestrator: Food logging for user {user_id}")

    # Step 1: Vision - Detect foods from image
    vision = _get_agent("vision")
    vision_result: VisionResult = await asyncio.wait_for(
        vision.analyze_image(
            image_base64=image_base64 or "",
            image_url=image_url,
            meal_type=None,
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

            # Prepare foods for database
            foods_for_db = []
            for food in knowledge_result.foods:
                foods_for_db.append({
                    "food_name": food.name,
                    "food_id": food.food_id,
                    "portion_grams": food.portion_consumed_grams,
                    "calories": food.total_nutrients.calories,
                    "protein": food.total_nutrients.protein,
                    "carbohydrates": food.total_nutrients.carbohydrates,
                    "fat": food.total_nutrients.fat,
                    "iron": food.total_nutrients.iron,
                    "calcium": food.total_nutrients.calcium,
                    "potassium": food.total_nutrients.potassium,
                    "zinc": food.total_nutrients.zinc,
                    "confidence": food.similarity_score,
                })

            # Log meal
            meal_record = await log_meal(
                user_id=user_id,
                meal_type="lunch",  # Could be inferred from time of day
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
