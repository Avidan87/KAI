"""
KAI Orchestrator

Async workflow coordinator for triage → vision → knowledge → coaching.

Notes:
- Uses async agents updated in kai/agents with @function_tool decorator
- Runs vision first (needed to determine foods) then knowledge
- Coaching optionally enriches with Tavily MCP per CoachingAgent
- Reuses agent instances across requests for efficiency
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from kai.agents.triage_agent import TriageAgent
from kai.agents.vision_agent import VisionAgent
from kai.agents.knowledge_agent import KnowledgeAgent
from kai.agents.coaching_agent import CoachingAgent
from kai.models.agent_models import VisionResult, KnowledgeResult, CoachingResult
from kai.database import (
    create_user,
    get_user,
    get_user_health_profile,
    log_meal,
    get_daily_nutrition_totals,
)
from kai.jobs import calculate_and_update_user_stats


logger = logging.getLogger(__name__)


# ============================================================================
# Singleton Agent Instances (reused across requests for efficiency)
# ============================================================================

_agent_instances = {
    "triage": None,
    "vision": None,
    "knowledge": None,
    "coaching": None,
}


def _get_agent(agent_type: str):
    """Get or create singleton agent instance."""
    if _agent_instances[agent_type] is None:
        if agent_type == "triage":
            _agent_instances[agent_type] = TriageAgent()
            logger.info("✓ Initialized Triage Agent")
        elif agent_type == "vision":
            _agent_instances[agent_type] = VisionAgent()
            logger.info("✓ Initialized Vision Agent (GPT-4o)")
        elif agent_type == "knowledge":
            _agent_instances[agent_type] = KnowledgeAgent()
            logger.info("✓ Initialized Knowledge Agent (ChromaDB RAG)")
        elif agent_type == "coaching":
            _agent_instances[agent_type] = CoachingAgent()
            logger.info("✓ Initialized Coaching Agent (GPT-4o + Tavily MCP)")

    return _agent_instances[agent_type]


def _extract_foods_from_vision(vision_result: VisionResult) -> Tuple[List[str], List[float]]:
    """Extract food names and estimated grams from VisionResult.

    Falls back to 200g if grams are missing/non-positive.
    """
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
    """Main orchestrator entrypoint.

    Coordinates the multi-agent workflow based on triage decision.
    Uses singleton agent instances for efficiency.

    Returns a dict with workflow-specific fields.
    """
    logger.info(f"🚀 Orchestrator: Processing request for user {user_id}")
    has_image = bool(image_base64 or image_url)

    # Step 1: Triage - Route request to appropriate workflow
    triage = _get_agent("triage")
    triage_result = await asyncio.wait_for(
        triage.analyze_request(user_message=user_message, has_image=has_image, conversation_history=conversation_history),
        timeout=30.0,  # Increased from 15s to handle network latency and API response time
    )
    logger.info(f"   → Workflow: {triage_result.workflow} (confidence: {triage_result.confidence:.2f})")

    if triage_result.workflow == "food_logging":
        # Full Pipeline: Vision → Knowledge → Coaching
        logger.info("   Pipeline: Vision → Knowledge → Coaching")

        # Step 2: Vision - Detect foods from image
        vision = _get_agent("vision")
        vision_result: VisionResult = await asyncio.wait_for(
            vision.analyze_image(
                image_base64=image_base64 or "",
                image_url=image_url,
                meal_type=None,
            ),
            timeout=150.0,  # Extended timeout: MiDaS depth estimation can take 60-90s
        )
        logger.info(f"   → Detected: {len(vision_result.detected_foods)} foods")

        # Step 3: Knowledge - Retrieve nutrition data
        food_names, portions_grams = _extract_foods_from_vision(vision_result)
        knowledge = _get_agent("knowledge")

        # If we have a user_id, we can concurrently check user existence while RAG runs
        user_task = None
        if user_id:
            user_task = asyncio.create_task(get_user(user_id))

        knowledge_result: KnowledgeResult = await asyncio.wait_for(
            knowledge.retrieve_nutrition(food_names=food_names, portions_grams=portions_grams),
            timeout=45.0,
        )
        logger.info(
            f"   → Nutrition: {knowledge_result.total_calories:.0f} cal, "
            f"{knowledge_result.total_protein:.1f}g protein, "
            f"{knowledge_result.total_iron:.1f}mg iron"
        )

        # Step 4: Save meal to database
        if user_id:
            try:
                # Ensure user exists (use concurrent result if available)
                user = await user_task if user_task else None
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
                        "vitamin_a": food.total_nutrients.vitamin_a,
                        "zinc": food.total_nutrients.zinc,
                        "confidence": food.similarity_score,
                    })

                # Log meal to database
                meal_record = await log_meal(
                    user_id=user_id,
                    meal_type="lunch",  # Could be inferred from time of day
                    foods=foods_for_db,
                    image_url=image_url,
                )
                logger.info(f"   → Saved meal to database: {meal_record['meal_id']}")

                # Update user stats (calculate weekly averages, trends, streaks)
                # This MUST happen after meal logging so coaching has latest stats
                try:
                    updated_stats = await calculate_and_update_user_stats(user_id)
                    logger.info(f"   → Updated user stats: {updated_stats.get('total_meals_logged', 0)} meals, {updated_stats.get('current_logging_streak', 0)} day streak")
                except Exception as stats_error:
                    logger.error(f"Stats update error (non-fatal): {stats_error}")

                # Fetch daily totals and health profile concurrently
                daily_totals_task = asyncio.create_task(get_daily_nutrition_totals(user_id))
                health_profile_task = asyncio.create_task(get_user_health_profile(user_id))
                daily_totals, health_profile = await asyncio.gather(daily_totals_task, health_profile_task)

            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                # Continue without database (don't fail the request)
                daily_totals = None
                health_profile = None
        else:
            daily_totals = None
            health_profile = None

        # Step 5: Coaching - Generate personalized guidance
        coaching = _get_agent("coaching")

        # Build user context with health profile if available
        # NOTE: New coaching agent uses user_id to fetch stats, RDV, and history
        user_context = {
            "budget": "mid",  # Could be from user profile
            "activity_level": "moderate",  # Could be from user profile
            "use_web_research": True,
            "vision_foods": [df.name for df in vision_result.detected_foods],
        }

        # NEW SIGNATURE: provide_coaching(user_id, knowledge_result, user_context, workflow_type)
        coaching_result: CoachingResult = await asyncio.wait_for(
            coaching.provide_coaching(
                user_id=user_id,
                knowledge_result=knowledge_result,
                user_context=user_context,
                workflow_type="food_logging"
            ),
            timeout=45.0,
        )
        logger.info(f"   → Coaching: {len(coaching_result.nutrient_insights)} insights generated")

        response = {
            "workflow": "food_logging",
            "detected_foods": [df.name for df in vision_result.detected_foods],
            "vision": vision_result,
            "nutrition": knowledge_result,
            "coaching": coaching_result,
        }

        # Add daily totals if available
        if daily_totals:
            response["daily_totals"] = daily_totals

        return response

    elif triage_result.workflow == "nutrition_query":
        # Nutrition Query: Knowledge + Coaching (no vision needed)
        logger.info("   Pipeline: Knowledge + Coaching")

        # If triage extracted food names, use Knowledge Agent
        if triage_result.extracted_food_names:
            knowledge = _get_agent("knowledge")
            # Estimate typical portion (250g)
            portions = [250.0] * len(triage_result.extracted_food_names)
            knowledge_result: KnowledgeResult = await asyncio.wait_for(
                knowledge.retrieve_nutrition(
                    food_names=triage_result.extracted_food_names,
                    portions_grams=portions
                ),
                timeout=30.0,
            )
        else:
            # No specific foods, create empty result with all 8 nutrients
            knowledge_result = KnowledgeResult(
                foods=[],
                total_calories=0.0,
                total_protein=0.0,
                total_carbohydrates=0.0,
                total_fat=0.0,
                total_iron=0.0,
                total_calcium=0.0,
                total_vitamin_a=0.0,
                total_zinc=0.0,
                query_interpretation=user_message,
                sources_used=[],
            )

        # Pass to coaching for answer formatting
        # NOTE: For nutrition queries, we need user_id for personalized coaching
        coaching = _get_agent("coaching")

        # Create user context dict that will be modified by coaching agent
        user_ctx = {
            "use_web_research": True,
            "budget": "mid",
            "activity_level": "moderate",
            "user_question": user_message  # Pass user's question for Tavily query
        }

        if user_id:
            # Personalized coaching with user stats
            coaching_result: CoachingResult = await coaching.provide_coaching(
                user_id=user_id,
                knowledge_result=knowledge_result,
                user_context=user_ctx,
                workflow_type="nutrition_query"
            )
        else:
            # Fallback: Use deprecated method without user_id
            logger.warning("No user_id provided for nutrition_query - using deprecated coaching")
            coaching_result: CoachingResult = await coaching.provide_coaching(
                user_id="anonymous",  # Use anonymous user_id
                knowledge_result=knowledge_result,
                user_context=user_ctx,
                workflow_type="nutrition_query"
            )

        # Extract tavily_used flag from user_context (set by coaching agent)
        tavily_used = user_ctx.get("tavily_used", False)

        return {
            "workflow": "nutrition_query",
            "nutrition": knowledge_result,
            "coaching": coaching_result,
            "tavily_used": tavily_used,
        }

    else:
        # Health Coaching or General Chat: Coaching only
        logger.info("   Pipeline: Coaching")

        coaching = _get_agent("coaching")
        workflow = triage_result.workflow  # "health_coaching" or "general_chat"

        # Create user context dict that will be modified by coaching agent
        user_ctx = {
            "use_web_research": True,
            "budget": "mid",
            "activity_level": "moderate",
            "user_question": user_message  # Pass user's question for Tavily query
        }

        if user_id:
            # Personalized coaching with user stats
            coaching_result: CoachingResult = await coaching.provide_coaching(
                user_id=user_id,
                knowledge_result=KnowledgeResult(
                    foods=[],
                    total_calories=0.0,
                    total_protein=0.0,
                    total_carbohydrates=0.0,
                    total_fat=0.0,
                    total_iron=0.0,
                    total_calcium=0.0,
                    total_vitamin_a=0.0,
                    total_zinc=0.0,
                    query_interpretation=user_message,
                    sources_used=[],
                ),
                user_context=user_ctx,
                workflow_type=workflow
            )
        else:
            # Fallback: Use anonymous user
            logger.warning("No user_id provided for general chat - using anonymous coaching")
            coaching_result: CoachingResult = await coaching.provide_coaching(
                user_id="anonymous",
                knowledge_result=KnowledgeResult(
                    foods=[],
                    total_calories=0.0,
                    total_protein=0.0,
                    total_carbohydrates=0.0,
                    total_fat=0.0,
                    total_iron=0.0,
                    total_calcium=0.0,
                    total_vitamin_a=0.0,
                    total_zinc=0.0,
                    query_interpretation=user_message,
                    sources_used=[],
                ),
                user_context=user_ctx,
                workflow_type=workflow
            )

        # Extract tavily_used flag from user_context (set by coaching agent)
        tavily_used = user_ctx.get("tavily_used", False)

        return {
            "workflow": triage_result.workflow,
            "coaching": coaching_result,
            "tavily_used": tavily_used,
        }


def handle_user_request_sync(**kwargs: Any) -> Dict[str, Any]:
    """Synchronous wrapper for environments without async entrypoint."""
    return asyncio.run(handle_user_request(**kwargs))


