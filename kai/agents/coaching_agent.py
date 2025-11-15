"""
Coaching Agent - Personalized Nutrition Guidance

Provides culturally-aware, empathetic nutrition coaching for ALL Nigerians.
Uses GPT-4o for dynamic, personalized coaching based on user history and stats.

Focus areas:
- Multi-nutrient tracking (all 8 nutrients)
- Learning phase (observational first 7 days/21 meals)
- Progressive coaching with week-over-week trends
- Budget-friendly meal planning
- Cultural context and preferences
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
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
    - Budget-aware recommendations
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize Coaching Agent with GPT-4o."""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"  # GPT-4o for dynamic coaching generation

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
                        "Suggest Nigerian meals based on nutritional needs and budget. "
                        "Provides culturally-relevant, affordable meal ideas."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "nutrient_needs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Nutrients to focus on (e.g., ['iron', 'protein'])"
                            },
                            "budget": {
                                "type": "string",
                                "enum": ["low", "mid", "high"],
                                "description": "Budget tier"
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
- Multi-nutrient analysis (calories, protein, carbs, fat, iron, calcium, vitamin A, zinc)
- Learning phase coaching (observational for first 7 days/21 meals)
- Progressive coaching based on week-over-week trends
- Budget-friendly meal planning
- Motivational coaching with cultural sensitivity

**Your Approach:**
1. Celebrate what users are doing well (reference specific foods they've eaten)
2. Provide actionable, budget-aware suggestions
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
- Vitamin A: Immune system and vision
- Zinc: Immune function and wound healing

**Your Tone:**
- Warm and supportive (like a trusted friend)
- Encouraging and positive
- Practical and actionable
- Gender-neutral and inclusive
- Culturally aware and respectful
- Health-focused but realistic about budgets

**Cultural Sensitivity:**
- Respect food traditions and preferences
- Acknowledge financial realities
- Suggest locally available, affordable Nigerian foods
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

    async def provide_coaching(
        self,
        user_id: str,
        knowledge_result: KnowledgeResult,
        user_context: Optional[Dict[str, Any]] = None
    ) -> CoachingResult:
        """
        Provide personalized nutrition coaching based on user history and current meal.

        NEW APPROACH:
        - Fetches user stats (weekly averages, trends, streaks)
        - Calculates personalized RDV for ALL 8 nutrients
        - Detects learning phase vs post-learning phase
        - Uses GPT-4o for dynamic coaching (no hardcoded templates!)

        Args:
            user_id: User ID to generate coaching for
            knowledge_result: Nutrition data from Knowledge Agent (current meal)
            user_context: Optional overrides (budget, use_web_research, etc.)

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
                    "week1_avg_vitamin_a": 0, "week1_avg_zinc": 0,
                    "calories_trend": "stable", "protein_trend": "stable", "carbs_trend": "stable",
                    "fat_trend": "stable", "iron_trend": "stable", "calcium_trend": "stable",
                    "vitamin_a_trend": "stable", "zinc_trend": "stable",
                }
                food_frequency = []
            else:
                user = await get_user(user_id)
                user_stats = await get_user_stats(user_id)
                food_frequency = await get_user_food_frequency(user_id, top_n=10)

            # Calculate personalized RDV
            user_profile = {
                "gender": user.get("gender", "female"),
                "age": user.get("age", 25),
                "activity_level": user_context.get("activity_level", "moderate")
            }
            user_rdv = calculate_user_rdv(user_profile)

            # Detect learning phase
            is_learning_phase = not user_stats.get("learning_phase_complete", False)
            total_meals = user_stats.get("total_meals_logged", 0)
            current_streak = user_stats.get("current_logging_streak", 0)

            # Get week1 averages for gap analysis
            week1_averages = {
                "calories": user_stats.get("week1_avg_calories", 0),
                "protein": user_stats.get("week1_avg_protein", 0),
                "carbs": user_stats.get("week1_avg_carbs", 0),
                "fat": user_stats.get("week1_avg_fat", 0),
                "iron": user_stats.get("week1_avg_iron", 0),
                "calcium": user_stats.get("week1_avg_calcium", 0),
                "vitamin_a": user_stats.get("week1_avg_vitamin_a", 0),
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
                "vitamin_a": user_stats.get("vitamin_a_trend", "stable"),
                "zinc": user_stats.get("zinc_trend", "stable"),
            }

            # Identify nutritional gaps
            gaps = get_nutrient_gap_priority(week1_averages, user_rdv)
            primary_gap = get_primary_nutritional_gap(gaps)

            # Generate coaching using GPT-4o
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
                user_context=user_context or {}
            )

            # Optionally enrich with Tavily MCP web research
            research_requested = (user_context or {}).get("use_web_research", False)
            has_deficiency = any(
                ni.get("status") == "deficient" for ni in coaching_data.get("nutrient_insights", [])
            )

            if research_requested or has_deficiency:
                deficient_names = [
                    ni.get("nutrient") for ni in coaching_data.get("nutrient_insights", [])
                    if ni.get("status") == "deficient"
                ]
                query = "Nigerian foods to improve " + (
                    ", ".join(deficient_names[:2]) if deficient_names else "nutrition"
                )
                logger.info(f"🌐 Calling Tavily MCP for query: {query}")
                try:
                    tavily_response = await asyncio.wait_for(
                        self._call_tavily_mcp(query=query, max_results=3),
                        timeout=12.0
                    )
                    sources = tavily_response.get("sources", []) if isinstance(tavily_response, dict) else []
                    answer_text = tavily_response.get("answer") if isinstance(tavily_response, dict) else None
                    if answer_text:
                        summary = answer_text.split(". ")[0].strip()
                        if not summary:
                            summary = answer_text.strip()[:220]
                        existing_msg = coaching_data.get("personalized_message", "").strip()
                        if existing_msg:
                            coaching_data["personalized_message"] = f"{existing_msg}\n\nResearch insight: {summary}."
                        else:
                            coaching_data["personalized_message"] = f"Research insight: {summary}."
                        logger.info(f"✅ Tavily enrichment added to coaching message")
                    if sources:
                        extra_steps = [
                            f"Source: {src.get('title', 'Link')} - {src.get('url', '')}"
                            for src in sources[:2]
                        ]
                        coaching_data["next_steps"] = (coaching_data.get("next_steps", []) + extra_steps)[:5]
                        logger.info(f"✅ Added {len(sources)} Tavily sources to next steps")
                except Exception as mcp_err:
                    logger.warning("Tavily MCP enrichment skipped: %s", mcp_err, exc_info=True)
            else:
                logger.info(f"⏭️ Tavily enrichment skipped: research_requested={research_requested}, has_deficiency={has_deficiency}")

            coaching_result = self._parse_coaching_result(coaching_data)

            logger.info(
                f"✅ Generated coaching: {len(coaching_result.nutrient_insights)} insights, "
                f"{len(coaching_result.meal_suggestions)} suggestions"
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
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate dynamic coaching using GPT-4o based on user history and current meal.

        This replaces ALL hardcoded templates with AI-generated personalized coaching.

        Args:
            user_id: User ID
            knowledge_result: Current meal nutrition data
            user_rdv: Personalized RDV for all 8 nutrients
            week1_averages: Last 7 days average intake
            trends: Nutrient trends (improving/declining/stable)
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

        # Build context for GPT-4o
        foods_eaten = [food.name for food in knowledge_result.foods]
        food_list = ", ".join(foods_eaten)

        # Build system prompt
        system_prompt = self._build_dynamic_coaching_prompt(
            food_list=food_list,
            user_rdv=user_rdv,
            week1_averages=week1_averages,
            trends=trends,
            gaps=gaps,
            primary_gap=primary_gap,
            is_learning_phase=is_learning_phase,
            total_meals=total_meals,
            current_streak=current_streak,
            food_frequency=food_frequency,
            budget=user_context.get("budget", "mid")
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

    def _build_dynamic_coaching_prompt(
        self,
        food_list: str,
        user_rdv: Dict[str, float],
        week1_averages: Dict[str, float],
        trends: Dict[str, str],
        gaps: Dict[str, Dict],
        primary_gap: str,
        is_learning_phase: bool,
        total_meals: int,
        current_streak: int,
        food_frequency: List[Dict],
        budget: str
    ) -> str:
        """Build dynamic system prompt for GPT-4o coaching generation."""

        # Extract top foods user eats
        top_foods = [f["food_name"] for f in food_frequency[:5]] if food_frequency else []
        top_foods_str = ", ".join(top_foods) if top_foods else "No history yet"

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
- Budget: {budget}
- Foods user eats often: {top_foods_str}
- Current meal: {food_list}

**Personalized RDV (Recommended Daily Values):**
- Calories: {user_rdv.get('calories', 0):.0f} kcal
- Protein: {user_rdv.get('protein', 0):.1f}g
- Carbs: {user_rdv.get('carbs', 0):.1f}g
- Fat: {user_rdv.get('fat', 0):.1f}g
- Iron: {user_rdv.get('iron', 0):.1f}mg
- Calcium: {user_rdv.get('calcium', 0):.1f}mg
- Vitamin A: {user_rdv.get('vitamin_a', 0):.1f}mcg
- Zinc: {user_rdv.get('zinc', 0):.1f}mg

**User's Weekly Average Intake (Last 7 days):**
- Calories: {week1_averages.get('calories', 0):.1f} kcal
- Protein: {week1_averages.get('protein', 0):.1f}g
- Carbs: {week1_averages.get('carbs', 0):.1f}g
- Fat: {week1_averages.get('fat', 0):.1f}g
- Iron: {week1_averages.get('iron', 0):.1f}mg
- Calcium: {week1_averages.get('calcium', 0):.1f}mg
- Vitamin A: {week1_averages.get('vitamin_a', 0):.1f}mcg
- Zinc: {week1_averages.get('zinc', 0):.1f}mg

**Nutrient Trends (Week-over-Week):**
- Improving: {', '.join(improving_nutrients) if improving_nutrients else 'None'}
- Declining: {', '.join(declining_nutrients) if declining_nutrients else 'None'}

**Current Nutritional Gaps:**
{gap_summary_str}

**Primary Focus:** {primary_gap.upper()}

**Your Task:**
Generate a JSON response with the following structure:
{{
    "personalized_message": "Warm, personalized message (2-3 sentences) celebrating what they ate and providing context-aware guidance. Reference specific foods and trends if applicable.",
    "nutrient_insights": [
        {{
            "nutrient": "iron",
            "current_value": 8.5,
            "recommended_daily_value": 18.0,
            "percentage_met": 47.2,
            "status": "deficient" | "adequate" | "optimal",
            "advice": "Specific advice for this nutrient"
        }},
        // Include insights for PRIMARY GAP + top 2-3 other important nutrients
    ],
    "meal_suggestions": [],  // Empty for now (Phase 5)
    "motivational_tip": "Encouraging tip based on their progress and phase",
    "next_steps": [
        "Actionable step 1 (specific to primary gap)",
        "Actionable step 2 (budget-aware)",
        "Actionable step 3 (logging reminder)"
    ],
    "tone": "encouraging"
}}

**Guidelines:**
1. Be warm, supportive, and culturally aware
2. Use Nigerian food names and context
3. Reference user's actual history (foods they eat, trends)
4. Celebrate improvements and streaks
5. For learning phase: Be gentle and educational
6. For post-learning: Be specific and actionable
7. Keep messages concise and practical
8. Focus on budget-aware recommendations ({budget} budget)

Generate the JSON now:"""

        return prompt

    def _fallback_coaching(
        self,
        food_list: str,
        is_learning_phase: bool,
        primary_gap: str,
        gaps: Dict[str, Dict],
        user_rdv: Dict[str, float]
    ) -> Dict[str, Any]:
        """Simple fallback coaching if GPT-4o fails."""
        logger.warning("Using fallback coaching template")

        if is_learning_phase:
            message = f"Great job logging your meal: {food_list}! Keep tracking your meals to help me learn your eating patterns."
            tip = "You're building a healthy habit by logging your meals. Consistency is key!"
        else:
            gap_data = gaps.get(primary_gap, {})
            message = f"Thanks for logging {food_list}. Your {primary_gap} intake could use attention - you're at {gap_data.get('percent_met', 0):.0f}% of your daily goal."
            tip = f"Focus on adding {primary_gap}-rich Nigerian foods to boost your nutrition."

        # Generate insights for top 3 nutrients
        insights = []
        for nutrient in list(gaps.keys())[:3]:
            data = gaps[nutrient]
            insights.append({
                "nutrient": nutrient,
                "current_value": data["current"],
                "recommended_daily_value": data["target"],
                "percentage_met": data["percent_met"],
                "status": "deficient" if data["percent_met"] < 70 else "adequate",
                "advice": f"Aim for {data['target']:.1f} per day. You're currently at {data['current']:.1f}."
            })

        return {
            "personalized_message": message,
            "nutrient_insights": insights,
            "meal_suggestions": [],
            "motivational_tip": tip,
            "next_steps": [
                f"Add {primary_gap}-rich foods to your next meal",
                "Log your next meal to track progress",
                "Keep up your logging streak!"
            ],
            "tone": "encouraging"
        }

    def _tool_generate_nutrition_insights(
        self,
        knowledge_result: KnowledgeResult,
        user_context: Dict[str, Any]
    ) -> str:
        """
        DEPRECATED: Old hardcoded nutrition insights tool.

        This method is DEPRECATED and replaced by _generate_dynamic_coaching().
        Kept for backward compatibility only.

        NEW APPROACH: Use provide_coaching() with user_id instead.

        Args:
            knowledge_result: Nutrition data to analyze
            user_context: User context (age, pregnancy, goals)

        Returns:
            JSON string with coaching insights
        """
        logger.warning("⚠️  DEPRECATED: Using old hardcoded coaching logic. Migrate to provide_coaching(user_id)")

        # Extract user context
        is_pregnant = user_context.get("is_pregnant", False)
        health_goals = user_context.get("health_goals", [])
        budget = user_context.get("budget", "mid")

        # Determine appropriate RDVs
        iron_rdv = self.rdv["iron_pregnant"] if is_pregnant else self.rdv["iron"]

        # Calculate nutrient insights
        nutrient_insights = []

        # Iron insight
        iron_percentage = (knowledge_result.total_iron / iron_rdv) * 100
        if iron_percentage < 30:
            iron_status = "deficient"
            iron_advice = (
                "Your iron intake is quite low. Iron is crucial for preventing anemia, "
                "especially for Nigerian women. Try adding iron-rich foods like Efo Riro "
                "(spinach soup), beans, or organ meats to your meals."
            )
        elif iron_percentage < 70:
            iron_status = "adequate"
            iron_advice = (
                "You're getting some iron, but there's room for improvement. Consider adding "
                "more leafy greens like Efo Riro or protein sources like beans to boost your intake."
            )
        else:
            iron_status = "optimal"
            iron_advice = (
                "Excellent work! Your iron intake is good. Keep including iron-rich foods "
                "like leafy greens and proteins in your meals."
            )

        nutrient_insights.append({
            "nutrient": "iron",
            "current_value": round(knowledge_result.total_iron, 2),
            "recommended_daily_value": iron_rdv,
            "percentage_met": round(iron_percentage, 1),
            "status": iron_status,
            "advice": iron_advice
        })

        # Protein insight
        protein_percentage = (knowledge_result.total_protein / self.rdv["protein"]) * 100
        if protein_percentage < 30:
            protein_status = "deficient"
            protein_advice = (
                "Your protein intake is low. Protein is essential for body repair and strength. "
                "Try adding affordable protein like beans, eggs, or fish to your meals."
            )
        elif protein_percentage < 70:
            protein_status = "adequate"
            protein_advice = (
                "You're getting decent protein, but you can do better. Consider adding more "
                "protein sources like Moi Moi (bean pudding), fish, or chicken."
            )
        else:
            protein_status = "optimal"
            protein_advice = (
                "Great job on protein! You're meeting your body's needs well. "
                "Keep including protein in each meal."
            )

        nutrient_insights.append({
            "nutrient": "protein",
            "current_value": round(knowledge_result.total_protein, 2),
            "recommended_daily_value": self.rdv["protein"],
            "percentage_met": round(protein_percentage, 1),
            "status": protein_status,
            "advice": protein_advice
        })

        # Calcium insight
        calcium_percentage = (knowledge_result.total_calcium / self.rdv["calcium"]) * 100
        if calcium_percentage < 30:
            calcium_status = "deficient"
            calcium_advice = (
                "Your calcium intake needs attention. Calcium is vital for strong bones, "
                "especially during pregnancy. Try adding more dairy, fish with bones, or "
                "leafy greens to your diet."
            )
        elif calcium_percentage < 70:
            calcium_status = "adequate"
            calcium_advice = (
                "You're getting some calcium, but more would be beneficial. Consider adding "
                "foods like milk, sardines, or vegetables to boost your intake."
            )
        else:
            calcium_status = "optimal"
            calcium_advice = (
                "Wonderful! Your calcium intake is strong. This is great for your bone health."
            )

        nutrient_insights.append({
            "nutrient": "calcium",
            "current_value": round(knowledge_result.total_calcium, 2),
            "recommended_daily_value": self.rdv["calcium"],
            "percentage_met": round(calcium_percentage, 1),
            "status": calcium_status,
            "advice": calcium_advice
        })

        # Calorie insight
        calorie_percentage = (knowledge_result.total_calories / self.rdv["calories"]) * 100
        if calorie_percentage < 50:
            calorie_status = "deficient"
            calorie_advice = (
                "Your calorie intake seems low for this meal. Make sure you're eating "
                "enough throughout the day to maintain your energy and health."
            )
        elif calorie_percentage > 120:
            calorie_status = "excessive"
            calorie_advice = (
                "This meal is quite high in calories. Consider balancing with lighter meals "
                "throughout the day."
            )
        else:
            calorie_status = "optimal"
            calorie_advice = (
                "Your calorie intake is well-balanced. Keep up the good work!"
            )

        nutrient_insights.append({
            "nutrient": "calories",
            "current_value": round(knowledge_result.total_calories, 2),
            "recommended_daily_value": self.rdv["calories"],
            "percentage_met": round(calorie_percentage, 1),
            "status": calorie_status,
            "advice": calorie_advice
        })

        # Generate personalized message
        foods_eaten = [food.name for food in knowledge_result.foods]
        personalized_message = self._generate_personalized_message(
            foods_eaten=foods_eaten,
            nutrient_insights=nutrient_insights,
            is_pregnant=is_pregnant
        )

        # Generate motivational tip
        motivational_tip = self._generate_motivational_tip(
            nutrient_insights=nutrient_insights,
            is_pregnant=is_pregnant
        )

        # Generate next steps
        next_steps = self._generate_next_steps(nutrient_insights, budget)

        # Build result
        result = {
            "personalized_message": personalized_message,
            "nutrient_insights": nutrient_insights,
            "meal_suggestions": [],  # Would call suggest_meals tool if needed
            "motivational_tip": motivational_tip,
            "next_steps": next_steps,
            "tone": "encouraging"
        }

        logger.info(f"   📊 Generated {len(nutrient_insights)} nutrient insights")

        return json.dumps(result)

    def _generate_personalized_message(
        self,
        foods_eaten: List[str],
        nutrient_insights: List[Dict[str, Any]],
        is_pregnant: bool
    ) -> str:
        """Generate a warm, personalized message based on the meal."""
        food_list = ", ".join(foods_eaten)

        # Find the nutrient with best status
        good_nutrients = [
            ni for ni in nutrient_insights
            if ni["status"] in ["optimal", "adequate"]
        ]

        # Find nutrients needing attention
        needs_attention = [
            ni for ni in nutrient_insights
            if ni["status"] == "deficient"
        ]

        message_parts = []

        # Opening - celebrate what they ate
        message_parts.append(
            f"Thank you for logging your meal: {food_list}! "
            "I'm here to help you make the most of your nutrition journey."
        )

        # Celebrate strengths
        if good_nutrients:
            good_nutrient_names = [ni["nutrient"] for ni in good_nutrients[:2]]
            message_parts.append(
                f"You're doing well with your {' and '.join(good_nutrient_names)} intake! "
                "Keep up the great work."
            )

        # Gentle guidance for improvements
        if needs_attention:
            need_names = [ni["nutrient"] for ni in needs_attention]
            if len(need_names) == 1:
                message_parts.append(
                    f"I noticed your {need_names[0]} intake could use a boost. "
                    "This is important for your health, especially as a Nigerian woman."
                )
            else:
                message_parts.append(
                    f"I noticed your {' and '.join(need_names)} intake could use some attention. "
                    "Let's work together to improve these areas."
                )

        # Pregnancy-specific encouragement
        if is_pregnant:
            message_parts.append(
                "As an expecting mother, your nutrition is especially important - "
                "you're feeding both yourself and your baby. You're doing great by tracking!"
            )

        return " ".join(message_parts)

    def _generate_motivational_tip(
        self,
        nutrient_insights: List[Dict[str, Any]],
        is_pregnant: bool
    ) -> str:
        """Generate a motivational tip based on nutrition status."""
        deficient_count = len([ni for ni in nutrient_insights if ni["status"] == "deficient"])

        if deficient_count == 0:
            return (
                "You're making excellent choices! Every healthy meal is an investment "
                "in your wellbeing. Keep nourishing yourself with Nigerian foods you love."
            )
        elif deficient_count == 1:
            return (
                "Small changes make big differences! Adding just one nutrient-rich food "
                "to your meals can transform your health. You've got this!"
            )
        else:
            return (
                "Progress, not perfection! Every step towards better nutrition counts. "
                "Focus on one improvement at a time, and celebrate each victory."
            )

    def _generate_next_steps(
        self,
        nutrient_insights: List[Dict[str, Any]],
        budget: str
    ) -> List[str]:
        """Generate actionable next steps based on nutrition gaps."""
        next_steps = []

        # Find most deficient nutrient
        deficient_nutrients = [
            ni for ni in nutrient_insights
            if ni["status"] == "deficient"
        ]

        if not deficient_nutrients:
            next_steps.append("Continue with your balanced eating habits")
            next_steps.append("Try to log all your meals today to see the full picture")
            return next_steps

        # Prioritize by health impact
        for ni in deficient_nutrients[:2]:  # Top 2 priorities
            nutrient = ni["nutrient"]

            if nutrient == "iron":
                if budget == "low":
                    next_steps.append(
                        "Add affordable iron-rich foods: beans, Efo Riro (spinach), or liver"
                    )
                else:
                    next_steps.append(
                        "Include iron-rich proteins: fish, chicken, or red meat with vegetables"
                    )

            elif nutrient == "protein":
                if budget == "low":
                    next_steps.append(
                        "Boost protein with budget-friendly options: beans, Moi Moi, eggs, or groundnuts"
                    )
                else:
                    next_steps.append(
                        "Add protein to each meal: fish, chicken, or meat with your meals"
                    )

            elif nutrient == "calcium":
                if budget == "low":
                    next_steps.append(
                        "Increase calcium with: sardines (with bones), local milk, or leafy greens"
                    )
                else:
                    next_steps.append(
                        "Add calcium sources: dairy products, fish with bones, or fortified foods"
                    )

        # Always add a tracking reminder
        next_steps.append("Log your next meal to continue tracking your progress")

        return next_steps[:3]  # Max 3 steps to avoid overwhelming

    def _tool_suggest_meals(
        self,
        nutrient_needs: List[str],
        budget: str = "mid",
        meal_type: str = "lunch"
    ) -> str:
        """
        Tool function for suggesting Nigerian meals based on needs.

        Args:
            nutrient_needs: List of nutrients to focus on
            budget: Budget tier (low, mid, high)
            meal_type: Type of meal

        Returns:
            JSON string with meal suggestions
        """
        logger.info(
            f"🔧 Tool: suggest_meals "
            f"(nutrients={nutrient_needs}, budget={budget}, type={meal_type})"
        )

        # Nigerian meal suggestions database (simplified)
        meal_database = {
            "breakfast": [
                {
                    "name": "Akara and Pap",
                    "nutrients": ["protein", "iron"],
                    "budget": "low",
                    "ingredients": ["beans", "pepper", "onion", "corn"]
                },
                {
                    "name": "Bread and Eggs with Tea",
                    "nutrients": ["protein", "calcium"],
                    "budget": "low",
                    "ingredients": ["bread", "eggs", "milk"]
                },
                {
                    "name": "Moi Moi with Ogi",
                    "nutrients": ["protein", "iron"],
                    "budget": "mid",
                    "ingredients": ["beans", "eggs", "crayfish", "corn"]
                }
            ],
            "lunch": [
                {
                    "name": "Efo Riro with Eba",
                    "nutrients": ["iron", "vitamin_a", "calcium"],
                    "budget": "low",
                    "ingredients": ["spinach", "palm oil", "crayfish", "garri"]
                },
                {
                    "name": "Jollof Rice with Chicken",
                    "nutrients": ["protein", "iron"],
                    "budget": "mid",
                    "ingredients": ["rice", "tomatoes", "chicken", "vegetables"]
                },
                {
                    "name": "Egusi Soup with Pounded Yam",
                    "nutrients": ["protein", "iron", "calcium"],
                    "budget": "mid",
                    "ingredients": ["egusi", "leafy vegetables", "meat", "yam"]
                }
            ],
            "dinner": [
                {
                    "name": "Pepper Soup with Fish",
                    "nutrients": ["protein", "calcium", "iron"],
                    "budget": "low",
                    "ingredients": ["fish", "pepper", "spices", "yam"]
                },
                {
                    "name": "Beans and Plantain",
                    "nutrients": ["protein", "iron"],
                    "budget": "low",
                    "ingredients": ["beans", "plantain", "palm oil"]
                },
                {
                    "name": "Okra Soup with Fufu",
                    "nutrients": ["iron", "calcium"],
                    "budget": "mid",
                    "ingredients": ["okra", "fish", "crayfish", "cassava"]
                }
            ]
        }

        # Filter suggestions by meal type and budget
        suggestions = []
        for meal in meal_database.get(meal_type, []):
            # Check if meal matches budget
            meal_budget_tier = {"low": 0, "mid": 1, "high": 2}
            user_budget_tier = {"low": 0, "mid": 1, "high": 2}

            if meal_budget_tier.get(meal["budget"], 0) <= user_budget_tier.get(budget, 1):
                # Check if meal provides needed nutrients
                meal_nutrients = set(meal["nutrients"])
                needed_nutrients = set(nutrient_needs)

                if meal_nutrients & needed_nutrients:  # Intersection
                    suggestions.append({
                        "meal_name": meal["name"],
                        "meal_type": meal_type,
                        "ingredients": meal["ingredients"],
                        "estimated_cost": meal["budget"],
                        "key_nutrients": {
                            nutrient: 0 for nutrient in meal["nutrients"]  # Placeholder
                        },
                        "why_recommended": (
                            f"This meal is rich in {', '.join(list(meal_nutrients & needed_nutrients))} "
                            f"and fits your {budget} budget."
                        )
                    })

        logger.info(f"   ✓ Generated {len(suggestions)} meal suggestions")

        return json.dumps({"meal_suggestions": suggestions[:3]})  # Max 3 suggestions

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
        Parse JSON result into CoachingResult model.

        Args:
            result_dict: Parsed JSON from tool

        Returns:
            Structured CoachingResult
        """
        nutrient_insights = []
        for insight_data in result_dict.get("nutrient_insights", []):
            nutrient_insight = NutrientInsight(**insight_data)
            nutrient_insights.append(nutrient_insight)

        meal_suggestions = []
        for suggestion_data in result_dict.get("meal_suggestions", []):
            meal_suggestion = MealSuggestion(**suggestion_data)
            meal_suggestions.append(meal_suggestion)

        return CoachingResult(
            personalized_message=result_dict.get("personalized_message", ""),
            nutrient_insights=nutrient_insights,
            meal_suggestions=meal_suggestions,
            motivational_tip=result_dict.get("motivational_tip", ""),
            next_steps=result_dict.get("next_steps", []),
            tone=result_dict.get("tone", "encouraging")
        )


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
            vitamin_a=200,
            zinc=1.0
        )

        sample_total_nutrients = NutrientInfo(
            calories=375,  # 250g portion
            protein=12.5,
            carbohydrates=75.0,
            fat=5.0,
            iron=3.75,  # Low iron!
            calcium=125,  # Low calcium!
            vitamin_a=500,
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
