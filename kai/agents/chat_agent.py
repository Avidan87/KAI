"""
Chat Agent - KAI's Conversational Interface

Handles all user conversations:
- Nigerian food nutrition queries (ChromaDB first, Tavily fallback)
- User progress and stats (Database)
- Meal feedback after food logging (Database + RDV analysis)
- General health questions
- Learning phase coaching (first 7 days/21 meals)

Uses GPT-4o with function calling + structured prompt + Light CoT.
Enhanced with emoji support and personalized coaching.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from kai.database import (
    get_user_stats,
    get_user,
    get_user_health_profile,
    get_daily_nutrition_totals,
    get_user_meals,
)
from kai.utils import (
    calculate_user_rdv,
    get_nutrient_gap_priority,
    get_primary_nutritional_gap,
)
from kai.rag.chromadb_setup import NigerianFoodVectorDB

load_dotenv()
logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Chat Agent for KAI - handles all conversational interactions.

    Tools:
    - search_foods: Query ChromaDB for Nigerian food nutrition
    - get_user_progress: Fetch user's daily totals, RDV, streaks
    - get_meal_history: Fetch recent meals
    - web_search: Tavily fallback when food not in database
    """

    def __init__(self, openai_api_key: Optional[str] = None, chromadb_path: str = "chromadb_data"):
        """Initialize Chat Agent with GPT-4o and ChromaDB."""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"

        # Initialize ChromaDB
        try:
            self.vector_db = NigerianFoodVectorDB(
                persist_directory=chromadb_path,
                collection_name="nigerian_foods",
                openai_api_key=api_key
            )
            logger.info("✓ ChatAgent: ChromaDB initialized")
        except Exception as e:
            logger.warning(f"⚠️ ChromaDB initialization failed: {e}")
            self.vector_db = None

        self.tools = self._define_tools()
        self.system_prompt = self._build_system_prompt()

    def _define_tools(self) -> List[Dict]:
        """Define function calling tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_foods",
                    "description": "Search Nigerian food database for GENERAL nutrition information about foods (e.g., 'what is in jollof rice?', 'foods high in iron'). DO NOT use for analyzing meals the user already logged.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Food name or nutrition query (e.g., 'egusi soup', 'foods high in iron')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_last_meal",
                    "description": "Analyze the user's most recently logged meal with personalized coaching feedback. Use when user asks about their last meal, recent food, or wants feedback on what they logged.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_progress",
                    "description": "Get user's nutrition progress: daily totals, RDV targets, streak, health goals. Use when user asks 'how am I doing?', 'my stats', 'my progress'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_weekly": {
                                "type": "boolean",
                                "description": "Include weekly averages and trends",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_meal_history",
                    "description": "Get user's recent meals with nutrition data. Use when user asks about 'what did I eat', 'my meal history', 'recent meals'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of meals to fetch (default 5)",
                                "default": 5
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search web for nutrition info. ONLY use when food NOT found in database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def _build_system_prompt(self) -> str:
        """Build system prompt with structured format + Light CoT."""
        return """# IDENTITY 🎯
You are KAI, an INTELLIGENT, HONEST, and RESULTS-DRIVEN Nigerian nutrition coach. Your job is to help users achieve their health goals through strategic nutrition. You focus on OUTCOMES and PROGRESS, not tracking behavior. You're direct, actionable, and goal-oriented.

# CORE MISSION 🎯
Help users achieve their health goals through:
- ✅ HONEST assessment of nutritional quality
- ✅ GOAL-SPECIFIC guidance (weight loss vs muscle gain vs maintenance)
- ✅ ACTIONABLE fixes with specific food recommendations
- ✅ EDUCATION on why nutrients matter for THEIR goal

# CAPABILITIES 🛠️
You have access to these tools:
1. **search_foods** - Nigerian food database (ChromaDB) for GENERAL food nutrition info
2. **analyze_last_meal** - Analyze user's MOST RECENT logged meal with RDV-based coaching
3. **get_user_progress** - User's daily totals, RDV targets, streaks, learning phase
4. **get_meal_history** - User's recent meals history
5. **web_search** - Web search fallback (ONLY when food not in database)

# INTELLIGENT TOOL ROUTING 🧠
**CRITICAL: Choose the RIGHT tool based on what the user is asking!**

**Questions about LOGGED MEALS** (what they already ate):
  - "How was my last meal?" → analyze_last_meal()
  - "Give me feedback on what I logged" → analyze_last_meal()
  - "Analyze my recent food" → analyze_last_meal()
  - "What do you think about my meal?" → analyze_last_meal()
  ❌ DO NOT use search_foods() for analyzing logged meals!

**Questions about GENERAL FOOD INFO** (not yet logged):
  - "What's in jollof rice?" → search_foods()
  - "Tell me about egusi soup" → search_foods()
  - "What foods are high in iron?" → search_foods()
  ✅ Use search_foods() for general nutrition questions

**Questions about PROGRESS/STATS**:
  - "How am I doing today?" → get_user_progress()
  - "Show my progress" → get_user_progress()
  - "My stats" → get_user_progress(include_weekly=True)

**Questions about MEAL HISTORY**:
  - "What did I eat this week?" → get_meal_history()
  - "Show my recent meals" → get_meal_history()

# COACHING PHILOSOPHY: GOAL-DRIVEN NUTRITION STRATEGIST 🎯

You receive a `feedback_structure` object with every meal analysis containing:
- `calorie_status` - Meal & daily calories vs target (with health goal context)
- `goal_nutrient` - Primary nutrient for their goal (usually protein)
- `critical_gaps` - Nutrients <50% RDV (sorted by goal priority)
- `moderate_gaps` - Nutrients 50-80% RDV (top 2 only)
- `top_win` - Best performing nutrient (for motivation)
- `health_goal` - User's goal (lose_weight, gain_muscle, maintain_weight, general_wellness)

## GOAL-SPECIFIC APPROACH

**Weight Loss (lose_weight):**
Priority: Calorie deficit + High protein + Micronutrients
- Check if calories are appropriate for deficit (not too high, not dangerously low)
- Emphasize protein to preserve muscle and stay full
- Ensure adequate iron and calcium (common deficiencies)

**Muscle Gain (gain_muscle):**
Priority: Calorie surplus + High protein + Carbs
- Check if calories are sufficient for growth
- Emphasize protein for muscle building (target 1.6-2.2g/kg)
- Ensure adequate carbs for energy and recovery

**Maintenance (maintain_weight):**
Priority: Balanced nutrition + Protein adequacy
- Check if calories are close to target
- Focus on overall nutrient balance
- Encourage variety and micronutrient coverage

**General Wellness (general_wellness):**
Priority: Nutrient density + Variety
- Focus on micronutrient coverage
- Encourage diverse food choices
- Support overall health optimization

# DYNAMIC EMOJI USAGE 🎨
**CRITICAL: Use emojis DYNAMICALLY based on context - NOT hardcoded patterns!**

Choose emojis that match:
- **Meal quality:** 🎉✨ for excellent, 💡⚠️ for needs improvement
- **Specific foods:** 🍚 rice, 🥘 stew, 🐟 fish, 🥬 veggies, 🍗 chicken
- **Nutrients:** 💪 protein, 🦴 calcium, 🩸 iron, ⚡ energy/calories
- **Progress:** 🔥 streaks, 📊 stats, 📈 improvement, 📉 decline
- **Tone:** 👏 approval, 💡 tips, ⚠️ gentle warnings, 🎯 goals

**Rules:**
- Match emojis to actual meal content (if they ate fish, use 🐟)
- Use achievement emojis ONLY when deserved
- Use warning emojis when genuinely needed
- Vary emojis - don't repeat same pattern every response
- Let the DATA guide your emoji choice, not a template

# LEARNING PHASE ADAPTATION 🎓

The tool `analyze_last_meal` returns a `learning_phase` object with:
- `is_learning` (boolean) - true if user has logged < 21 meals

**CRITICAL: Adapt your TONE based on learning phase - NOT what you tell them!**

## 📚 LEARNING PHASE (First 21 meals, is_learning: true)
**Tone:** Gentle, Encouraging, Educational

**Approach:**
- ✅ Softer delivery on bad news
- ✅ More encouraging on good choices
- ✅ Explain WHY nutrients matter (they're still learning)
- ✅ Give 1 clear suggestion (don't overwhelm)

**Example Tone Differences:**

Poor Meal - Learning Phase:
"Your jollof rice gave you energy, but your body needs protein too to stay full and build strength. Try adding grilled chicken or fish next time! 💪"

Poor Meal - Active Phase:
"Jollof rice alone won't cut it - you're at only 12% protein. Add grilled chicken or fish to hit your goals! 💪"

**Key Point:** Same data, different delivery. Learning = gentler, Active = more direct.

## 🎯 ACTIVE COACHING PHASE (After 21 meals, is_learning: false)
**Tone:** Direct, Firm, Results-Focused

**Approach:**
- ✅ More direct about problems
- ✅ Higher expectations for nutrition quality
- ✅ Show ALL critical gaps (not hiding truth)
- ✅ Can be firm about poor choices (still kind)

**KEY DIFFERENCE:**
- Learning Phase: "Try adding protein..." (softer suggestion)
- Active Phase: "You need protein - add chicken or fish!" (direct command)
- **Both phases show the SAME nutritional data!** Only tone changes.

# RESPONSE STRUCTURE 📝

When using `analyze_last_meal` tool, you receive:
- `meal` - Food names, totals, meal type
- `feedback_structure` - **USE THIS!** Goal-driven structured feedback
- `learning_phase` - Tone adjustment (gentle vs direct)
- `streak` - Logging streak (ONLY mention on first meal of new day!)
- `meal_quality` - Quality score for context

## NEW GOAL-DRIVEN FEEDBACK FORMAT 🎯

**CRITICAL: Use `feedback_structure` object for ALL meal feedback!**

The `feedback_structure` contains:
1. `calorie_status` - Meal + daily calories vs target (with goal context)
2. `goal_nutrient` - Primary nutrient (usually protein) with gap
3. `critical_gaps` - Nutrients <50% RDV (sorted by goal priority)
4. `moderate_gaps` - Nutrients 50-80% RDV (top 2)
5. `top_win` - Best performing nutrient (motivation)

## Response Structure (Adapt to Learning vs Active Phase):

### 🟢 EXCELLENT MEAL (Few/no gaps, good balance)

**Learning Phase:**
"[Food combo]! You're getting [goal_nutrient] ([amount]g, [%] of target) 💪 and [top_win nutrient] is strong at [%]! [Why it matters for their goal]. Keep this up! 🎯"

**Active Phase:**
"THIS is what I'm talking about! 🔥 [Food combo] hitting [goal_nutrient] at [%] and [calorie_status]. [top_win] is excellent! This is the nutrition that drives [goal outcome]! 💪"

### 🟡 OKAY MEAL (1-2 moderate gaps)

**Learning Phase:**
"[Food combo] gave you good [calorie_status], but your body needs more [goal_nutrient] ([current]g, [%] of target). Try adding [specific Nigerian food] next time! 💡"

**Active Phase:**
"Good energy but you're light on [goal_nutrient] ([%]) and [moderate_gap_1] ([%]). Add [specific food] to hit your [health_goal] targets! 🎯"

### 🔴 POOR MEAL (Multiple critical gaps)

**Learning Phase:**
"[Food combo] gave energy, but you're missing key nutrients: [goal_nutrient] at only [%], [critical_gap_1], and [critical_gap_2]. Your body needs these for [goal outcome]. Next meal: Add [protein source] + [veggie]! 💪"

**Active Phase:**
"I need to be honest - [food combo] won't get you to your [health_goal] goal. Critical gaps: [goal_nutrient] ([%]), [critical_gap_1] ([%]), [critical_gap_2] ([%]). Next meal needs: [specific fixes]. Let's get back on track! 🎯"

## CALORIE STATUS RULES 📊

**ALWAYS mention calories using `calorie_status`:**

**For Weight Loss:**
- Status "on_track" or "under": "Good calorie control at [X] cal ([%] of target)!"
- Status "over": "You're at [X] cal ([%] of target) - watch portion sizes for weight loss!"

**For Muscle Gain:**
- Status "on_track" or "over": "Great - [X] cal ([%] of target) fueling growth!"
- Status "under": "You're only at [%] of calorie target - eat more to build muscle!"

**For Maintenance/Wellness:**
- Status "on_track": "[X] cal - right on target!"
- Status "over/under": "[X] cal ([%] of target) - aim for closer to [target]"

## CRITICAL RULES:
- ✅ ALWAYS use `feedback_structure` data (not raw nutrient gaps!)
- ✅ ALWAYS mention calories with goal context
- ✅ Focus on `goal_nutrient` (usually protein) first
- ✅ Show ALL `critical_gaps` (don't hide problems!)
- ✅ Only show `top_win` if it exists (excellent meals)
- ✅ Keep it 3-5 sentences max
- ✅ Vary language - don't copy examples verbatim

**STREAK CELEBRATION 🔥**
The `streak` field shows consecutive days of logging.

**CRITICAL RULE: Only mention streak on FIRST meal of a NEW day!**

Check if this is likely the first meal of the day:
- If `daily_nutrient_percentages.calories` is LOW (<30%), it's probably first meal → mention streak
- If `daily_nutrient_percentages.calories` is HIGH (>40%), it's probably 2nd/3rd meal → DON'T mention streak

**When to celebrate streak (on first meal only):**
- ✅ Streak ≥ 7 days: BIG celebration! "7-day streak! 🔥 That's the consistency that drives results!"
- ✅ Streak ≥ 14 days: HUGE! "14 days straight! 🔥🔥 You're building unstoppable momentum!"
- ✅ Streak ≥ 30 days: MASSIVE! "30-DAY STREAK! 🔥🔥🔥 This is next-level commitment!"
- ✅ Streak 3-6 days: Quick nod. "Day [X] streak going! 🔥"
- ❌ Streak 1-2 days: Don't mention

**Examples:**
First meal of day (calories ~20-30%):
"[Meal feedback]... Plus you're on a 7-day streak! 🔥 That consistency is key!"

Second meal of day (calories ~60%):
"[Meal feedback only - NO streak mention]"

## Example Responses Using NEW Format 🌟

### Example 1: EXCELLENT Meal - Weight Loss Goal (Active Phase)
Tool returns:
- Foods: Egusi soup (300g) + Grilled fish (150g) + Wheat fufu (200g)
- feedback_structure.calorie_status: 720 cal (36% daily, status: on_track)
- feedback_structure.goal_nutrient: protein 48g (85% target, status: excellent)
- feedback_structure.critical_gaps: []
- feedback_structure.top_win: iron (82%)

Response:
"THIS is what I'm talking about! 🔥 Egusi + grilled fish + wheat fufu is hitting 48g protein (85% of your goal) and 720 cal - perfect for weight loss! Your iron is crushing it at 82% 🩸. This is the kind of nutrition that keeps you full while burning fat! 💪"

### Example 2: OKAY Meal - Muscle Gain Goal (Learning Phase)
Tool returns:
- Foods: Jollof rice (400g) + Fried plantain (100g)
- feedback_structure.calorie_status: 780 cal (26% daily, status: under)
- feedback_structure.goal_nutrient: protein 14g (18% target, status: low)
- feedback_structure.moderate_gaps: [iron: 55%, zinc: 62%]

Response:
"Your jollof rice and plantain gave you energy (780 cal), but for muscle gain you need more - you're only at 26% of your calorie target! 🎯 Protein is at 14g (18% of goal). Try adding grilled chicken or fish next time to fuel muscle growth! 💪"

### Example 3: POOR Meal - Weight Loss Goal (Active Phase, FIRST meal of day with 7-day streak)
Tool returns:
- Foods: White rice (500g)
- feedback_structure.calorie_status: 650 cal (36% daily, status: on_track)
- feedback_structure.goal_nutrient: protein 6g (10% target, status: low)
- feedback_structure.critical_gaps: [protein: 10%, iron: 8%, calcium: 12%, zinc: 15%]
- daily_nutrient_percentages.calories: 22% (indicates first meal)
- streak: 7

Response:
"I need to be honest - white rice alone won't get you to your weight loss goal. Critical gaps: protein at only 10% (you need +50g today!), iron 8%, calcium 12%. Next meal needs: grilled chicken/fish 🐟 + veggies (ugwu 🥬) + maybe beans. You're on a 7-day streak! 🔥 Let's keep that momentum with better nutrition! 💪"

**CRITICAL RULES FOR NEW FORMAT:**
- ✅ ALWAYS use `feedback_structure` object (not raw nutrient_gaps!)
- ✅ ALWAYS mention calories with goal context from `calorie_status`
- ✅ ALWAYS show `goal_nutrient` first (usually protein)
- ✅ ALWAYS show ALL `critical_gaps` (don't hide problems!)
- ✅ Mention `top_win` only for excellent meals
- ✅ Adapt TONE based on `learning_phase.is_learning`
- ✅ Mention streak ONLY on first meal of day (check daily_nutrient_percentages.calories < 30%)
- ❌ NEVER mention meal counts (#8, "after 25 meals", etc.)
- ❌ NEVER say "great job logging!" - focus on NUTRITION quality
- ❌ NEVER praise objectively poor meals

# EXAMPLE SCENARIOS - BEFORE vs AFTER 🔄

**Scenario: White rice only, Weight Loss Goal**
❌ OLD: "Great job logging! 🎉 Your rice gave you 500 calories!"
✅ NEW: "White rice alone (650 cal, 36% of target) won't drive weight loss. You're critically low on protein (6g, only 10% of goal), iron (8%), and calcium (12%). Next meal: Add grilled chicken 🍗 + ugwu 🥬 to fix these gaps! 💪"

**Scenario: Jollof + plantain, Muscle Gain Goal**
❌ OLD: "Nice combo! 🍚🍌"
✅ NEW: "Jollof rice and plantain gave you 780 cal - but that's only 26% of your target for muscle gain! You need more food. Protein is at 14g (18% of goal). Add grilled fish 🐟 or chicken to fuel growth! 💪"

**Scenario: Egusi + fish + fufu, Weight Loss Goal (First meal, 7-day streak)**
❌ OLD: "Fantastic meal choice! 🎉"
✅ NEW: "THIS is what I'm talking about! 🔥 Egusi + fish + fufu hitting 48g protein (85% of goal) and 720 cal - perfect calorie control for weight loss! Iron at 82% 🩸. You're on a 7-day streak! 🔥 This is the nutrition that burns fat! 💪"

Remember: You're a RESULTS-DRIVEN NUTRITION STRATEGIST, not a meal tracking cheerleader! Focus on OUTCOMES and GOALS! 🎯"""

    async def chat(
        self,
        user_id: str,
        message: str,
        conversation_history: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.

        Args:
            user_id: User ID for personalized data
            message: User's message
            conversation_history: Previous ChatMessage objects for context

        Returns:
            Dict with success, message, suggestions
        """
        try:
            logger.info(f"💬 ChatAgent: '{message[:50]}...' for user {user_id}")

            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add conversation history (last 10)
            if conversation_history:
                for msg in conversation_history[-10:]:
                    # Handle both dict and Pydantic model
                    if hasattr(msg, "role"):
                        role = msg.role
                        content = msg.content
                    else:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                    messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": message})

            # Call GPT-4o with tools
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )

            assistant_message = response.choices[0].message

            # Handle tool calls
            if assistant_message.tool_calls:
                tool_results = await self._process_tool_calls(
                    assistant_message.tool_calls,
                    user_id
                )

                messages.append(assistant_message)

                for tool_call, result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Get final response
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                final_message = final_response.choices[0].message.content
            else:
                final_message = assistant_message.content

            suggestions = self._generate_suggestions(message)

            logger.info(f"✅ ChatAgent response generated")

            return {
                "success": True,
                "message": final_message,
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"ChatAgent error: {e}", exc_info=True)
            return {
                "success": False,
                "message": "I'm having trouble right now. Please try again.",
                "suggestions": ["Ask about Nigerian foods", "Check your progress"],
                "error": str(e)
            }

    async def _process_tool_calls(self, tool_calls: List, user_id: str) -> List[tuple]:
        """Process tool calls and return results."""
        results = []

        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info(f"   🔧 {name}({args})")

            if name == "search_foods":
                result = await self._search_foods(args.get("query", ""), args.get("limit", 5))
            elif name == "analyze_last_meal":
                result = await self._analyze_last_meal(user_id)
            elif name == "get_user_progress":
                result = await self._get_user_progress(user_id, args.get("include_weekly", False))
            elif name == "get_meal_history":
                result = await self._get_meal_history(user_id, args.get("limit", 5))
            elif name == "web_search":
                result = await self._web_search(args.get("query", ""))
            else:
                result = {"error": f"Unknown tool: {name}"}

            results.append((tool_call, result))

        return results

    async def _search_foods(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search ChromaDB for Nigerian foods."""
        if not self.vector_db:
            return {"error": "Food database not available", "foods": []}

        try:
            results = self.vector_db.search(query, n_results=limit)

            foods = []
            for food in results:
                nutrients = food.get("nutrients_per_100g", {})
                foods.append({
                    "name": food.get("name", "Unknown"),
                    "per_100g": {
                        "calories": nutrients.get("calories", 0),
                        "protein": nutrients.get("protein", 0),
                        "carbs": nutrients.get("carbohydrates", 0),
                        "fat": nutrients.get("fat", 0),
                        "iron": nutrients.get("iron", 0),
                        "calcium": nutrients.get("calcium", 0),
                        "potassium": nutrients.get("potassium", 0),
                        "zinc": nutrients.get("zinc", 0),
                    }
                })

            logger.info(f"   → Found {len(foods)} foods")
            return {"foods": foods, "source": "nigerian_food_database"}

        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return {"error": str(e), "foods": []}

    async def _analyze_last_meal(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user's most recently logged meal with RDV-based coaching.

        Returns comprehensive analysis including:
        - Meal details (foods, portions, nutrients)
        - RDV-based analysis (% of daily goals met)
        - Learning phase status
        - Nutrient gap analysis
        - Coaching insights
        """
        try:
            # Fetch last meal
            meals = await get_user_meals(user_id, limit=1)
            if not meals or len(meals) == 0:
                return {"error": "No meals logged yet", "message": "Log your first meal to get personalized feedback! 🍽️"}

            last_meal = meals[0]

            # Fetch user profile and stats
            profile = await get_user_health_profile(user_id)
            user_stats = await get_user_stats(user_id)
            daily_totals = await get_daily_nutrition_totals(user_id)

            if not profile:
                return {"error": "User profile not found"}

            # Get user RDV
            rdv = profile.get("rdv", {})

            # Calculate learning phase
            total_meals = user_stats.get("total_meals_logged", 0) if user_stats else 0
            learning_phase = total_meals < 21  # First 21 meals = learning phase

            # Extract meal info
            meal_foods = last_meal.get("foods", [])
            meal_type = last_meal.get("meal_type", "meal")
            meal_time = last_meal.get("meal_time", "")

            # Calculate meal totals from individual foods
            # (get_user_meals doesn't return totals, only individual foods)
            meal_totals = {
                "calories": 0.0,
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "iron": 0.0,
                "calcium": 0.0,
                "potassium": 0.0,
                "zinc": 0.0,
            }

            for food in meal_foods:
                meal_totals["calories"] += food.get("calories", 0)
                meal_totals["protein"] += food.get("protein", 0)
                meal_totals["carbs"] += food.get("carbohydrates", 0)
                meal_totals["fat"] += food.get("fat", 0)
                meal_totals["iron"] += food.get("iron", 0)
                meal_totals["calcium"] += food.get("calcium", 0)
                meal_totals["potassium"] += food.get("potassium", 0)
                meal_totals["zinc"] += food.get("zinc", 0)

            # Calculate meal size classification
            meal_calories = meal_totals.get("calories", 0)
            rdv_calories = rdv.get("calories", 2000)
            meal_percentage = (meal_calories / rdv_calories * 100) if rdv_calories > 0 else 0

            if meal_percentage < 20:
                meal_size = "light"
                meal_emoji = "🍃"
            elif meal_percentage < 35:
                meal_size = "moderate"
                meal_emoji = "🍽️"
            else:
                meal_size = "heavy"
                meal_emoji = "🍖"

            # Calculate nutrient percentages for this meal
            meal_nutrient_percentages = {}
            for nutrient in ["calories", "protein", "carbs", "fat", "iron", "calcium", "potassium", "zinc"]:
                target = rdv.get(nutrient, 1)
                current = meal_totals.get(nutrient, 0)
                meal_nutrient_percentages[nutrient] = round((current / target) * 100, 1) if target > 0 else 0

            # Calculate daily progress after this meal
            daily_nutrient_percentages = {}
            if daily_totals and rdv:
                for nutrient in ["calories", "protein", "carbs", "fat", "iron", "calcium", "potassium", "zinc"]:
                    target = rdv.get(nutrient, 1)
                    current = daily_totals.get(nutrient, 0)
                    daily_nutrient_percentages[nutrient] = round((current / target) * 100, 1) if target > 0 else 0

            # Identify nutrient gaps (nutrients below 70% after this meal)
            nutrient_gaps = []
            for nutrient, percentage in daily_nutrient_percentages.items():
                if percentage < 70:
                    nutrient_gaps.append({
                        "nutrient": nutrient,
                        "current_percentage": percentage,
                        "target": rdv.get(nutrient, 0),
                        "current": daily_totals.get(nutrient, 0) if daily_totals else 0
                    })

            # Sort gaps by severity (lowest percentage first)
            nutrient_gaps.sort(key=lambda x: x["current_percentage"])

            # Get primary gap (if any)
            primary_gap = nutrient_gaps[0]["nutrient"] if nutrient_gaps else None

            # Get streak
            streak = profile.get("current_logging_streak", 0)

            # Format food names
            food_names = [f.get("food_name", "") for f in meal_foods]

            # Calculate meal quality score (for intelligent coaching)
            meal_quality = self._assess_meal_quality(
                meal_nutrient_percentages=meal_nutrient_percentages,
                num_foods=len(food_names),
                nutrient_gaps=nutrient_gaps
            )

            # Determine if this is a snack based on meal type and calories
            is_snack = meal_type == "snack" or meal_percentage < 20

            # Build structured feedback
            health_goal = profile.get("health_goals", "general_wellness")
            feedback_structure = self._build_meal_feedback_structure(
                meal_totals=meal_totals,
                daily_totals=daily_totals or {},
                rdv=rdv,
                health_goal=health_goal,
                meal_size=meal_size,
                is_snack=is_snack
            )

            return {
                "meal": {
                    "foods": food_names,
                    "meal_type": meal_type,
                    "meal_time": meal_time,
                    "totals": meal_totals,
                    "meal_size": meal_size,
                    "meal_emoji": meal_emoji,
                    "meal_percentage_of_daily": round(meal_percentage, 1)
                },
                "rdv_analysis": {
                    "meal_nutrient_percentages": meal_nutrient_percentages,
                    "daily_nutrient_percentages": daily_nutrient_percentages,
                    "rdv_targets": rdv,
                    "daily_totals": daily_totals or {}
                },
                "learning_phase": {
                    "is_learning": learning_phase,
                    "total_meals_logged": total_meals,
                    "meals_until_complete": max(0, 21 - total_meals)
                },
                "nutrient_gaps": nutrient_gaps,
                "primary_gap": primary_gap,
                "streak": streak,
                "meal_quality": meal_quality,
                "feedback_structure": feedback_structure,
                "coaching_context": {
                    "health_goal": health_goal,
                    "age": profile.get("age", 25),
                    "gender": profile.get("gender", "female")
                }
            }

        except Exception as e:
            logger.error(f"Analyze last meal error: {e}")
            return {"error": str(e)}

    def _get_nutrient_priority_by_goal(self, health_goal: str) -> List[str]:
        """
        Get nutrient priority ranking based on health goal.

        Returns list of nutrients in priority order (most important first).
        """
        priorities = {
            "lose_weight": ["calories", "protein", "iron", "calcium", "zinc"],
            "gain_muscle": ["calories", "protein", "carbs", "iron", "zinc"],
            "maintain_weight": ["protein", "calories", "iron", "calcium", "zinc"],
            "general_wellness": ["protein", "calories", "iron", "calcium", "potassium"]
        }
        return priorities.get(health_goal, priorities["general_wellness"])

    def _build_meal_feedback_structure(
        self,
        meal_totals: Dict[str, float],
        daily_totals: Dict[str, float],
        rdv: Dict[str, float],
        health_goal: str,
        meal_size: str,
        is_snack: bool = False
    ) -> Dict[str, Any]:
        """
        Build structured feedback for meal analysis based on user's health goal.

        Returns:
            - calorie_status: Dict with calorie info vs target & goal
            - goal_nutrient: Primary nutrient to focus on (usually protein)
            - critical_gaps: List of nutrients <50% RDV
            - moderate_gaps: List of nutrients 50-80% RDV
            - top_win: Best performing nutrient (for motivation)
        """
        # Get nutrient priorities for this goal
        priorities = self._get_nutrient_priority_by_goal(health_goal)

        # 1. CALORIE STATUS
        daily_cal = daily_totals.get("calories", 0)
        target_cal = rdv.get("calories", 2000)
        meal_cal = meal_totals.get("calories", 0)
        cal_percentage = (daily_cal / target_cal * 100) if target_cal > 0 else 0

        calorie_status = {
            "meal_calories": meal_cal,
            "daily_calories": daily_cal,
            "target_calories": target_cal,
            "percentage": round(cal_percentage, 1),
            "status": "on_track" if 40 <= cal_percentage <= 120 else ("over" if cal_percentage > 120 else "under"),
            "is_snack": is_snack,
            "meal_size": meal_size
        }

        # 2. GOAL NUTRIENT (usually protein, but depends on goal)
        goal_nutrient_name = "protein"  # Default to protein for most goals
        goal_nutrient_daily = daily_totals.get(goal_nutrient_name, 0)
        goal_nutrient_target = rdv.get(goal_nutrient_name, 1)
        goal_nutrient_pct = (goal_nutrient_daily / goal_nutrient_target * 100) if goal_nutrient_target > 0 else 0

        goal_nutrient = {
            "nutrient": goal_nutrient_name,
            "current": goal_nutrient_daily,
            "target": goal_nutrient_target,
            "percentage": round(goal_nutrient_pct, 1),
            "gap": max(0, goal_nutrient_target - goal_nutrient_daily),
            "status": "excellent" if goal_nutrient_pct >= 80 else ("good" if goal_nutrient_pct >= 50 else "low")
        }

        # 3. CRITICAL GAPS (<50% RDV) - excluding calories
        critical_gaps = []
        for nutrient in ["protein", "carbs", "fat", "iron", "calcium", "potassium", "zinc"]:
            current = daily_totals.get(nutrient, 0)
            target = rdv.get(nutrient, 1)
            percentage = (current / target * 100) if target > 0 else 0

            if percentage < 50:
                critical_gaps.append({
                    "nutrient": nutrient,
                    "current": current,
                    "target": target,
                    "percentage": round(percentage, 1),
                    "gap": target - current
                })

        # Sort by priority for this goal
        critical_gaps.sort(key=lambda x: priorities.index(x["nutrient"]) if x["nutrient"] in priorities else 99)

        # 4. MODERATE GAPS (50-80% RDV) - excluding calories
        moderate_gaps = []
        for nutrient in ["protein", "carbs", "fat", "iron", "calcium", "potassium", "zinc"]:
            current = daily_totals.get(nutrient, 0)
            target = rdv.get(nutrient, 1)
            percentage = (current / target * 100) if target > 0 else 0

            if 50 <= percentage < 80:
                moderate_gaps.append({
                    "nutrient": nutrient,
                    "current": current,
                    "target": target,
                    "percentage": round(percentage, 1),
                    "gap": target - current
                })

        # Sort by priority
        moderate_gaps.sort(key=lambda x: priorities.index(x["nutrient"]) if x["nutrient"] in priorities else 99)

        # 5. TOP WIN (best performing nutrient for motivation)
        top_win = None
        best_percentage = 0
        for nutrient in ["protein", "iron", "calcium", "potassium", "zinc"]:
            current = daily_totals.get(nutrient, 0)
            target = rdv.get(nutrient, 1)
            percentage = (current / target * 100) if target > 0 else 0

            if percentage >= 70 and percentage > best_percentage:
                best_percentage = percentage
                top_win = {
                    "nutrient": nutrient,
                    "percentage": round(percentage, 1),
                    "current": current,
                    "target": target
                }

        return {
            "calorie_status": calorie_status,
            "goal_nutrient": goal_nutrient,
            "critical_gaps": critical_gaps,
            "moderate_gaps": moderate_gaps[:2],  # Top 2 only
            "top_win": top_win,
            "health_goal": health_goal
        }

    def _assess_meal_quality(
        self,
        meal_nutrient_percentages: Dict[str, float],
        num_foods: int,
        nutrient_gaps: List[Dict]
    ) -> Dict[str, Any]:
        """
        Assess meal quality based on nutrient balance and variety.

        Returns a quality assessment to guide intelligent coaching responses.
        """
        protein_pct = meal_nutrient_percentages.get("protein", 0)
        num_gaps = len(nutrient_gaps)

        # Calculate quality score (0-100)
        # Factors: protein adequacy, food variety, nutrient gaps
        score = 0

        # Protein score (0-40 points)
        if protein_pct >= 20:
            score += 40
        elif protein_pct >= 15:
            score += 30
        elif protein_pct >= 10:
            score += 20
        elif protein_pct >= 5:
            score += 10

        # Food variety score (0-30 points)
        if num_foods >= 4:
            score += 30
        elif num_foods >= 3:
            score += 20
        elif num_foods >= 2:
            score += 10

        # Nutrient completeness score (0-30 points)
        if num_gaps == 0:
            score += 30
        elif num_gaps <= 2:
            score += 20
        elif num_gaps <= 4:
            score += 10

        # Determine quality tier
        if score >= 70:
            quality = "excellent"
            emoji = "🟢"
            message = "This is a well-balanced meal!"
        elif score >= 40:
            quality = "okay"
            emoji = "🟡"
            message = "Decent meal, but could be improved"
        else:
            quality = "poor"
            emoji = "🔴"
            message = "This meal needs significant improvement"

        return {
            "score": score,
            "quality": quality,
            "emoji": emoji,
            "message": message,
            "protein_adequate": protein_pct >= 15,
            "has_variety": num_foods >= 3,
            "num_gaps": num_gaps
        }

    async def _get_user_progress(self, user_id: str, include_weekly: bool = False) -> Dict[str, Any]:
        """Get user's nutrition progress."""
        try:
            profile = await get_user_health_profile(user_id)
            daily_totals = await get_daily_nutrition_totals(user_id)

            if not profile:
                return {"error": "User profile not found"}

            rdv = profile.get("rdv", {})

            progress = {
                "daily_totals": daily_totals or {},
                "targets": rdv,
                "streak": profile.get("current_logging_streak", 0),
                "health_goal": profile.get("health_goals", "general_wellness"),
            }

            # Calculate percentages
            if daily_totals and rdv:
                progress["percentages"] = {}
                for nutrient in ["calories", "protein", "iron", "calcium"]:
                    target = rdv.get(nutrient, 1)
                    current = daily_totals.get(nutrient, 0)
                    progress["percentages"][nutrient] = round((current / target) * 100, 1) if target > 0 else 0

            if include_weekly:
                stats = await get_user_stats(user_id)
                if stats:
                    progress["weekly"] = {
                        "avg_calories": stats.get("week1_avg_calories", 0),
                        "avg_protein": stats.get("week1_avg_protein", 0),
                        "calories_trend": stats.get("calories_trend", "stable"),
                        "protein_trend": stats.get("protein_trend", "stable"),
                    }

            logger.info(f"   → User progress fetched")
            return progress

        except Exception as e:
            logger.error(f"Get user progress error: {e}")
            return {"error": str(e)}

    async def _get_meal_history(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """Get user's recent meals."""
        try:
            meals = await get_user_meals(user_id, limit=limit)

            formatted = []
            for meal in meals:
                formatted.append({
                    "meal_type": meal.get("meal_type"),
                    "date": meal.get("meal_date"),
                    "time": meal.get("meal_time"),
                    "foods": [f.get("food_name") for f in meal.get("foods", [])],
                    "totals": meal.get("totals", {}),
                })

            logger.info(f"   → Found {len(formatted)} meals")
            return {"meals": formatted}

        except Exception as e:
            logger.error(f"Get meal history error: {e}")
            return {"error": str(e), "meals": []}

    async def _web_search(self, query: str) -> Dict[str, Any]:
        """Search web using Tavily (fallback)."""
        try:
            from kai.mcp_servers.tavily_server import TavilyMCPServer

            loop = asyncio.get_event_loop()
            tavily_server = TavilyMCPServer()

            request = {
                "method": "tools/call",
                "params": {
                    "name": "search_nigerian_nutrition",
                    "arguments": {"query": query, "max_results": 3}
                }
            }

            response = await loop.run_in_executor(None, tavily_server.handle_request, request)

            logger.info(f"   → Tavily search completed")
            return {
                "source": "web_search",
                "answer": response.get("answer", ""),
                "sources": [s.get("url") for s in response.get("sources", [])[:3]]
            }

        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
            return {"error": str(e), "source": "web_search"}

    def _generate_suggestions(self, message: str) -> List[str]:
        """Generate follow-up suggestions based on message context."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["iron", "calcium", "protein", "nutrient"]):
            return ["Show me a meal with this nutrient", "How am I doing today?"]
        elif any(word in message_lower for word in ["progress", "doing", "stats"]):
            return ["What should I eat next?", "Show my meal history"]
        elif any(word in message_lower for word in ["ate", "meal", "lunch", "dinner", "breakfast"]):
            return ["How was that meal?", "Suggest my next meal"]
        else:
            return ["Ask about Nigerian foods", "Check your progress"]


# Singleton
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    """Get or create singleton ChatAgent."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
        logger.info("✓ ChatAgent singleton created")
    return _chat_agent
