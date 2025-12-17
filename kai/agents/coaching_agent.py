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
                tavily_context=tavily_context  # Pass Tavily research to GPT-4o
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
                f"✅ Generated coaching: {len(coaching_result.nutrient_insights)} insights, "
                f"{len(coaching_result.meal_suggestions)} suggestions (Tavily: {tavily_used})"
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
        tavily_context: Optional[str] = None
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

        # Build context for GPT-4o
        foods_eaten = [food.name for food in knowledge_result.foods]
        if not foods_eaten and user_context is not None and 'vision_foods' in user_context:
            # Fallback to vision agent's detected foods only if no foods in knowledge
            foods_eaten = user_context['vision_foods']

        food_list = ", ".join(foods_eaten)

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
            budget=user_context.get("budget", "mid"),
            meal_quality=meal_quality,
            high_nutrients=high_nutrients,
            low_nutrients=low_nutrients,
            poor_meal_count=poor_meal_count,
            streak_status=streak_status,
            workflow_type=workflow_type,
            tavily_context=tavily_context
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
        budget: str,
        meal_quality: str,
        high_nutrients: Dict[str, float],
        low_nutrients: Dict[str, float],
        poor_meal_count: int,
        streak_status: str,
        workflow_type: str = "food_logging",
        tavily_context: Optional[str] = None
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
- Budget: {budget}
- Foods user eats often: {top_foods_str}
- Current meal: {food_list}

**Current Meal Nutrition (What User Just Logged):**
This meal contains:
- Calories: {knowledge_result.total_calories:.0f} kcal ({(knowledge_result.total_calories/user_rdv.get('calories',2500)*100):.0f}% of daily {user_rdv.get('calories',0):.0f} kcal)
- Protein: {knowledge_result.total_protein:.1f}g ({(knowledge_result.total_protein/user_rdv.get('protein',60)*100):.0f}% of daily {user_rdv.get('protein',0):.1f}g)
- Carbs: {knowledge_result.total_carbohydrates:.1f}g ({(knowledge_result.total_carbohydrates/user_rdv.get('carbs',325)*100):.0f}% of daily {user_rdv.get('carbs',0):.1f}g)
- Fat: {knowledge_result.total_fat:.1f}g ({(knowledge_result.total_fat/user_rdv.get('fat',70)*100):.0f}% of daily {user_rdv.get('fat',0):.1f}g)
- Iron: {knowledge_result.total_iron:.1f}mg ({(knowledge_result.total_iron/user_rdv.get('iron',18)*100):.0f}% of daily {user_rdv.get('iron',0):.1f}mg)
- Calcium: {knowledge_result.total_calcium:.1f}mg ({(knowledge_result.total_calcium/user_rdv.get('calcium',1000)*100):.0f}% of daily {user_rdv.get('calcium',0):.1f}mg)
- Vitamin A: {knowledge_result.total_vitamin_a:.1f}mcg ({(knowledge_result.total_vitamin_a/user_rdv.get('vitamin_a',800)*100):.0f}% of daily {user_rdv.get('vitamin_a',0):.1f}mcg)
- Zinc: {knowledge_result.total_zinc:.1f}mg ({(knowledge_result.total_zinc/user_rdv.get('zinc',8)*100):.0f}% of daily {user_rdv.get('zinc',0):.1f}mg)

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
Generate a SIMPLIFIED JSON response for food logging with ONLY these fields:
{{
    "personalized_message": "3-4 sentence message that MUST include:
        1. Opening celebration/acknowledgment with emojis 🎉
        2. Nutrient overview highlighting 2-3 HIGH nutrients from current meal with percentages and emojis
        3. Mention 1-2 LOW nutrients from current meal (if any) - tone depends on quality and phase
        4. Closing encouragement or action item

        Emoji Guide (USE THESE):
        - 🎉 celebrations
        - ⚡ energy/calories
        - 💪 protein
        - 🍚 carbs
        - 🥑 healthy fats
        - 🩸 iron
        - 🦴 calcium
        - 👁️ vitamin A
        - ✨ zinc

        TONE BASED ON MEAL QUALITY AND PHASE:
        {self._get_tone_instructions(meal_quality, streak_status, is_learning_phase)}",

    "motivational_tip": "Short encouraging tip with emojis. Include streak celebration if relevant (e.g., '5-day streak! 🔥'). Max 1-2 sentences.",

    "next_steps": [
        "Simple actionable step related to meal quality or primary gap (with emoji)",
        "Budget-aware food suggestion (with emoji)",
        "Logging encouragement or streak reminder (with emoji)"
    ]
}}

**IMPORTANT - DO NOT INCLUDE:**
- ❌ nutrient_insights array (redundant - already in personalized_message)
- ❌ meal_suggestions (not needed for quick logging)
- ❌ Research paper citations or sources
- ❌ tone field

**Guidelines:**
1. USE EMOJIS LIBERALLY throughout all fields (personalized_message, motivational_tip, next_steps)
2. Be warm, supportive, and culturally aware
3. Use Nigerian food names and context
4. ALWAYS include nutrient overview in personalized_message (what meal is HIGH in, what it LACKS)
5. Reference user's actual history (foods they eat, trends) when relevant
6. Celebrate improvements and streaks in motivational_tip
7. Keep ALL messages concise (personalized_message: 3-4 sentences, motivational_tip: 1-2 sentences, next_steps: 3 simple items)
8. Focus on budget-aware recommendations ({budget} budget)
9. Adjust tone based on meal quality (see tone instructions above)
10. next_steps should be SIMPLE actions, NO research citations

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
- Vitamin A: {knowledge_result.total_vitamin_a:.1f}mcg ({(knowledge_result.total_vitamin_a/user_rdv.get('vitamin_a',800)*100):.0f}% of daily needs)
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
            - Example: "Excellent choice! 🎉 This meal is a nutrient powerhouse! Packed with protein (45g - 75%) 💪, iron (8mg - 44%) 🩸, and vitamin A (65%) 👁️. You're nourishing your body perfectly! Keep up this amazing work! 🌟"
            """

        elif meal_quality == "good":
            # Good meal - Positive and encouraging
            return """
            😊 ENCOURAGING TONE (good meal):
            - Be positive and supportive
            - Highlight the HIGH nutrients
            - Gently mention what could be better (if relevant)
            - Example: "Great job logging! 🎉 This meal is rich in protein (35g - 58%) 💪 and vitamin A (520mcg - 65%) 👁️. It's a bit low in calcium (9%) 🦴 - consider adding yogurt or milk next time. Overall, great choice! Keep it up!"
            """

        else:  # meal_quality == "okay"
            # Okay meal - Supportive with suggestions
            return """
            💪 SUPPORTIVE TONE (okay meal):
            - Be supportive and constructive
            - Acknowledge what's good
            - Suggest simple improvements
            - Example: "Nice logging! 😊 This meal provides decent energy (calories 25%) ⚡ and some protein (20%) 💪. To make it even better, add some vegetables (for vitamin A 👁️) or dairy (for calcium 🦴). Small additions make a big difference!"
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

    def _food_list_phrase(self, foods: List[str]) -> str:
        # Helper to produce natural food enumeration
        if not foods:
            return "your meal"
        if len(foods) == 1:
            return foods[0]
        if len(foods) == 2:
            return f"{foods[0]} and {foods[1]}"
        return f"{', '.join(foods[:-1])}, and {foods[-1]}"

    def _generate_personalized_message(
        self,
        foods_eaten: List[str],
        nutrient_insights: List[Dict[str, Any]],
        is_pregnant: bool
    ) -> str:
        """Generate a warm, personalized message based on the meal."""
        intro = f"🎉 Great job logging your {self._food_list_phrase(foods_eaten)}! "

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

        message_parts = [intro]

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
            'vitamin_a': (knowledge_result.total_vitamin_a / user_rdv.get('vitamin_a', 800)) * 100,
            'zinc': (knowledge_result.total_zinc / user_rdv.get('zinc', 8)) * 100,
        }

        # Identify high nutrients (>40% RDV)
        high_nutrients = {k: v for k, v in nutrient_percentages.items() if v >= 40}

        # Identify low nutrients (<20% RDV)
        low_nutrients = {k: v for k, v in nutrient_percentages.items() if v < 20}

        # Classify quality
        protein_pct = nutrient_percentages['protein']
        high_count = len(high_nutrients)
        low_count = len(low_nutrients)

        if protein_pct >= 30 and high_count >= 3:
            quality = "excellent"  # High protein + 3+ nutrients above 40%
        elif high_count >= 2:
            quality = "good"  # 2+ nutrients above 40%
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
                    'iron': 0, 'calcium': 0, 'vitamin_a': 0, 'zinc': 0
                }

                for food in meal.get('foods', []):
                    meal_totals['calories'] += food.get('calories', 0)
                    meal_totals['protein'] += food.get('protein', 0)
                    meal_totals['carbohydrates'] += food.get('carbohydrates', 0)
                    meal_totals['fat'] += food.get('fat', 0)
                    meal_totals['iron'] += food.get('iron', 0)
                    meal_totals['calcium'] += food.get('calcium', 0)
                    meal_totals['vitamin_a'] += food.get('vitamin_a', 0)
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
                    total_vitamin_a=meal_totals['vitamin_a'],
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
