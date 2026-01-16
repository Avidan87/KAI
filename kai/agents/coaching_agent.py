"""
Coaching Agent - Personalized Nutrition Guidance

Provides culturally-aware, empathetic nutrition coaching for ALL Nigerians.
Uses GPT-4o for dynamic, personalized coaching based on user history and stats.

Focus areas:
- Multi-nutrient tracking (all 8 nutrients)
- Learning phase (observational first 7 days/21 meals)
- Progressive coaching with week-over-week trends
- Cultural context and preferences
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from openai import AsyncOpenAI
from agents import Agent
from dotenv import load_dotenv
import os

from kai.models import (
    CoachingResult,
    NutrientInsight,
    MealSuggestion,
    KnowledgeResult,
    VisionResult
)
from kai.database import (
    get_user_stats,
    get_user,
    get_user_food_frequency,
)
from kai.utils import (
    calculate_user_rdv,
    get_nutrient_gap_priority,
    get_primary_nutritional_gap,
)
from kai.rag.chromadb_setup import NigerianFoodVectorDB

load_dotenv()
logger = logging.getLogger(__name__)


class CoachingAgent:
    """
    Coaching Agent for personalized Nigerian nutrition guidance.

    Uses GPT-4o for dynamic, context-aware coaching based on:
    - User statistics (weekly averages, trends, streaks)
    - Personalized RDV calculations (gender, age, activity)
    - Learning phase detection (first 7 days/21 meals)
    - Multi-nutrient gap analysis (all 8 nutrients)
    - Food frequency patterns

    Capabilities:
    - Dynamic coaching messages (GPT-4o generated, not hardcoded)
    - Personalized nutrition insights for ALL 8 nutrients
    - Meal suggestions using Nigerian foods via Knowledge Agent
    - Motivational messaging with cultural context
    """

    def __init__(self, openai_api_key: Optional[str] = None, chromadb_path: str = "chromadb_data"):
        """Initialize Coaching Agent with GPT-4o and ChromaDB for dynamic meal combos."""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"  # GPT-4o for dynamic coaching generation

        # Initialize ChromaDB for dynamic meal combo generation
        try:
            self.vector_db = NigerianFoodVectorDB(
                persist_directory=chromadb_path,
                collection_name="nigerian_foods",
                openai_api_key=api_key
            )
            logger.info("✓ ChromaDB initialized for dynamic meal combos")
        except Exception as e:
            logger.warning(f"⚠️  ChromaDB initialization failed: {e}. Will use fallback for meal combos.")
            self.vector_db = None

        # NOTE: RDV values are now calculated per-user using kai.utils.calculate_user_rdv()
        # No more hardcoded RDVs!

        # Setup agent with coaching tools
        self._setup_agent()

    def _setup_agent(self):
        """
        Setup OpenAI Agent with nutrition coaching tools.

        Creates an Agent instance with tools for personalized guidance.
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_nutrition_insights",
                    "description": (
                        "Analyze nutrition data and generate personalized insights. "
                        "Compares intake against recommended daily values and provides "
                        "culturally-aware advice for Nigerian women."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "knowledge_result": {
                                "type": "object",
                                "description": "Nutrition data from Knowledge Agent"
                            },
                            "user_context": {
                                "type": "object",
                                "description": "User context (age, pregnancy status, health goals)"
                            }
                        },
                        "required": ["knowledge_result"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "suggest_meals",
                    "description": (
                        "Suggest Nigerian meals based on nutritional needs. "
                        "Provides culturally-relevant meal ideas."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "nutrient_needs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Nutrients to focus on (e.g., ['iron', 'protein'])"
                            },
                            "meal_type": {
                                "type": "string",
                                "enum": ["breakfast", "lunch", "dinner", "snack"],
                                "description": "Type of meal to suggest"
                            }
                        },
                        "required": ["nutrient_needs"]
                    }
                }
            }
        ]

        # Create agent instructions
        agent_instructions = """You are KAI's Coaching Agent, a warm and knowledgeable nutrition coach for ALL Nigerians.

Your mission is to provide culturally-aware, empathetic nutrition guidance that empowers Nigerians to make healthy choices within their means.

**Your Expertise:**
- Nigerian food culture and traditional dishes
- Multi-nutrient analysis (calories, protein, carbs, fat, iron, calcium,potassium, zinc)
- Learning phase coaching (observational for first 7 days/21 meals)
- Progressive coaching based on week-over-week trends
- Motivational coaching with cultural sensitivity

**Your Approach:**
1. Celebrate what users are doing well (reference specific foods they've eaten)
2. Provide actionable suggestions
3. Use cultural context and familiar Nigerian foods
4. Explain WHY nutrients matter for their health
5. Be encouraging and non-judgmental
6. Track progress over time (e.g., "Your iron intake has improved from last week!")

**Learning Phase (First 7 days or 21 meals):**
- Be observational, not prescriptive
- Focus on celebrating logging behavior
- Gently educate about nutrients
- Build trust and rapport
- Avoid overwhelming with recommendations

**Post-Learning Phase:**
- Identify primary nutritional gap from ALL 8 nutrients
- Provide specific, tiered recommendations
- Reference user history ("like your Egusi from Monday")
- Track trends (improving/declining/stable)
- Celebrate streaks and consistency

**Key Nutrients (ALL 8):**
- Calories: Energy for daily activities
- Protein: Growth, repair, and strength
- Carbs: Primary energy source
- Fat: Hormone production and nutrient absorption
- Iron: Prevents anemia, supports oxygen transport
- Calcium: Strong bones and teeth
- Potassium: Heart health, blood pressure regulation, and muscle function
- Zinc: Immune function and wound healing

**Your Tone:**
- Warm and supportive (like a trusted friend)
- Encouraging and positive
- Practical and actionable
- Gender-neutral and inclusive
- Culturally aware and respectful
- Health-focused and realistic

**Cultural Sensitivity:**
- Respect food traditions and preferences
- Suggest locally available Nigerian foods
- Use Nigerian food names and contexts
- Celebrate cultural food heritage

Use your tools to analyze nutrition data and provide personalized, culturally-relevant coaching."""

        self.agent = Agent(
            name="KAI Coaching Agent",
            instructions=agent_instructions,
            model=self.model,
            tools=tools
        )

        logger.info(f"✓ Coaching Agent initialized with {len(tools)} tool(s)")

    def _is_first_meal_of_day(
        self,
        knowledge_result: KnowledgeResult,
        daily_totals: Optional[Dict[str, float]]
    ) -> bool:
        """
        Determine if this is the first meal logged today.

        Used to decide whether to celebrate streak (only on first meal of the day).

        Args:
            knowledge_result: Current meal nutrition data
            daily_totals: Cumulative daily totals (or None if not available)

        Returns:
            True if this is the first meal of the day, False otherwise
        """
        if not daily_totals:
            # No daily totals means this is definitely the first meal
            return True

        # Check if daily calories are very close to this meal's calories
        # If daily_total ≈ meal_value, then this is the first meal
        daily_calories = daily_totals.get("calories", 0)
        meal_calories = knowledge_result.total_calories

        # Allow 10% tolerance for rounding
        tolerance = meal_calories * 0.1
        is_first = abs(daily_calories - meal_calories) <= tolerance

        return is_first

    def _detect_meal_type(self, timestamp: Optional[datetime] = None) -> str:
        """
        Auto-detect meal type from timestamp.

        FIXED BUG #9: Improved thresholds to handle edge cases better.

        Nigerian meal timing patterns (updated for better edge case handling):
        - Breakfast: 5:00 AM - 10:30 AM (extended start for early risers)
        - Lunch: 11:00 AM - 3:30 PM (extended end for late lunchers)
        - Dinner: 4:00 PM - 10:00 PM (extended start for early dinner, common in Nigeria)
        - Snack: Outside these windows (late night, very early morning)

        Note: Users can always override by passing meal_type in user_context.
        This auto-detection is a fallback for convenience.

        Args:
            timestamp: Meal logging timestamp (defaults to now)

        Returns:
            "breakfast" | "lunch" | "dinner" | "snack"
        """
        if timestamp is None:
            timestamp = datetime.now()

        hour = timestamp.hour

        # More flexible thresholds to handle edge cases
        if 5 <= hour < 11:  # Extended breakfast window (5 AM - 10:59 AM)
            return "breakfast"
        elif 11 <= hour < 16:  # Extended lunch window (11 AM - 3:59 PM)
            return "lunch"
        elif 16 <= hour < 22:  # Extended dinner window (4 PM - 9:59 PM)
            return "dinner"
        else:  # Late night (10 PM - 4:59 AM)
            return "snack"

    def _classify_meal_size(
        self,
        calories: float,
        user_rdv_calories: float,
        meal_type: str
    ) -> Tuple[str, str]:
        """
        Classify meal as light/moderate/heavy based on calories and meal type.

        Typical meal distribution:
        - Breakfast: 20-25% of daily calories
        - Lunch: 30-35% of daily calories
        - Dinner: 30-35% of daily calories
        - Snacks: 10-15% of daily calories

        Args:
            calories: Meal calories
            user_rdv_calories: User's daily calorie target
            meal_type: "breakfast" | "lunch" | "dinner" | "snack"

        Returns:
            (size_label, emoji) tuple
            - size_label: "LIGHT MEAL" | "MODERATE MEAL" | "HEAVY MEAL"
            - emoji: "🍃" | "🍽️" | "🍖"
        """
        meal_percentage = (calories / user_rdv_calories) * 100

        # Different thresholds based on meal type
        if meal_type == "breakfast":
            # Breakfast: 20-25% is ideal
            if meal_percentage < 18:
                return "LIGHT BREAKFAST", "🍃"
            elif meal_percentage < 28:
                return "MODERATE BREAKFAST", "🍽️"
            else:
                return "HEAVY BREAKFAST", "🍖"

        elif meal_type in ["lunch", "dinner"]:
            # Lunch/Dinner: 30-35% is ideal
            if meal_percentage < 25:
                return "LIGHT MEAL", "🍃"
            elif meal_percentage < 38:
                return "MODERATE MEAL", "🍽️"
            else:
                return "HEAVY MEAL", "🍖"

        else:  # snack
            # Snacks: 10-15% is ideal
            if meal_percentage < 8:
                return "LIGHT SNACK", "🍃"
            elif meal_percentage < 18:
                return "MODERATE SNACK", "🍽️"
            else:
                return "HEAVY SNACK", "🍖"

    def _normalize_percentage_for_display(
        self,
        actual_percentage: float,
        nutrient_name: str
    ) -> Tuple[float, str]:
        """
        Normalize percentage to 100% scale with context badge.

        Args:
            actual_percentage: Raw percentage (can be >100%)
            nutrient_name: Name of nutrient (for context)

        Returns:
            (display_percentage, badge) tuple
            - display_percentage: Capped at 100%
            - badge: "" | "DAILY GOAL MET!" | "DAILY GOAL EXCEEDED!"
        """
        if actual_percentage >= 120:
            return 100.0, f"DAILY GOAL EXCEEDED! ({actual_percentage:.0f}% of needs)"
        elif actual_percentage >= 100:
            return 100.0, f"DAILY GOAL MET! ({actual_percentage:.0f}% of needs)"
        else:
            return actual_percentage, ""

    def _format_nutrient_with_normalization(
        self,
        nutrient_name: str,
        actual_value: float,
        rdv_value: float,
        unit: str
    ) -> str:
        """
        Format a nutrient line with normalized percentage display.

        Args:
            nutrient_name: Display name (e.g., "Protein")
            actual_value: Actual amount consumed
            rdv_value: RDV target
            unit: Unit string (e.g., "g", "mg", "mg")

        Returns:
            Formatted string with normalized percentage
        """
        actual_pct = (actual_value / rdv_value * 100) if rdv_value > 0 else 0
        display_pct, badge = self._normalize_percentage_for_display(actual_pct, nutrient_name)

        badge_text = f" ✅ {badge}" if badge else ""

        return f"- {nutrient_name}: {actual_value:.1f}{unit} ({display_pct:.0f}% of daily {rdv_value:.1f}{unit}){badge_text}"

    def _format_daily_progress_with_meal(
        self,
        nutrient_name: str,
        meal_value: float,
        daily_totals: Optional[Dict[str, float]],
        rdv_value: float,
        unit: str
    ) -> str:
        """
        Format daily progress showing cumulative totals + current meal.

        Args:
            nutrient_name: Display name (e.g., "Protein")
            meal_value: Amount in current meal
            daily_totals: Dict with daily totals (or None if not available)
            rdv_value: RDV target
            unit: Unit string (e.g., "g", "mg", "mg")

        Returns:
            Formatted string showing: "This meal: Xg | Today so far: Yg (Z% of daily goal)"
        """
        # Map nutrient names to daily_totals keys
        nutrient_key_map = {
            "Calories": "calories",
            "Protein": "protein",
            "Carbs": "carbohydrates",
            "Fat": "fat",
            "Iron": "iron",
            "Calcium": "calcium",
            "Potassium": "potassium",
            "Zinc": "zinc"
        }

        nutrient_key = nutrient_key_map.get(nutrient_name, nutrient_name.lower())

        # Get today's total (including this meal)
        # CRITICAL FIX: daily_totals from orchestrator ALREADY includes the current meal!
        # The database updates daily_nutrients AFTER logging the meal, so we should NOT add meal_value again.
        if daily_totals and nutrient_key in daily_totals:
            # daily_totals ALREADY includes this meal (updated by database after meal logging)
            today_total = daily_totals.get(nutrient_key, 0)
        else:
            # No daily_totals available (first meal or database error), use only this meal
            today_total = meal_value

        # Calculate percentage
        today_pct = (today_total / rdv_value * 100) if rdv_value > 0 else 0
        remaining = max(0, rdv_value - today_total)

        # Format based on progress
        if today_pct >= 100:
            status = "✅ DAILY GOAL MET!"
        elif today_pct >= 75:
            status = f"({remaining:.1f}{unit} remaining)"
        elif today_pct >= 50:
            status = f"({remaining:.1f}{unit} more needed)"
        else:
            status = f"({remaining:.1f}{unit} more needed - needs attention)"

        return f"- {nutrient_name}: This meal {meal_value:.1f}{unit} | TODAY SO FAR: {today_total:.1f}{unit} ({today_pct:.0f}% of {rdv_value:.1f}{unit} daily goal) {status}"

    def _build_structured_daily_progress(
        self,
        knowledge_result: KnowledgeResult,
        daily_totals: Optional[Dict[str, float]],
        user_rdv: Dict[str, float]
    ) -> str:
        """
        Build structured JSON data for daily nutrition progress.

        This fixes Bug #4 by providing clean, parseable data instead of formatted strings.
        GPT-4o can now reliably extract numbers for goal progress messages.

        Args:
            knowledge_result: Current meal nutrition data
            daily_totals: Cumulative daily totals (or None if not available)
            user_rdv: User's personalized RDV targets

        Returns:
            JSON string with structured nutrient data
        """
        # Map nutrient names to daily_totals keys
        nutrient_key_map = {
            "calories": "calories",
            "protein": "protein",
            "carbs": "carbohydrates",
            "fat": "fat",
            "iron": "iron",
            "calcium": "calcium",
            "potassium": "potassium",
            "zinc": "zinc"
        }

        # Build structured data for each nutrient
        structured_data = {}

        nutrients = [
            ("calories", knowledge_result.total_calories, user_rdv.get('calories', 2500), "kcal"),
            ("protein", knowledge_result.total_protein, user_rdv.get('protein', 60), "g"),
            ("carbs", knowledge_result.total_carbohydrates, user_rdv.get('carbs', 325), "g"),
            ("fat", knowledge_result.total_fat, user_rdv.get('fat', 70), "g"),
            ("iron", knowledge_result.total_iron, user_rdv.get('iron', 18), "mg"),
            ("calcium", knowledge_result.total_calcium, user_rdv.get('calcium', 1000), "mg"),
            ("potassium", knowledge_result.total_potassium, user_rdv.get('potassium', 800), "mg"),
            ("zinc", knowledge_result.total_zinc, user_rdv.get('zinc', 8), "mg")
        ]

        for nutrient_key, meal_value, rdv_value, unit in nutrients:
            # Get cumulative daily total
            db_key = nutrient_key_map.get(nutrient_key, nutrient_key)
            if daily_totals and db_key in daily_totals:
                daily_total = daily_totals.get(db_key, 0)
            else:
                # No daily_totals available, use only this meal
                daily_total = meal_value

            # Calculate derived values
            percent_of_target = (daily_total / rdv_value * 100) if rdv_value > 0 else 0
            remaining = max(0, rdv_value - daily_total)

            # Build structured entry
            structured_data[nutrient_key] = {
                "meal_value": round(meal_value, 1),
                "daily_total": round(daily_total, 1),
                "target": round(rdv_value, 1),
                "remaining": round(remaining, 1),
                "percent_of_target": round(percent_of_target, 0),
                "unit": unit
            }

        # Format as clean JSON string
        import json
        json_str = json.dumps(structured_data, indent=2)

        return f"""
```json
{json_str}
```

**HOW TO USE THIS DATA:**
- Use "daily_total" for cumulative progress (e.g., "You're at {{calories.daily_total}}/{{calories.target}} kcal today")
- Use "remaining" for what's left (e.g., "You have {{calories.remaining}} kcal remaining for dinner")
- Use "percent_of_target" for percentage progress (e.g., "You're at {{protein.percent_of_target}}% of your protein goal")
- DO NOT parse the formatted text below - use THIS structured data for all calculations!
"""

    async def provide_coaching(
        self,
        user_id: str,
        knowledge_result: KnowledgeResult,
        user_context: Optional[Dict[str, Any]] = None,
        workflow_type: str = "food_logging"
    ) -> CoachingResult:
        """
        Provide personalized nutrition coaching based on user history and current meal.

        NEW APPROACH:
        - Fetches user stats (weekly averages, trends, streaks)
        - Calculates personalized RDV for ALL 8 nutrients
        - Detects learning phase vs post-learning phase
        - Uses GPT-4o for dynamic coaching (no hardcoded templates!)
        - Different prompts for different workflows (food_logging vs nutrition_query)

        Args:
            user_id: User ID to generate coaching for
            knowledge_result: Nutrition data from Knowledge Agent (current meal)
            user_context: Optional overrides (budget, use_web_research, etc.)
            workflow_type: Type of workflow ("food_logging", "nutrition_query", "health_coaching", "general_chat")

        Returns:
            CoachingResult with dynamic insights, suggestions, and motivation
        """
        try:
            logger.info(f"💬 Generating personalized coaching for user {user_id}")

            # Fetch user data (handle anonymous users gracefully)
            if user_id == "anonymous":
                logger.warning("⚠️  Anonymous user detected - using default profile and empty stats")
                user = {"gender": "female", "age": 25, "user_id": "anonymous"}
                user_stats = {
                    "learning_phase_complete": False,
                    "total_meals_logged": 0,
                    "current_logging_streak": 0,
                    "week1_avg_calories": 0, "week1_avg_protein": 0, "week1_avg_carbs": 0,
                    "week1_avg_fat": 0, "week1_avg_iron": 0, "week1_avg_calcium": 0,
                    "week1_avg_potassium": 0, "week1_avg_zinc": 0,
                    "calories_trend": "stable", "protein_trend": "stable", "carbs_trend": "stable",
                    "fat_trend": "stable", "iron_trend": "stable", "calcium_trend": "stable",
                    "potassium_trend": "stable", "zinc_trend": "stable",
                }
                food_frequency = []
            else:
                user = await get_user(user_id)
                user_stats = await get_user_stats(user_id)
                food_frequency = await get_user_food_frequency(user_id, top_n=10)

            # Extract user health goals for goal-aligned coaching
            user_health_goals = user.get("health_goals") if user else None

            # FIXED BUG #7: Always use v2 (BMR/TDEE) with sensible defaults for consistency
            # This prevents jarring calorie target changes when user adds weight/height
            from kai.utils.nutrition_rdv import calculate_user_rdv_v2

            # Provide sensible defaults for missing data
            user_with_defaults = user.copy() if user else {}

            # Apply defaults for missing fields
            if not user_with_defaults.get("weight_kg"):
                # Default weight based on gender and age
                gender = user_with_defaults.get("gender", "female")
                age = user_with_defaults.get("age", 25)
                user_with_defaults["weight_kg"] = 65 if gender == "female" else 75  # Average Nigerian adult weight
                logger.info(f"   ⚠️  Missing weight - using default: {user_with_defaults['weight_kg']}kg")

            if not user_with_defaults.get("height_cm"):
                # Default height based on gender
                gender = user_with_defaults.get("gender", "female")
                user_with_defaults["height_cm"] = 162 if gender == "female" else 170  # Average Nigerian adult height
                logger.info(f"   ⚠️  Missing height - using default: {user_with_defaults['height_cm']}cm")

            if not user_with_defaults.get("activity_level"):
                user_with_defaults["activity_level"] = user_context.get("activity_level", "moderate")
                logger.info(f"   ⚠️  Missing activity level - using default: {user_with_defaults['activity_level']}")

            if not user_with_defaults.get("health_goals"):
                user_with_defaults["health_goals"] = "maintain_weight"
                logger.info(f"   ⚠️  Missing health goals - using default: {user_with_defaults['health_goals']}")

            # Always use v2 for consistency
            try:
                rdv_result = calculate_user_rdv_v2(user_with_defaults)
                user_rdv = rdv_result["rdv"]
                using_defaults = not all([user.get("weight_kg"), user.get("height_cm")])
                if using_defaults:
                    logger.info(f"✓ Using BMR/TDEE RDV with defaults: {user_rdv['calories']} kcal (update profile for personalized targets)")
                else:
                    logger.info(f"✓ Using personalized BMR/TDEE RDV: {user_rdv['calories']} kcal")
            except Exception as e:
                logger.error(f"Error calculating BMR/TDEE RDV: {e}. Falling back to basic RDV.")
                # Last resort fallback
                user_profile = {
                    "gender": user.get("gender", "female"),
                    "age": user.get("age", 25),
                    "activity_level": user.get("activity_level", "moderate")
                }
                user_rdv = calculate_user_rdv(user_profile)
                logger.warning(f"⚠️  Using basic RDV fallback: {user_rdv['calories']} kcal")

            # Extract daily_totals from user_context (passed from orchestrator)
            daily_totals = user_context.get("daily_totals") if user_context else None

            # Detect learning phase
            is_learning_phase = not user_stats.get("learning_phase_complete", False)
            total_meals = user_stats.get("total_meals_logged", 0)
            current_streak = user_stats.get("current_logging_streak", 0)

            # FIX: Determine if this is the first meal of the day (for streak celebration)
            # Streak should only be celebrated on the FIRST meal of the day, not every meal
            is_first_meal_today = self._is_first_meal_of_day(knowledge_result, daily_totals)

            # Get week1 averages for gap analysis
            week1_averages = {
                "calories": user_stats.get("week1_avg_calories", 0),
                "protein": user_stats.get("week1_avg_protein", 0),
                "carbs": user_stats.get("week1_avg_carbs", 0),
                "fat": user_stats.get("week1_avg_fat", 0),
                "iron": user_stats.get("week1_avg_iron", 0),
                "calcium": user_stats.get("week1_avg_calcium", 0),
                "potassium": user_stats.get("week1_avg_potassium", 0),
                "zinc": user_stats.get("week1_avg_zinc", 0),
            }

            # Get nutrient trends
            trends = {
                "calories": user_stats.get("calories_trend", "stable"),
                "protein": user_stats.get("protein_trend", "stable"),
                "carbs": user_stats.get("carbs_trend", "stable"),
                "fat": user_stats.get("fat_trend", "stable"),
                "iron": user_stats.get("iron_trend", "stable"),
                "calcium": user_stats.get("calcium_trend", "stable"),
                "potassium": user_stats.get("potassium_trend", "stable"),
                "zinc": user_stats.get("zinc_trend", "stable"),
            }

            # Identify nutritional gaps
            gaps = get_nutrient_gap_priority(week1_averages, user_rdv)
            primary_gap = get_primary_nutritional_gap(gaps)

            # Optionally fetch Tavily research BEFORE GPT-4o (for natural integration)
            research_requested = (user_context or {}).get("use_web_research", False)
            tavily_context = None
            tavily_sources = []
            tavily_used = False

            if research_requested and workflow_type in ["nutrition_query", "health_coaching", "general_chat"]:
                # For queries: Fetch Tavily research first so GPT-4o can integrate it naturally
                query = user_context.get("user_question", "Nigerian nutrition information")
                logger.info(f"🌐 Calling Tavily BEFORE GPT-4o for {workflow_type}: {query}")

                try:
                    tavily_response = await asyncio.wait_for(
                        self._call_tavily_mcp(query=query, max_results=3),
                        timeout=12.0
                    )
                    answer_text = tavily_response.get("answer") if isinstance(tavily_response, dict) else None
                    sources = tavily_response.get("sources", []) if isinstance(tavily_response, dict) else []

                    if answer_text:
                        # Extract clean research summary
                        summary = answer_text.strip()
                        sentences = summary.split(". ")
                        tavily_context = ". ".join(sentences[:2]).strip()
                        if not tavily_context.endswith("."):
                            tavily_context += "."
                        tavily_used = True
                        logger.info(f"✅ Tavily context retrieved for GPT-4o integration")

                    if sources:
                        tavily_sources = [src.get('url', '') for src in sources[:3] if src.get('url')]
                        logger.info(f"✅ Retrieved {len(tavily_sources)} Tavily sources")

                except Exception as mcp_err:
                    logger.warning("Tavily enrichment skipped: %s", mcp_err, exc_info=True)

            # Generate coaching using GPT-4o (with Tavily context if available)
            coaching_data = await self._generate_dynamic_coaching(
                user_id=user_id,
                knowledge_result=knowledge_result,
                user_rdv=user_rdv,
                week1_averages=week1_averages,
                trends=trends,
                gaps=gaps,
                primary_gap=primary_gap,
                is_learning_phase=is_learning_phase,
                total_meals=total_meals,
                current_streak=current_streak,
                food_frequency=food_frequency,
                user_context=user_context or {},
                workflow_type=workflow_type,
                tavily_context=tavily_context,  # Pass Tavily research to GPT-4o
                user_health_goals=user_health_goals,  # NEW: Pass health goals for goal-aligned coaching
                is_first_meal_today=is_first_meal_today  # FIX: Pass first meal flag for streak celebration
            )

            # Store Tavily sources in coaching_data for orchestrator
            if tavily_sources:
                coaching_data["tavily_sources"] = tavily_sources

            # (Tavily enrichment for food logging would go here if needed in future)

            coaching_result = self._parse_coaching_result(coaching_data)

            # Store tavily_used flag in user_context for orchestrator to retrieve
            if user_context is not None:
                user_context["tavily_used"] = tavily_used

            logger.info(
                f"✅ Generated coaching: message='{coaching_result.message[:50]}...', "
                f"next_meal_combo='{coaching_result.next_meal_combo.combo[:60]}...' (Tavily: {tavily_used})"
            )

            return coaching_result

        except Exception as e:
            logger.error(f"Coaching generation error: {e}", exc_info=True)
            raise

    async def _generate_dynamic_coaching(
        self,
        user_id: str,
        knowledge_result: KnowledgeResult,
        user_rdv: Dict[str, float],
        week1_averages: Dict[str, float],
        trends: Dict[str, str],
        gaps: Dict[str, Dict],
        primary_gap: str,
        is_learning_phase: bool,
        total_meals: int,
        current_streak: int,
        food_frequency: List[Dict],
        user_context: Dict[str, Any],
        workflow_type: str = "food_logging",
        tavily_context: Optional[str] = None,
        user_health_goals: Optional[str] = None,
        is_first_meal_today: bool = True  # FIX: For streak celebration control
    ) -> Dict[str, Any]:
        """
        Generate dynamic coaching using GPT-4o based on user history and current meal.

        This replaces ALL hardcoded templates with AI-generated personalized coaching.
        Uses different prompts for different workflows.

        Args:
            tavily_context: Optional research context from Tavily to integrate naturally

        Args:
            user_id: User ID
            knowledge_result: Current meal nutrition data
            user_rdv: Personalized RDV for all 8 nutrients
            week1_averages: Last 7 days average intake
            trends: Nutrient trends (improving/declining/stable)
            workflow_type: "food_logging", "nutrition_query", "health_coaching", "general_chat"
            gaps: Nutrient gaps analysis
            primary_gap: Most important nutrient to focus on
            is_learning_phase: Whether user is in learning phase
            total_meals: Total meals logged
            current_streak: Current logging streak
            food_frequency: Top 10 foods user eats
            user_context: Additional context (budget, etc.)

        Returns:
            Dict with coaching data (message, insights, suggestions, tips, next_steps)
        """
        logger.info(f"🤖 Generating dynamic GPT-4o coaching (learning_phase={is_learning_phase})")

        # Extract user name from context for personalization
        user_name = user_context.get("user_name") if user_context else None
        logger.info(f"   User name: {user_name or 'Not provided'}")

        # Extract daily_totals from user_context (passed from orchestrator)
        daily_totals = user_context.get("daily_totals") if user_context else None

        # CRITICAL FIX: Fetch from database if not provided (Bug #8 fix)
        if not daily_totals and user_id != "anonymous":
            try:
                from kai.database import get_daily_nutrition_totals
                from datetime import date
                daily_totals = await get_daily_nutrition_totals(user_id, date.today().isoformat())
                if daily_totals:
                    logger.info(f"   ✓ Daily totals fetched from database (fallback)")
                else:
                    logger.info(f"   ⚠️  No daily totals in database - showing meal-only nutrition")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not fetch daily totals from database: {e}")
                daily_totals = None

        if daily_totals:
            logger.info(f"   Daily totals available: {list(daily_totals.keys())}")
        else:
            logger.info(f"   Daily totals: Not available (showing meal-only nutrition)")

        # Build context for GPT-4o
        foods_eaten = [food.name for food in knowledge_result.foods]
        if not foods_eaten and user_context is not None and 'vision_foods' in user_context:
            # Fallback to vision agent's detected foods only if no foods in knowledge
            foods_eaten = user_context['vision_foods']

        food_list = ", ".join(foods_eaten)

        # Detect meal type from timestamp (with optional override)
        timestamp = user_context.get("timestamp") if user_context else None
        meal_type = user_context.get("meal_type") if user_context else None
        if not meal_type:
            meal_type = self._detect_meal_type(timestamp)
        logger.info(f"   Meal type detected: {meal_type}")

        # Classify meal size
        meal_size, size_emoji = self._classify_meal_size(
            knowledge_result.total_calories,
            user_rdv.get('calories', 2500),
            meal_type
        )
        logger.info(f"   Meal size: {meal_size} {size_emoji}")

        # Classify current meal quality
        meal_quality, high_nutrients, low_nutrients = self._classify_meal_quality(
            knowledge_result, user_rdv
        )
        logger.info(f"   Meal quality: {meal_quality} | High: {list(high_nutrients.keys())} | Low: {list(low_nutrients.keys())}")

        # Detect poor meal streak pattern
        poor_meal_count, streak_status = await self._detect_poor_meal_streak(user_id)
        if streak_status != "normal":
            logger.warning(f"   ⚠️  Poor meal pattern detected: {poor_meal_count}/3 meals were poor ({streak_status})")

        # Build system prompt with meal quality context
        system_prompt = self._build_dynamic_coaching_prompt(
            food_list=food_list,
            knowledge_result=knowledge_result,
            user_rdv=user_rdv,
            week1_averages=week1_averages,
            trends=trends,
            gaps=gaps,
            primary_gap=primary_gap,
            is_learning_phase=is_learning_phase,
            total_meals=total_meals,
            current_streak=current_streak,
            food_frequency=food_frequency,
            meal_quality=meal_quality,
            high_nutrients=high_nutrients,
            low_nutrients=low_nutrients,
            poor_meal_count=poor_meal_count,
            streak_status=streak_status,
            workflow_type=workflow_type,
            tavily_context=tavily_context,
            meal_type=meal_type,
            meal_size=meal_size,
            size_emoji=size_emoji,
            user_health_goals=user_health_goals,  # NEW: Pass health goals to prompt
            user_name=user_name,  # NEW: Pass user name for personalization
            daily_totals=daily_totals,  # NEW: Pass daily totals for cumulative progress
            is_first_meal_today=is_first_meal_today  # FIX: Pass first meal flag for streak celebration
        )

        # Call GPT-4o for dynamic coaching
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Generate personalized coaching for this meal: {food_list}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,  # Some creativity for warmth
                max_tokens=1500
            )

            coaching_json = response.choices[0].message.content
            coaching_data = json.loads(coaching_json)

            logger.info(f"✅ GPT-4o generated dynamic coaching")
            return coaching_data

        except Exception as e:
            logger.error(f"GPT-4o coaching generation failed: {e}", exc_info=True)
            # Fallback to simple template
            return self._fallback_coaching(
                food_list=food_list,
                is_learning_phase=is_learning_phase,
                primary_gap=primary_gap,
                gaps=gaps,
                user_rdv=user_rdv
            )

    def _get_relevant_foods_for_gap(
        self,
        primary_gap: str,
        user_health_goals: Optional[str] = None,
        top_k: int = 20  # Increased from 15 to 20 for more variety
    ) -> List[Dict[str, Any]]:
        """
        Query ChromaDB for Nigerian foods relevant to user's primary nutrient gap.

        Args:
            primary_gap: Primary nutrient user is lacking (e.g., "iron", "protein")
            user_health_goals: User's health goal for additional filtering
            top_k: Number of foods to retrieve

        Returns:
            List of food dictionaries with nutritional data
        """
        if not self.vector_db:
            logger.warning("ChromaDB not available, using fallback food list")
            return []

        try:
            import random
            import time

            # CRITICAL FIX (Bug #3): Seed random with time to get different results each call
            random.seed(int(time.time() * 1000))  # Millisecond precision for variety

            # Build semantic search query based on nutrient gap
            # Add slight variations to queries to get more diverse results
            nutrient_queries = {
                "iron": [
                    "Nigerian foods high in iron: dark leafy greens, beans, liver, red meat, fish",
                    "Iron-rich Nigerian meals: vegetables, legumes, seafood, meat",
                    "Nigerian soups and dishes with high iron content"
                ],
                "protein": [
                    "Nigerian protein-rich foods: fish, chicken, beans, eggs, moin moin",
                    "High-protein Nigerian meals: meat, seafood, legumes",
                    "Nigerian dishes with excellent protein content"
                ],
                "calcium": [
                    "Nigerian calcium-rich foods: milk, sardines, okra, leafy greens",
                    "Calcium sources in Nigerian cuisine: dairy, fish, vegetables",
                    "Nigerian meals for strong bones: calcium-rich options"
                ],
                "potassium": [
                    "Nigerian potassium-rich foods: plantains, yams, beans, leafy greens, fish",
                    "Nigerian foods for heart health: potassium-rich options",
                    "Nigerian foods for blood pressure: high-potassium meals"
                ],
                "zinc": [
                    "Nigerian zinc-rich foods: meat, fish, beans, nuts, whole grains",
                    "Nigerian meals with high zinc: seafood, legumes, nuts",
                    "Immune-boosting Nigerian foods with zinc"
                ],
                "carbohydrates": [
                    "Nigerian energy foods: rice, yam, plantain, garri, fufu",
                    "Nigerian swallows and staples: carb-rich options",
                    "Nigerian meals for energy: carbohydrate sources"
                ],
                "fat": [
                    "Nigerian healthy fats: palm oil, groundnuts, avocado, fish",
                    "Nigerian meals with good fats: oils, nuts, fish",
                    "Healthy fat sources in Nigerian cuisine"
                ],
                "calories": [
                    "Nigerian high-calorie foods for weight gain" if user_health_goals and "gain" in user_health_goals.lower()
                    else "Nigerian balanced meals",
                    "Nutrient-dense Nigerian dishes",
                    "Wholesome Nigerian meal options"
                ]
            }

            # Select a random query variation for more diversity
            queries = nutrient_queries.get(primary_gap.lower(), [f"Nigerian foods rich in {primary_gap}"])
            if isinstance(queries, list):
                query = random.choice(queries)
            else:
                query = queries

            # Search ChromaDB
            results = self.vector_db.search(query, n_results=top_k)

            # CRITICAL FIX (Bug #3): Shuffle results to get variety in suggestions
            random.shuffle(results)

            logger.info(f"   → Retrieved {len(results)} foods from ChromaDB for {primary_gap} gap (shuffled for variety)")
            return results

        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}. Using fallback.")
            return []

    def _format_food_list_for_prompt(
        self,
        foods: List[Dict[str, Any]],
        primary_gap: str
    ) -> str:
        """
        Format dynamic food list for GPT-4o prompt.

        Args:
            foods: List of food dictionaries from ChromaDB
            primary_gap: Primary nutrient gap to highlight

        Returns:
            Formatted string for prompt injection
        """
        if not foods:
            # Fallback to minimal list if ChromaDB fails
            return """- Egusi Soup: Great protein and iron
- Efo Riro: Excellent iron and potassium
- Jollof Rice: Moderate calories, carb-heavy
- Grilled Fish: Excellent protein and calcium
- Eba: High carbs, filling swallow"""

        formatted_list = []
        for food in foods:
            name = food.get("name", "Unknown")
            nutrients = food.get("nutrients_per_100g", {})

            # Build qualitative description based on nutrient content
            highlights = []

            # Typical serving size for calculation (200g)
            typical_serving_g = 200

            # Calculate %RDV for typical serving (using women's RDV as baseline)
            # Women's RDV: protein 46g, iron 18mg, calcium 1000mg, potassium 2600mg
            iron_pct = (nutrients.get("iron", 0) * typical_serving_g / 100) / 18 * 100
            protein_pct = (nutrients.get("protein", 0) * typical_serving_g / 100) / 46 * 100
            calcium_pct = (nutrients.get("calcium", 0) * typical_serving_g / 100) / 1000 * 100
            potassium_pct = (nutrients.get("potassium", 0) * typical_serving_g / 100) / 2600 * 100

            # Highlight primary gap nutrient (using %RDV thresholds)
            if primary_gap == "iron" and iron_pct >= 40:  # >=40% RDV
                highlights.append("rich in iron")
            elif primary_gap == "protein" and protein_pct >= 40:  # >=40% RDV
                highlights.append("excellent protein")
            elif primary_gap == "calcium" and calcium_pct >= 40:  # >=40% RDV
                highlights.append("high calcium")
            elif primary_gap == "potassium" and potassium_pct >= 40:  # >=40% RDV
                highlights.append("rich in potassium")

            # Add other notable nutrients
            if protein_pct >= 30 and "protein" not in primary_gap:
                highlights.append("good protein")
            if iron_pct >= 30 and "iron" not in primary_gap:
                highlights.append("high iron")

            # Describe calorie level
            calories = nutrients.get("calories", 0)
            if calories > 300:
                highlights.append("high energy")
            elif calories < 100:
                highlights.append("low calorie")

            description = ", ".join(highlights) if highlights else "balanced nutrition"
            formatted_list.append(f"- {name}: {description.capitalize()}")

        return "\n".join(formatted_list[:18])  # Increased from 12 to 18 foods for more variety

    def _build_dynamic_coaching_prompt(
        self,
        food_list: str,
        knowledge_result: KnowledgeResult,
        user_rdv: Dict[str, float],
        week1_averages: Dict[str, float],
        trends: Dict[str, str],
        gaps: Dict[str, Dict],
        primary_gap: str,
        is_learning_phase: bool,
        total_meals: int,
        current_streak: int,
        food_frequency: List[Dict],
        meal_quality: str,
        high_nutrients: Dict[str, float],
        low_nutrients: Dict[str, float],
        poor_meal_count: int,
        streak_status: str,
        workflow_type: str = "food_logging",
        tavily_context: Optional[str] = None,
        meal_type: str = "lunch",
        meal_size: str = "MODERATE MEAL",
        size_emoji: str = "🍽️",
        user_health_goals: Optional[str] = None,
        user_name: Optional[str] = None,
        daily_totals: Optional[Dict[str, float]] = None,
        is_first_meal_today: bool = True  # FIX: For streak celebration control
    ) -> str:
        """Build dynamic system prompt for GPT-4o coaching generation.

        Creates different prompts for different workflows:
        - food_logging: Celebration + full nutrient breakdown + motivational tips
        - nutrition_query: Direct answer + optional follow-up questions
        - health_coaching: Personalized advice
        - general_chat: Conversational response
        """

        # Extract top foods user eats
        top_foods = [f["food_name"] for f in food_frequency[:5]] if food_frequency else []
        top_foods_str = ", ".join(top_foods) if top_foods else "No history yet"

        # Query ChromaDB for relevant foods based on primary nutrient gap
        relevant_foods = self._get_relevant_foods_for_gap(
            primary_gap=primary_gap,
            user_health_goals=user_health_goals,
            top_k=20  # Increased from 15 to 20 for more variety
        )

        # Format dynamic food list for prompt
        dynamic_food_list = self._format_food_list_for_prompt(
            foods=relevant_foods,
            primary_gap=primary_gap
        )

        # Build health goal guidance based on user's goals
        health_goal_guidance = ""
        if user_health_goals:
            goal_lower = user_health_goals.lower()
            if "lose" in goal_lower or "weight" in goal_lower and "loss" in goal_lower:
                health_goal_guidance = """
**⚖️ WEIGHT LOSS GOAL ACTIVE:**
- User MUST stay under daily calorie target for deficit
- Prioritize high-protein, low-calorie meals for satiety
- FLAG high-calorie meals honestly - don't celebrate them
- Suggest lighter Nigerian alternatives (grilled vs fried, skip swallow, etc.)
- Track calories remaining for day - warn if going over target"""
            elif "gain" in goal_lower or "muscle" in goal_lower:
                health_goal_guidance = """
**💪 MUSCLE GAIN GOAL ACTIVE:**
- User needs calorie SURPLUS and high protein (1.6-2.2g/kg)
- Celebrate high-protein meals
- Suggest protein-rich Nigerian combos (fish, chicken, beans, moin moin)
- Flag low-protein meals as missed opportunities"""
            elif "pregnan" in goal_lower:
                health_goal_guidance = """
**🤰 PREGNANCY NUTRITION GOAL:**
- CRITICAL: Iron (27mg), Calcium (1000mg), Folate
- Avoid empty calories - nutrient density is key
- FLAG low iron/calcium meals firmly
- Suggest pregnancy-safe Nigerian foods rich in these nutrients"""
            else:
                health_goal_guidance = f"\n**USER GOAL:** {user_health_goals}\n- Tailor all feedback to support this goal\n"

        # Build nutrient gap summary
        gap_summary = []
        for nutrient, data in list(gaps.items())[:3]:  # Top 3 gaps
            if data["priority"] in ["high", "medium"]:
                gap_summary.append(
                    f"- {nutrient.upper()}: {data['current']}/{data['target']} ({data['percent_met']}% met) - {data['priority']} priority"
                )
        gap_summary_str = "\n".join(gap_summary) if gap_summary else "All nutrients met!"

        # Build trend summary
        improving_nutrients = [n for n, t in trends.items() if t == "improving"]
        declining_nutrients = [n for n, t in trends.items() if t == "declining"]

        # Branch based on workflow type
        if workflow_type in ["nutrition_query", "health_coaching", "general_chat"]:
            # Simple conversational prompt for queries (no coaching celebration)
            return self._build_nutrition_query_prompt(
                food_list=food_list,
                knowledge_result=knowledge_result,
                user_rdv=user_rdv,
                week1_averages=week1_averages,
                gaps=gaps,
                primary_gap=primary_gap,
                total_meals=total_meals,
                workflow_type=workflow_type,
                tavily_context=tavily_context
            )

        # FOOD LOGGING WORKFLOW - Full coaching with celebration
        if is_learning_phase:
            phase_context = f"""
**LEARNING PHASE MODE** (First 7 days/21 meals)
- User has logged {total_meals} meals so far
- Current logging streak: {current_streak} days
- Be OBSERVATIONAL, not prescriptive
- Celebrate logging behavior and build trust
- Gently educate about nutrients without overwhelming
- Avoid heavy recommendations - focus on encouragement
"""
        else:
            phase_context = f"""
**POST-LEARNING PHASE MODE**
- User has logged {total_meals} meals (learning phase complete!)
- Current logging streak: {current_streak} days
- Be PRESCRIPTIVE and actionable
- Identify primary nutritional gap: **{primary_gap.upper()}**
- Reference user history and trends
- Provide specific recommendations
"""

        prompt = f"""You are KAI's Coaching Agent. Generate personalized nutrition coaching in JSON format.

{phase_context}

**User Context:**
- User Name: {user_name or "there"}  (Use this for personalization when appropriate)
- Foods user eats often: {top_foods_str}
- Current meal: {food_list}

**Current Meal Context:**
- Meal Type: {meal_type.upper()}
- Meal Size: {meal_size} {size_emoji} ({knowledge_result.total_calories:.0f} kcal)

**DAILY PROGRESS (Structured Data - Use This for Calculations!):**
CRITICAL: Use these EXACT numbers for all calculations and progress messages.
DO NOT parse the formatted text below - use THIS structured data!

{self._build_structured_daily_progress(knowledge_result, daily_totals, user_rdv)}

**DAILY PROGRESS (Human-Readable Reference):**
The formatted text below is for context only. Use the structured data above for all calculations!

{self._format_daily_progress_with_meal(
    "Calories", knowledge_result.total_calories, daily_totals, user_rdv.get('calories', 2500), "kcal"
)}
{self._format_daily_progress_with_meal(
    "Protein", knowledge_result.total_protein, daily_totals, user_rdv.get('protein', 60), "g"
)}
{self._format_daily_progress_with_meal(
    "Carbs", knowledge_result.total_carbohydrates, daily_totals, user_rdv.get('carbs', 325), "g"
)}
{self._format_daily_progress_with_meal(
    "Fat", knowledge_result.total_fat, daily_totals, user_rdv.get('fat', 70), "g"
)}
{self._format_daily_progress_with_meal(
    "Iron", knowledge_result.total_iron, daily_totals, user_rdv.get('iron', 18), "mg"
)}
{self._format_daily_progress_with_meal(
    "Calcium", knowledge_result.total_calcium, daily_totals, user_rdv.get('calcium', 1000), "mg"
)}
{self._format_daily_progress_with_meal(
    "Potassium", knowledge_result.total_potassium, daily_totals, user_rdv.get('potassium', 800), "mg"
)}
{self._format_daily_progress_with_meal(
    "Zinc", knowledge_result.total_zinc, daily_totals, user_rdv.get('zinc', 8), "mg"
)}

**Meal Quality Assessment:**
- Quality: {meal_quality.upper()}
- High Nutrients (>40% RDV): {', '.join([f"{k} ({v:.0f}%)" for k, v in high_nutrients.items()]) if high_nutrients else 'None'}
- Low Nutrients (<20% RDV): {', '.join([f"{k} ({v:.0f}%)" for k, v in low_nutrients.items()]) if low_nutrients else 'None'}
- Recent Pattern: {poor_meal_count}/3 recent meals were poor quality (Status: {streak_status.upper()})

**Personalized RDV (Recommended Daily Values):**
- Calories: {user_rdv.get('calories', 0):.0f} kcal
- Protein: {user_rdv.get('protein', 0):.1f}g
- Carbs: {user_rdv.get('carbs', 0):.1f}g
- Fat: {user_rdv.get('fat', 0):.1f}g
- Iron: {user_rdv.get('iron', 0):.1f}mg
- Calcium: {user_rdv.get('calcium', 0):.1f}mg
- Potassium: {user_rdv.get('potassium', 0):.1f}mg
- Zinc: {user_rdv.get('zinc', 0):.1f}mg

**User's Weekly Average Intake (Last 7 days):**
- Calories: {week1_averages.get('calories', 0):.1f} kcal
- Protein: {week1_averages.get('protein', 0):.1f}g
- Carbs: {week1_averages.get('carbs', 0):.1f}g
- Fat: {week1_averages.get('fat', 0):.1f}g
- Iron: {week1_averages.get('iron', 0):.1f}mg
- Calcium: {week1_averages.get('calcium', 0):.1f}mg
- Potassium: {week1_averages.get('potassium', 0):.1f}mg
- Zinc: {week1_averages.get('zinc', 0):.1f}mg

**Nutrient Trends (Week-over-Week):**
- Improving: {', '.join(improving_nutrients) if improving_nutrients else 'None'}
- Declining: {', '.join(declining_nutrients) if declining_nutrients else 'None'}

**Current Nutritional Gaps:**
{gap_summary_str}

**Primary Focus:** {primary_gap.upper()}

{health_goal_guidance}

**NIGERIAN MEAL COMBO KNOWLEDGE BASE:**
Generate smart meal combos using Nigerian foods relevant to user's {primary_gap} gap.
Foods available (dynamically retrieved based on nutrient needs):

{dynamic_food_list}

**MEAL COMBO GENERATION RULES:**
1. Generate ONE complete Nigerian meal combo for next meal
2. Combo format: "Main dish + Protein source ± Swallow/Side" (NO gram measurements!)
3. Use qualitative portion sizes ONLY: small/medium/large/generous
4. Target user's PRIMARY nutrient gap: {primary_gap}
5. Respect health goal{' - WEIGHT LOSS: suggest lighter combos, skip or reduce swallow' if user_health_goals and 'lose' in user_health_goals.lower() else ''}
6. Use qualitative nutrient descriptions (rich in iron, good protein, etc.)

**CRITICAL: BE CREATIVE AND VARY YOUR SUGGESTIONS!**
- DO NOT repeat the same meal combo every time
- Use the FULL knowledge base above (up to 18 foods available!)
- Mix and match different soups, proteins, and sides creatively
- Consider what user frequently eats (from food frequency data) and suggest VARIETY
- Examples are just inspiration - CREATE UNIQUE COMBOS from the knowledge base!
- The knowledge base changes with each query, giving you fresh options to work with

Example combo formats (VARY THESE, don't copy verbatim!):
- Soup + Protein + Optional Swallow: "Ugu soup + Grilled fish + small Eba"
- Soup + Protein (no swallow): "Efo riro + Fish - skip swallow"
- Rice/Grain + Protein: "Jollof Rice + Grilled chicken"
- Stew + Protein + Swallow: "Egusi soup + Beef + medium Fufu"
- Beans-based: "Moin Moin + Plantain + Fish"
- Vegetable-heavy: "Okra soup + Catfish + small Garri"

**Your Task:**
Generate a CONCISE, HONEST JSON response with ONLY these fields:
{{
    "message": "2-3 sentences max. HONEST assessment of meal quality - don't celebrate if meal is poor.
                CRITICAL: ALWAYS reference the SPECIFIC foods user logged (e.g., 'Your Egusi soup with fish...').
                Make it personal and specific to THIS meal, not generic advice.
                Use qualitative language for nutrients (great/good/low protein) - NO specific measurements like '30g' or '8mg'.
                Only mention kcal when critical for decision-making (especially weight loss/gain goals).
                Reference health goal if relevant: {user_health_goals or 'general wellness'}.

                **STREAK CELEBRATION RULES:**
                - Current streak: {current_streak} days
                - Is this the first meal of the day? {is_first_meal_today}
                - IF is_first_meal_today=True AND streak >= 3: Your message MUST START with streak celebration!
                  * 3-6 days: START with "{current_streak}-day streak! 🔥"
                  * 7-13 days: START with "Amazing {current_streak}-day streak! 🔥"
                  * 14+ days: START with "Incredible {current_streak}-day streak! 🔥🔥"
                - IF is_first_meal_today=False: DO NOT mention streak at all - proceed with normal meal assessment
                - Streak celebration ONLY on first meal of the day (not every meal)
                - Example (first meal, 5-day streak): "5-day streak! 🔥 Your Egusi soup with fish was excellent..."
                - Example (subsequent meal, 5-day streak): "Your Jollof rice with chicken was solid! Good protein 💪"

                Use emojis: 💪 protein, 🩸 iron, 🦴 calcium, 👁️ potassium, ⚡ calories, 🔥 streaks.

                **CRITICAL NUTRIENT RULES (BASED ON DAILY CUMULATIVE PROGRESS):**
                IMPORTANT: The percentages in 'DAILY PROGRESS' are CUMULATIVE (all meals so far today).
                DO NOT judge this single meal - judge the ENTIRE DAY's progress!

                **DAILY PROGRESS THRESHOLDS (for cumulative daily totals, NOT single meals):**
                - >= 70% of daily RDV: "Great progress today!" (on track)
                - 40-69% of daily RDV: "Good progress, keep going!" (decent)
                - < 40% of daily RDV: "Needs attention today" (concerning for full day)

                **ALWAYS reference cumulative daily totals (TODAY SO FAR values), NOT just this meal!**

                SPECIFIC THRESHOLDS FOR EACH NUTRIENT (based on DAILY CUMULATIVE totals):
                - Daily protein >= 70%: "You're doing great on protein today! 💪"
                - Daily protein 40-69%: "Good protein progress today 💪, keep it up!"
                - Daily protein < 40%: "Let's boost protein for your remaining meals 💪"
                - Daily iron >= 70%: "Excellent iron intake today! 🩸"
                - Daily iron 40-69%: "Good iron progress! 🩸"
                - Daily iron < 40%: "Add more iron-rich foods today 🩸"
                - Same threshold logic for calcium 🦴, potassium 👁️, zinc
                - ONLY flag nutrients as 'low' if DAILY CUMULATIVE total is < 40% RDV (not per meal!)

                Examples (using STRUCTURED DATA from 'DAILY PROGRESS (Structured Data)'):
                  * "You've had 42g protein today (70% of goal) - excellent progress! 💪" (use protein.daily_total and protein.percent_of_target)
                  * "You're at 8mg iron so far (44% of goal) - great! 🩸 One more meal and you'll hit your target" (use iron.daily_total and iron.percent_of_target)
                  * "Only 15g protein today (25% of goal) - add more protein to your next meal 💪" (use protein.daily_total and protein.percent_of_target)
                  * For CALORIES: "You're at 1650/2500 kcal today (66%) - you have 850 kcal remaining for your next meal" (use calories.daily_total, calories.target, calories.remaining)

                Examples (streak ONLY if is_first_meal_today=True AND >= 3 days):
                - FIRST MEAL with 3-day streak: '{user_name or "Great job"}, 3-day streak! 🔥 Your Egusi soup with fish was excellent! Great protein 💪 and iron 🩸.'
                - FIRST MEAL with 7-day streak: 'Amazing week-long streak! 🔥 Your Jollof rice with chicken was solid! You're at 1200/2500 kcal today.'
                - FIRST MEAL with 14-day streak: 'Incredible 2-week streak! 🔥🔥 Your Efo riro with fish was perfect! High iron 🩸 and protein 💪.'
                - SUBSEQUENT MEAL (no streak mention): 'Your Jollof rice with chicken was solid! You're at 1650/2500 kcal today - 850 left for dinner.'
                - SUBSEQUENT MEAL (no streak mention): 'Your Eba with vegetable soup was decent but low on protein. Add fish to your next meal!'
                - NO STREAK (< 3 days): 'Your {meal_type} of Jollof rice with chicken was solid! Good protein and energy.'
                - POOR meal (weight loss): 'Your fried plantain with rice (800 kcal ⚡) puts you over target. Low protein and iron. Eat lighter for dinner to stay on track.'",

    "next_meal_combo": {{
        "combo": "ONE specific Nigerian meal combo selected from the knowledge base above.
                  Format: 'Main dish + Protein ± Side'.
                  NO portion sizes in grams! Just describe portions qualitatively (small/medium/large).

                  **IMPORTANT: CREATE VARIETY!**
                  - Use different foods from the 18 options in the knowledge base
                  - Don't suggest the same combos repeatedly
                  - Mix and match creatively based on user's nutrient needs
                  - Consider user's frequently eaten foods and suggest complementary options
                  - The knowledge base is dynamically generated, so you have fresh foods to choose from each time

                  Examples (CREATE YOUR OWN, don't copy these):
                  - 'Ugu soup + Grilled fish + small Eba'
                  - 'Egusi soup + Beef + medium Fufu'
                  - 'Okra soup + Catfish - skip swallow'
                  - 'Jollof Rice + Grilled chicken'
                  - 'Moin Moin + Fried plantain + Fish'",

        "why": "One sentence explaining how this combo closes {primary_gap} gap and fits {user_health_goals or 'goal'}.
                Use qualitative language - NO specific grams/mg.
                Focus on the PRIMARY nutrient this combo provides.
                Example: 'Rich in iron and protein while keeping calories low for your weight loss goal'"
    }},

    "goal_progress": {{
        "type": "{user_health_goals or 'general_wellness'}",  // User's actual health goal
        "status": "excellent | on_track | needs_attention",  // Honest assessment
        "message": "One sentence about progress toward goal.

                    **CRITICAL: Use the STRUCTURED DATA from 'DAILY PROGRESS (Structured Data)' section above!**
                    DO NOT parse formatted text - use the JSON values directly!

                    Access the data like this:
                    - calories.daily_total (current cumulative intake today)
                    - calories.target (daily goal)
                    - calories.remaining (how much left for the day)
                    - calories.percent_of_target (percentage progress)
                    - Same structure for: protein, carbs, fat, iron, calcium, potassium, zinc

                    For weight goals, use: calories.daily_total / calories.target format

                    Examples (using structured data):
                    - Weight loss: 'You're at 1650/1800 kcal today - only 150 kcal left for dinner. Stay disciplined!'
                    - Muscle gain: 'Great protein today! You're at 85g/120g. One more high-protein meal and you'll hit your target.'
                    - General wellness: 'Good balance today. Your iron (8mg/18mg) and protein (45g/60g) levels are looking solid!'"
    }}
}}

**CRITICAL HONESTY RULES:**
1. DO NOT celebrate every meal - be honest about quality
2. If meal is poor (low protein, high calories, minimal nutrients):
   - State it clearly: "This meal is low in protein and nutrients"
   - Explain why it's problematic for their goal
   - Suggest better alternatives in next_meal_combo
3. Only celebrate when meal is genuinely good
4. Patterns matter: If user has 3 poor meals in a row, be FIRM and direct

**NEXT MEAL COMBO REQUIREMENTS:**
1. MUST suggest ONE complete Nigerian meal combo (not individual foods)
2. Combo MUST target user's TOP nutrient gap: {primary_gap}
3. Combo MUST fit user's health goal{' (WEIGHT LOSS: keep under 600 cal, prioritize protein)' if user_health_goals and 'lose' in user_health_goals.lower() else ''}
4. **CRITICAL: Use DIFFERENT foods from the 18 options in the knowledge base above - CREATE VARIETY!**
5. Mix and match creatively: Don't suggest "Efo riro + Fish" every time!
6. Use qualitative portions (small/medium/large) - NO grams!
7. The knowledge base varies each time, so explore the full list and be creative!

**GOAL PROGRESS REQUIREMENTS:**
1. Must reference user's ACTUAL health goal from profile
2. Status must be honest (not always "excellent")
3. Message should motivate without lying about progress

Generate the JSON now:"""

        return prompt

    def _build_nutrition_query_prompt(
        self,
        food_list: str,
        knowledge_result: KnowledgeResult,
        user_rdv: Dict[str, float],
        week1_averages: Dict[str, float],
        gaps: Dict[str, Dict],
        primary_gap: str,
        total_meals: int,
        workflow_type: str,
        tavily_context: Optional[str] = None
    ) -> str:
        """Build conversational prompt for nutrition queries (chat endpoint).

        Args:
            tavily_context: Optional research context from Tavily to integrate naturally
        """

        # Build nutrition data context
        foods_mentioned = food_list if food_list else "No specific food"

        # Check if user has history for personalization
        has_history = total_meals > 0
        personalization_context = ""
        if has_history:
            # Include relevant user context for personalization
            gap_summary = []
            for nutrient, data in list(gaps.items())[:2]:  # Top 2 gaps
                if data["priority"] == "high":
                    gap_summary.append(f"{nutrient} (currently {data['percent_met']}% of target)")

            if gap_summary:
                personalization_context = f"""
**User's Nutrition History (Optional for Personalization):**
- Total meals logged: {total_meals}
- Key nutritional gaps: {', '.join(gap_summary)}
- Weekly iron average: {week1_averages.get('iron', 0):.1f}mg (target: {user_rdv.get('iron', 18):.1f}mg)
- Use this ONLY if relevant to the question asked
"""

        # Build nutrition data if foods were found
        nutrition_context = ""
        if knowledge_result.foods:
            nutrition_context = f"""
**Nutrition Data for: {food_list}**
Per 250g serving (typical portion):
- Calories: {knowledge_result.total_calories:.0f} kcal ({(knowledge_result.total_calories/user_rdv.get('calories',2500)*100):.0f}% of daily needs)
- Protein: {knowledge_result.total_protein:.1f}g ({(knowledge_result.total_protein/user_rdv.get('protein',60)*100):.0f}% of daily needs)
- Carbs: {knowledge_result.total_carbohydrates:.1f}g ({(knowledge_result.total_carbohydrates/user_rdv.get('carbs',325)*100):.0f}% of daily needs)
- Fat: {knowledge_result.total_fat:.1f}g ({(knowledge_result.total_fat/user_rdv.get('fat',70)*100):.0f}% of daily needs)
- Iron: {knowledge_result.total_iron:.1f}mg ({(knowledge_result.total_iron/user_rdv.get('iron',18)*100):.0f}% of daily needs)
- Calcium: {knowledge_result.total_calcium:.1f}mg ({(knowledge_result.total_calcium/user_rdv.get('calcium',1000)*100):.0f}% of daily needs)
- Potassium: {knowledge_result.total_potassium:.1f}mg ({(knowledge_result.total_potassium/user_rdv.get('potassium',800)*100):.0f}% of daily needs)
- Zinc: {knowledge_result.total_zinc:.1f}mg ({(knowledge_result.total_zinc/user_rdv.get('zinc',8)*100):.0f}% of daily needs)

Source: Nigerian Foods Nutrition Database
"""

        # Check if Tavily research context is available
        tavily_context_section = ""
        if tavily_context:
            tavily_context_section = f"""
**Additional Research Context (integrate naturally):**
{tavily_context}

IMPORTANT: Integrate this research NATURALLY into your response. Do NOT use prefixes like "Research insight:" or "Source:".
Weave it seamlessly into the answer as if it's part of your knowledge.
"""

        prompt = f"""You are KAI, a conversational Nigerian nutrition assistant. Answer the user's question directly and naturally.

**User's Question Context:**
- Foods mentioned: {foods_mentioned}
- Query type: {workflow_type}

{nutrition_context}
{personalization_context}
{tavily_context_section}

**Your Task:**
Generate a CONVERSATIONAL JSON response with ONLY this field:
{{
    "personalized_message": "Direct answer to the user's question. 3-5 sentences.

    Structure:
    1. Direct answer with specific numbers/facts
    2. Additional helpful context (serving sizes, comparisons, benefits, research insights)
    3. Optional personalization if user history is relevant
    4. End with a follow-up question to encourage engagement

    Guidelines:
    - Be CONVERSATIONAL, not coaching-heavy
    - Use emojis sparingly (1-2 per message)
    - Answer what was asked - don't give unsolicited advice
    - Keep it concise and focused
    - Integrate research context NATURALLY (no "Research insight:" prefixes)
    - NO motivational tips
    - NO next_steps list
    - NO source citations in the message
    - End with an engaging follow-up question
    "
}}

**IMPORTANT - Response should ONLY contain:**
- ✅ personalized_message field
- ❌ NO motivational_tip
- ❌ NO next_steps
- ❌ NO nutrient_insights
- ❌ NO meal_suggestions
- ❌ NO source citations

Generate the JSON now:"""

        return prompt

    def _get_tone_instructions(self, meal_quality: str, streak_status: str, is_learning_phase: bool) -> str:
        """Generate tone instructions based on meal quality and user phase."""

        if streak_status == "intervention":
            # 3 poor meals in a row - STRICT intervention needed
            return """
            🚨 STRICT INTERVENTION TONE (3 poor meals detected):
            - Be FIRM and DIRECT about the concern
            - Start with: "We need to talk" or "I'm concerned"
            - Show specific nutrient deficits with numbers
            - Explain health risks (anemia, weak bones, etc.)
            - Demand immediate action: "Let's get back on track TODAY"
            - End with accountability question: "Can you commit to..."
            - Example: "We need to talk. 🛑 You've logged 3 poor meals in a row (biscuits, doughnuts, soft drinks). Your protein is only 8g/day vs your 60g target - this will cause muscle loss and fatigue. You need to eat a proper Nigerian meal TODAY: Jollof Rice with Chicken, or Beans and Plantain. Can you commit to this?"
            """

        elif streak_status == "warning":
            # 2 poor meals in last 3 - Warning tone
            return """
            ⚠️ WARNING TONE (2/3 recent meals were poor):
            - Be concerned but supportive
            - Acknowledge the pattern: "I've noticed..."
            - Show the nutrient impact
            - Provide clear next steps
            - Example: "I've noticed you've been logging mostly snacks lately (2 of your last 3 meals). ⚠️ This is affecting your nutrition - protein is down to 15g/day. Let's refocus! Try adding a proper meal like Egusi Soup or Jollof Rice with protein for your next meal. You were doing great before!"
            """

        elif meal_quality == "poor" and not is_learning_phase:
            # Single poor meal, post-learning phase - Corrective but not harsh
            return """
            ⚠️ CORRECTIVE TONE (single poor meal, post-learning):
            - Acknowledge what they logged without judgment
            - Explain WHY it's not ideal (specific nutrient gaps)
            - Suggest better alternatives
            - Example: "I see you logged a doughnut and soft drink. This meal is very low in protein (3g - 5%), iron (1mg - 6%), and calcium (2%) 🦴. It's mostly empty calories. Consider adding groundnuts for protein, or next time try Puff Puff with milk - still sweet but more nutritious! 💡"
            """

        elif meal_quality == "poor" and is_learning_phase:
            # Poor meal during learning phase - Gentle education
            return """
            💡 GENTLE EDUCATIONAL TONE (poor meal, learning phase):
            - Be kind and educational, not prescriptive
            - Acknowledge the meal positively
            - Gently explain nutrient content
            - End with encouragement
            - Example: "Thanks for logging your snack! 😊 This meal is high in calories but low in protein (5%), iron (4%), and calcium (3%). That's okay - you're learning what different foods contain! As KAI learns your patterns, we'll work together to balance nutrition and enjoyment. Keep logging! 🌟"
            """

        elif meal_quality == "excellent":
            # Excellent meal - Celebrate!
            return """
            🎉 CELEBRATORY TONE (excellent meal):
            - Be enthusiastic and celebratory!
            - Highlight all the HIGH nutrients with excitement
            - Encourage continuation
            - Example: "Excellent choice! 🎉 This meal is a nutrient powerhouse! Packed with protein (45g - 75%) 💪, iron (8mg - 44%) 🩸, and potassium (65%) 👁️. You're nourishing your body perfectly! Keep up this amazing work! 🌟"
            """

        elif meal_quality == "good":
            # Good meal - Positive and encouraging
            return """
            😊 ENCOURAGING TONE (good meal):
            - Be positive and supportive
            - Highlight the HIGH nutrients
            - Gently mention what could be better (if relevant)
            - Example: "Great job logging! 🎉 This meal is rich in protein (35g - 58%) 💪 and potassium (520mg - 65%) 👁️. It's a bit low in calcium (9%) 🦴 - consider adding yogurt or milk next time. Overall, great choice! Keep it up!"
            """

        else:  # meal_quality == "okay"
            # Okay meal - Supportive with suggestions
            return """
            💪 SUPPORTIVE TONE (okay meal):
            - Be supportive and constructive
            - Acknowledge what's good
            - Suggest simple improvements
            - Example: "Nice logging! 😊 This meal provides decent energy (calories 25%) ⚡ and some protein (20%) 💪. To make it even better, add some vegetables (for potassium 👁️) or dairy (for calcium 🦴). Small additions make a big difference!"
            """

    def _fallback_coaching(
        self,
        food_list: str,
        is_learning_phase: bool,
        primary_gap: str,
        gaps: Dict[str, Dict],
        user_rdv: Dict[str, float]
    ) -> Dict[str, Any]:
        """Simplified fallback coaching if GPT-4o fails."""
        logger.warning("Using fallback coaching template")

        if is_learning_phase:
            message = f"Great job logging your meal: {food_list}! 🎉 Keep tracking your meals to help KAI learn your eating patterns."
            tip = "You're building a healthy habit by logging your meals. Consistency is key! 🌟"
            steps = [
                "Log your next meal to continue building your profile 📝",
                "Keep exploring different Nigerian dishes 🍽️",
                "Celebrate your consistency! 🎉"
            ]
        else:
            gap_data = gaps.get(primary_gap, {})
            message = f"Thanks for logging {food_list}! 😊 Your {primary_gap} intake could use attention - you're at {gap_data.get('percent_met', 0):.0f}% of your daily goal."
            tip = f"Focus on adding {primary_gap}-rich Nigerian foods to boost your nutrition 💪"
            steps = [
                f"Add {primary_gap}-rich foods to your next meal 🥗",
                "Keep logging to track your progress 📊",
                "Stay consistent with your meal tracking! 🔥"
            ]

        # Simplified response (no nutrient_insights, no meal_suggestions)
        return {
            "personalized_message": message,
            "motivational_tip": tip,
            "next_steps": steps
        }

    async def _call_tavily_mcp(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Call Tavily search directly (avoiding subprocess for Windows compatibility).
        
        This method directly instantiates TavilyMCPServer instead of using subprocess,
        which avoids NotImplementedError on Windows event loops.
        """
        # Import here to avoid circular dependencies
        from kai.mcp_servers.tavily_server import TavilyMCPServer
        
        # Run Tavily search in thread pool to avoid blocking the event loop
        # TavilyClient makes HTTP requests which are I/O bound
        loop = asyncio.get_event_loop()
        tavily_server = TavilyMCPServer()
        
        # Create the request object matching MCP format
        request_obj = {
            "method": "tools/call",
            "params": {
                "name": "search_nigerian_nutrition",
                "arguments": {"query": query, "max_results": max_results}
            }
        }
        
        # Call the server's handle_request method in executor to avoid blocking
        response = await loop.run_in_executor(
            None,  # Use default ThreadPoolExecutor
            tavily_server.handle_request,
            request_obj
        )
        
        if isinstance(response, dict) and "error" in response:
            raise RuntimeError(response["error"])

        # Parse the MCP response format
        content = response.get("content", []) if isinstance(response, dict) else []
        if content and isinstance(content, list) and isinstance(content[0], dict) and content[0].get("type") == "text":
            try:
                return json.loads(content[0].get("text", "{}"))
            except Exception:
                return {"raw": content[0].get("text")}
        return response if isinstance(response, dict) else {"raw": str(response)}

    def _parse_coaching_result(self, result_dict: Dict[str, Any]) -> CoachingResult:
        """
        Parse GPT-4o's JSON response into CoachingResult model.

        Expected format from GPT-4o:
        {
            "message": "Honest assessment...",
            "next_meal_combo": {
                "combo": "Ugu soup (300g) + Fish (150g)...",
                "why": "Closes iron gap..."
            },
            "goal_progress": {
                "type": "lose_weight",
                "status": "needs_attention",
                "message": "You're at 1650/1800 cal today..."
            }
        }

        Args:
            result_dict: Parsed JSON from GPT-4o

        Returns:
            Structured CoachingResult with goal-aligned fields
        """
        from kai.models.agent_models import NextMealCombo, GoalProgress

        # Parse next_meal_combo
        next_meal_combo_data = result_dict.get("next_meal_combo", {})
        next_meal_combo = NextMealCombo(
            combo=next_meal_combo_data.get("combo", ""),
            why=next_meal_combo_data.get("why", "")
        )

        # Parse goal_progress
        goal_progress_data = result_dict.get("goal_progress", {})
        goal_progress = GoalProgress(
            type=goal_progress_data.get("type", "general_wellness"),
            status=goal_progress_data.get("status", "on_track"),
            message=goal_progress_data.get("message", "")
        )

        # Create CoachingResult with new format (no old fields!)
        return CoachingResult(
            message=result_dict.get("message", ""),
            next_meal_combo=next_meal_combo,
            goal_progress=goal_progress
        )

    def _classify_meal_quality(
        self,
        knowledge_result: KnowledgeResult,
        user_rdv: Dict[str, float]
    ) -> tuple[str, Dict[str, float], Dict[str, float]]:
        """
        Classify meal quality based on nutrient content.

        Returns:
            (quality, high_nutrients, low_nutrients)
            quality: "excellent" | "good" | "okay" | "poor"
            high_nutrients: Dict of nutrients >40% RDV with their percentages
            low_nutrients: Dict of nutrients <20% RDV with their percentages
        """
        # Calculate nutrient percentages for current meal
        nutrient_percentages = {
            'calories': (knowledge_result.total_calories / user_rdv.get('calories', 2500)) * 100,
            'protein': (knowledge_result.total_protein / user_rdv.get('protein', 60)) * 100,
            'carbohydrates': (knowledge_result.total_carbohydrates / user_rdv.get('carbs', 325)) * 100,
            'fat': (knowledge_result.total_fat / user_rdv.get('fat', 70)) * 100,
            'iron': (knowledge_result.total_iron / user_rdv.get('iron', 18)) * 100,
            'calcium': (knowledge_result.total_calcium / user_rdv.get('calcium', 1000)) * 100,
            'potassium': (knowledge_result.total_potassium / user_rdv.get('potassium', 800)) * 100,
            'zinc': (knowledge_result.total_zinc / user_rdv.get('zinc', 8)) * 100,
        }

        # Identify high nutrients (>40% RDV)
        high_nutrients = {k: v for k, v in nutrient_percentages.items() if v >= 40}

        # Identify low nutrients (<20% RDV)
        low_nutrients = {k: v for k, v in nutrient_percentages.items() if v < 20}

        # Classify quality
        protein_pct = nutrient_percentages['protein']
        iron_pct = nutrient_percentages['iron']
        calcium_pct = nutrient_percentages['calcium']
        potassium_pct = nutrient_percentages['potassium']
        zinc_pct = nutrient_percentages['zinc']

        high_count = len(high_nutrients)
        low_count = len(low_nutrients)

        # Explicit nutrient protection: High key nutrients should NEVER result in "poor" quality
        protein_is_high = protein_pct >= 40  # >40% RDV = HIGH (24g for women, 28g for men)
        iron_is_high = iron_pct >= 40  # >40% RDV = HIGH (7.2mg for women, 3.2mg for men)
        calcium_is_high = calcium_pct >= 40  # >40% RDV = HIGH (400mg)
        potassium_is_high = potassium_pct >= 40  # >40% RDV = HIGH (280-360mg)
        zinc_is_high = zinc_pct >= 40  # >40% RDV = HIGH (3.2-4.4mg)

        # Any key nutrient being high protects meal quality
        any_key_nutrient_high = (protein_is_high or iron_is_high or calcium_is_high or
                                 potassium_is_high or zinc_is_high)

        if protein_pct >= 30 and high_count >= 3:
            quality = "excellent"  # High protein + 3+ nutrients above 40%
        elif high_count >= 2 or any_key_nutrient_high:
            quality = "good"  # 2+ nutrients above 40% OR any key nutrient protects from low rating
        elif low_count >= 5 and protein_pct < 15:
            quality = "poor"  # 5+ nutrients below 20% AND low protein
        else:
            quality = "okay"  # Everything else

        return quality, high_nutrients, low_nutrients

    async def _detect_poor_meal_streak(self, user_id: str) -> tuple[int, str]:
        """
        Detect if user has logged multiple poor quality meals in a row.

        Returns:
            (poor_count, streak_status)
            poor_count: Number of poor meals in last 3
            streak_status: "normal" | "warning" | "intervention"
        """
        from kai.database import get_user_meals

        try:
            # Get last 3 meals
            recent_meals = await get_user_meals(user_id, limit=3)

            if not recent_meals:
                return 0, "normal"

            poor_count = 0
            for meal in recent_meals:
                # Calculate total nutrients for this meal
                meal_totals = {
                    'calories': 0, 'protein': 0, 'carbohydrates': 0, 'fat': 0,
                    'iron': 0, 'calcium': 0, 'potassium': 0, 'zinc': 0
                }

                for food in meal.get('foods', []):
                    meal_totals['calories'] += food.get('calories', 0)
                    meal_totals['protein'] += food.get('protein', 0)
                    meal_totals['carbohydrates'] += food.get('carbohydrates', 0)
                    meal_totals['fat'] += food.get('fat', 0)
                    meal_totals['iron'] += food.get('iron', 0)
                    meal_totals['calcium'] += food.get('calcium', 0)
                    meal_totals['potassium'] += food.get('potassium', 0)
                    meal_totals['zinc'] += food.get('zinc', 0)

                # Create temporary KnowledgeResult to classify
                from kai.models import KnowledgeResult
                temp_knowledge = KnowledgeResult(
                    foods=[],
                    total_calories=meal_totals['calories'],
                    total_protein=meal_totals['protein'],
                    total_carbohydrates=meal_totals['carbohydrates'],
                    total_fat=meal_totals['fat'],
                    total_iron=meal_totals['iron'],
                    total_calcium=meal_totals['calcium'],
                    total_potassium=meal_totals['potassium'],
                    total_zinc=meal_totals['zinc'],
                    query_interpretation="",
                    sources_used=[]
                )

                # Classify meal (use default RDV for classification)
                from kai.utils import calculate_user_rdv
                default_rdv = calculate_user_rdv({"gender": "female", "age": 25, "activity_level": "moderate"})
                meal_quality, _, _ = self._classify_meal_quality(temp_knowledge, default_rdv)

                if meal_quality == "poor":
                    poor_count += 1

            # Determine streak status
            if poor_count >= 3:
                streak_status = "intervention"  # All 3 were poor - serious concern
            elif poor_count >= 2:
                streak_status = "warning"  # 2+ poor meals - concerning pattern
            else:
                streak_status = "normal"

            return poor_count, streak_status

        except Exception as e:
            logger.warning(f"Could not detect poor meal streak: {e}")
            return 0, "normal"


# ============================================================================
# Convenience Functions
# ============================================================================

def provide_nutrition_coaching(
    user_id: str,
    knowledge_result: KnowledgeResult,
    user_context: Optional[Dict[str, Any]] = None,
    openai_api_key: Optional[str] = None
) -> CoachingResult:
    """
    Convenience function for single coaching session.

    NEW SIGNATURE: Now requires user_id for personalized stats-based coaching.

    Args:
        user_id: User ID to generate coaching for
        knowledge_result: Nutrition data to coach on
        user_context: Optional user context (budget, activity_level, etc.)
        openai_api_key: Optional API key override

    Returns:
        CoachingResult with personalized, dynamic guidance
    """
    import asyncio
    agent = CoachingAgent(openai_api_key=openai_api_key)
    return asyncio.run(agent.provide_coaching(user_id, knowledge_result, user_context))


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from kai.models import NutrientInfo, FoodNutritionData

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_coaching_agent():
        """Test Coaching Agent with sample nutrition data."""

        print("\n" + "="*60)
        print("Testing Coaching Agent - Personalized Nutrition Guidance")
        print("="*60 + "\n")

        # Initialize agent
        agent = CoachingAgent()

        print(f"Model: {agent.model}")
        print(f"Agent: {agent.agent.name}")

        # Create sample nutrition data (low iron scenario)
        sample_nutrients_per_100g = NutrientInfo(
            calories=150,
            protein=5.0,
            carbohydrates=30.0,
            fat=2.0,
            iron=1.5,
            calcium=50,
            potassium=200,
            zinc=1.0
        )

        sample_total_nutrients = NutrientInfo(
            calories=375,  # 250g portion
            protein=12.5,
            carbohydrates=75.0,
            fat=5.0,
            iron=3.75,  # Low iron!
            calcium=125,  # Low calcium!
            potassium=500,
            zinc=2.5
        )

        sample_food = FoodNutritionData(
            food_id="nigerian-jollof-rice",
            name="Jollof Rice",
            category="staple",
            portion_consumed_grams=250.0,
            nutrients_per_100g=sample_nutrients_per_100g,
            total_nutrients=sample_total_nutrients,
            health_benefits=["Energy source", "Contains vegetables"],
            cultural_significance="Popular Nigerian dish",
            common_pairings=["Chicken", "Plantain", "Salad"],
            dietary_flags=[],
            price_tier="mid",
            similarity_score=1.0
        )

        sample_knowledge_result = KnowledgeResult(
            foods=[sample_food],
            total_calories=375,
            total_protein=12.5,
            total_iron=3.75,
            total_calcium=125,
            query_interpretation="Single food meal",
            sources_used=["ChromaDB"]
        )

        # Test 1: Non-pregnant woman
        print("\n" + "-"*60)
        print("Test 1: Coaching for Non-Pregnant Woman")
        print("-"*60)

        result = await agent.provide_coaching(
            user_id="test_user_123", # Added user_id for testing
            knowledge_result=sample_knowledge_result,
            user_context={"is_pregnant": False, "budget": "mid"}
        )

        print(f"\n✉️  Personalized Message:")
        print(f"   {result.personalized_message}")

        print(f"\n📊 Nutrient Insights:")
        for insight in result.nutrient_insights:
            print(
                f"   - {insight.nutrient.upper()}: {insight.current_value}/{insight.recommended_daily_value} "
                f"({insight.percentage_met:.1f}%) - {insight.status}"
            )

        print(f"\n💪 Motivational Tip:")
        print(f"   {result.motivational_tip}")

        print(f"\n📝 Next Steps:")
        for i, step in enumerate(result.next_steps, 1):
            print(f"   {i}. {step}")

        # Test 2: Pregnant woman
        print("\n\n" + "-"*60)
        print("Test 2: Coaching for Pregnant Woman")
        print("-"*60)

        result_pregnant = await agent.provide_coaching(
            user_id="test_user_123", # Added user_id for testing
            knowledge_result=sample_knowledge_result,
            user_context={"is_pregnant": True, "budget": "low"}
        )

        print(f"\n✉️  Personalized Message:")
        print(f"   {result_pregnant.personalized_message}")

        print(f"\n📊 Nutrient Insights (Pregnancy Adjusted):")
        for insight in result_pregnant.nutrient_insights:
            if insight.nutrient == "iron":
                print(
                    f"   - {insight.nutrient.upper()}: {insight.current_value}/{insight.recommended_daily_value} "
                    f"({insight.percentage_met:.1f}%) - {insight.status} (PREGNANCY)"
                )

        print(f"\n📝 Next Steps:")
        for i, step in enumerate(result_pregnant.next_steps, 1):
            print(f"   {i}. {step}")

        print("\n" + "="*60)
        print("Coaching Agent Tests Complete!")
        print("="*60 + "\n")

    # Run tests
    asyncio.run(test_coaching_agent())
