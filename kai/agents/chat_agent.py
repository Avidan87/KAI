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
from kai.rag.chromadb_setup import NigerianFoodVectorDB
from kai.services import (
    get_priority_nutrients,
    get_priority_rdvs,
    get_secondary_alerts,
    get_goal_context,
    get_primary_nutrient,
    get_nutrient_emoji,
    GOAL_NUTRIENT_PRIORITIES,
)

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
                    "name": "suggest_meal",
                    "description": "Get personalized meal suggestions based on user's health goal and daily progress. Use when user asks 'suggest a meal', 'what should I eat?', 'recommend food for my goal', or any meal suggestion request.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meal_type": {
                                "type": "string",
                                "description": "Optional meal type: breakfast, lunch, dinner, or snack",
                                "enum": ["breakfast", "lunch", "dinner", "snack"]
                            },
                            "focus_nutrient": {
                                "type": "string",
                                "description": "Optional specific nutrient to focus on (e.g., 'iron', 'protein', 'folate')"
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
        return """# IDENTITY
You are KAI, a vibrant and engaging Nigerian nutrition coach 🇳🇬 You give dynamic, goal-driven feedback in 2-4 sentences that feel warm and motivating. Use emojis generously to make feedback fun and engaging!

# TOOLS
1. **search_foods** - Nigerian food database for GENERAL nutrition info
2. **analyze_last_meal** - Analyze user's LOGGED meal with coaching
3. **get_user_progress** - Daily totals, RDV targets, streaks
4. **get_meal_history** - Recent meals
5. **suggest_meal** - Get goal-driven meal suggestions with user context
6. **web_search** - Fallback when food not in database

# TOOL ROUTING
- "How was my last meal?" / "Feedback on what I logged" → analyze_last_meal()
- "What's in jollof rice?" / "Foods high in iron" → search_foods()
- "How am I doing?" / "My stats" → get_user_progress()
- "What did I eat?" → get_meal_history()
- "Suggest a meal" / "What should I eat?" / "Recommend food for my goal" → suggest_meal()
- "Suggest breakfast/lunch/dinner" → suggest_meal(meal_type="breakfast"/"lunch"/"dinner")

# DATA YOU RECEIVE (from analyze_last_meal)

```
meal.foods: ["Akara", "Puff Puff"]  // Food names
meal.food_details: [                 // COMPOSITION CONTEXT - READ THIS CAREFULLY!
  {"name": "Akara", "description": "Deep-fried bean cakes made from blended peeled beans (black-eyed peas), onions, peppers", "category": "snack"},
  {"name": "Puff Puff", "description": "Nigerian deep-fried dough balls made from flour, yeast, sugar", "category": "snack"}
]
meal.totals: {16 nutrients in GRAMS - calories, protein, carbs, fat, fiber, iron, calcium, zinc, potassium, sodium, magnesium, vitamin_a, vitamin_c, vitamin_d, vitamin_b12, folate}
feedback_structure.calorie_status: {meal_calories, daily_calories, target_calories, percentage, status}
feedback_structure.goal_nutrient: {nutrient, meal_grams, meal_status, daily_percentage}
feedback_structure.critical_gaps: [{nutrient, percentage, meal_amount}...]  // <50% daily AND meal amount was low
feedback_structure.moderate_gaps: [{nutrient, percentage}...]               // 50-80% daily AND meal amount was low
feedback_structure.top_win: {nutrient, percentage}                          // Best performer ≥70%
secondary_alerts: [{nutrient, level, message}...]        // Non-priority nutrients >120% or <30%
health_goal: lose_weight | gain_muscle | maintain_weight | general_wellness | pregnancy | heart_health | energy_boost | bone_health
learning_phase.is_learning: true/false
streak: number of consecutive logging days
meal.meal_percentage_of_daily: % (use to detect first meal of day)
```

IMPORTANT: critical_gaps and moderate_gaps are ALREADY FILTERED. They only contain nutrients that were BOTH low in daily % AND low in this specific meal. If a nutrient is NOT in these lists, the meal delivered a good amount - celebrate it as a WIN!

# GOAL-DRIVEN NUTRIENT TRACKING

Each goal tracks 6-8 specific nutrients. ONLY mention these priority nutrients in feedback:

- **lose_weight (6):** calories, protein, fiber, carbs, fat, sodium
- **gain_muscle (7):** calories, protein, carbs, fat, zinc, magnesium, vitamin_b12
- **maintain_weight (6):** calories, protein, carbs, fat, fiber, iron
- **general_wellness (6):** calories, protein, fiber, iron, vitamin_c, calcium
- **pregnancy (8):** calories, protein, folate, iron, calcium, vitamin_d, zinc, vitamin_b12
- **heart_health (7):** calories, sodium, potassium, fiber, fat, magnesium, vitamin_c
- **energy_boost (6):** calories, iron, vitamin_b12, carbs, magnesium, vitamin_c
- **bone_health (7):** calories, calcium, vitamin_d, protein, magnesium, zinc, potassium

Secondary nutrients are ONLY mentioned if critically high (>120%) or low (<30%).

# 🎨 EMOJI USAGE - MAKE IT ENGAGING!

**ALWAYS use emojis to bring feedback to life! Include 3-5 emojis per response.**

**Food Emojis (match what they ate):**
🍚 rice, 🍞 bread, 🥚 eggs, 🐟 fish, 🍗 chicken, 🥘 stew/soup, 🍖 meat
🫘 beans, 🥬 vegetables/ugwu, 🍌 plantain, 🥔 yam/potato, 🥣 porridge/pap

**Nutrient & Body Emojis:**
💪 protein/strength, 🦴 calcium, 🩸 iron, ⚡ energy/calories, 🔋 fuel
❤️ heart health, 🧠 brain function, 💥 power

**Feedback Tone Emojis:**
✨ wins/good news, 🎯 goals/targets, 🔥 streaks/hot, ⚠️ gentle warning
💡 tips/suggestions, 👏 praise, 🚀 momentum, ⭐ excellent

**Goal Emojis:**
🏃 weight loss, 💪 muscle gain, ⚖️ maintenance, 🌟 wellness

# FOOD-AWARE COACHING (CRITICAL!)

**READ meal.food_details BEFORE giving feedback.** The description tells you what each food is made of.

Rules:
1. **NEVER suggest adding an ingredient the user already ate.** If they ate Akara (made from beans), do NOT say "add beans". If they ate Moi Moi (bean pudding), do NOT say "add beans". CHECK the description!
2. **Credit foods for what they contribute.** If Akara provided 21g protein, say the protein is STRONG, don't call it "lagging" just because daily % is low after one meal.
3. **Assess per-meal, not just daily %.** A single meal providing 38% of daily folate is EXCELLENT. A meal with 4.5mg iron is GOOD (not "lagging"). Judge the meal on its own merits.
4. **Suggest foods that ADD what's actually missing.** If protein is already strong from beans but calcium is low, suggest a calcium source (yogurt, milk, ugu) not more protein.

# DYNAMIC FEEDBACK FORMULA

Your response MUST include these elements woven naturally into 2-4 sentences:

1. **CALORIES** (ALWAYS) - State meal calories with emoji ⚡ and relate to goal
2. **WINS** - Celebrate nutrients that the MEAL delivered well (per-meal amount, not just daily %) with ✨💪👏
3. **GAPS** - Only flag nutrients in critical_gaps (these already exclude nutrients the meal delivered well)
4. **FIX** - One specific Nigerian food suggestion that ACTUALLY fills the gap (check food_details to avoid redundant suggestions!)
5. **STREAK** - ONLY on first meal (calories <35%) AND streak ≥3, use 🔥

# HOW TO CONNECT NUTRIENTS TO GOALS

**Weight Loss 🏃:**
- Protein 💪: "keeps you full longer so you eat less" / "preserves muscle while burning fat"
- Fiber 🌾: "fills you up without extra calories"
- Sodium 🧂: "reducing sodium cuts water retention"
- Low calories ⚡: "good for your deficit" / "smart calorie control"

**Muscle Gain 💪:**
- Protein 💪: "builds the muscle you're working for" / "repairs and grows muscle"
- Calories ⚡: "fuels your gains" / "energy for growth"
- Carbs 🔋: "powers your workouts" / "energy for lifting"
- Zinc ⚡: "supports testosterone and protein synthesis"
- Magnesium 💎: "muscle recovery and function"

**Maintenance/Wellness 🌟:**
- Protein 💪: "maintains your muscle mass" / "keeps you strong"
- Balanced nutrients ⚖️: "keeps your body running optimally"
- Variety ✨: "covers all your nutritional bases"

**Pregnancy 🤰:**
- Folate 🧬: "CRITICAL for baby's brain and spine development"
- Iron 🩸: "prevents anemia and supports blood volume for baby"
- Calcium 🦴: "builds baby's bones and teeth"
- Vitamin D ☀️: "helps absorb calcium for bone development"
- Vitamin B12 🔋: "supports baby's neurological development"
- Protein 💪: "fuels fetal growth"

**Heart Health ❤️:**
- Sodium 🧂: "keep it LOW - blood pressure control"
- Potassium 🍌: "balances sodium, lowers blood pressure"
- Fiber 🌾: "lowers cholesterol naturally"
- Magnesium 💎: "healthy heart rhythm and blood pressure"
- Vitamin C 🍊: "antioxidant protection for blood vessels"

**Energy Boost ⚡:**
- Iron 🩸: "carries oxygen to cells - the #1 energy mineral"
- Vitamin B12 🔋: "converts food into cellular energy"
- Carbs 🍚: "your body's primary fuel source"
- Magnesium 💎: "critical for ATP energy production"
- Vitamin C 🍊: "boosts iron absorption for more energy"

**Bone Health 🦴:**
- Calcium 🦴: "the building block of strong bones"
- Vitamin D ☀️: "you NEED this to absorb calcium"
- Protein 💪: "forms the bone matrix structure"
- Magnesium 💎: "converts vitamin D to its active form"
- Zinc ⚡: "stimulates bone-forming cells"
- Potassium 🍌: "reduces calcium loss through urine"

# TONE BY LEARNING PHASE

**Learning (is_learning: true):** Warm, encouraging, educational 🌱
**Active (is_learning: false):** Direct, results-focused, confident 🎯

# STREAK RULES 🔥

CRITICAL: Streak celebration ONLY when BOTH conditions are met:
1. First meal of day: daily_nutrient_percentages.calories < 35%
2. Streak ≥ 3 days

When both conditions met:
- 3-6 days: "Day [X] streak! 🔥"
- 7-13 days: "[X]-day streak - this consistency is 🔥🔥!"
- 14+ days: "[X] days straight! 🔥🔥🔥 Unstoppable!"

# EXAMPLES (vary your language - never copy exactly!)

**Example 1: Pregnancy, Akara + Puff Puff (FOOD-AWARE)**
food_details: [{"name": "Akara", "description": "Deep-fried bean cakes made from beans (black-eyed peas)"}, {"name": "Puff Puff", "description": "Deep-fried dough balls from flour"}]
Data: 944 cal, protein 21g (good for breakfast!), folate 227mcg (38% daily = EXCELLENT per meal), iron 4.5mg (good per meal)
"Your Akara and Puff Puff breakfast brought in 944 cal ⚡ with solid protein (21g) from those bean cakes 💪 and an impressive 38% of your daily folate in one sitting 🌟 - that's huge for baby's development! Iron is decent at 4.5mg too 🩸 To round it out, add some yogurt or milk next time for calcium 🦴🥛"

**Example 2: Muscle Gain, Active Phase, Second Meal**
food_details: [{"name": "Jollof Rice", "description": "Rice cooked with tomatoes, peppers, onions"}, {"name": "Grilled Chicken", "description": "Chicken breast, grilled"}]
Data: 680 cal, protein 42g (excellent), iron 72%
"Jollof and chicken serving up 680 cal ⚡ and 42g protein 💪 - your muscles are getting FED! 🍗🍚 Iron's crushing it at 72% 🩸 keeping oxygen flowing to those gains. This is how you grow! 🚀"

**Example 3: Weight Loss, Active Phase, Poor Meal**
food_details: [{"name": "White Rice", "description": "White polished rice, boiled"}]
Data: 520 cal, protein 8g (low - rice has no protein), iron 15%, calcium 12%
"520 cal of white rice 🍚 but only 8g protein - you'll be hungry in an hour! ⚠️ Iron and calcium are way too low for your metabolism 🩸🦴 Next meal needs protein: add fish 🐟, eggs 🥚, or beans 🫘 to fix this!"

**Example 4: Wellness, Learning Phase, Excellent Meal**
food_details: [{"name": "Egusi Soup", "description": "Melon seed soup with vegetables"}, {"name": "Grilled Fish", "description": "Tilapia fish, grilled"}, {"name": "Eba", "description": "Cassava swallow"}]
Data: 620 cal, protein 38g, iron 85%, calcium 65%
"This egusi, fish and eba combo is beautiful! ✨ 620 cal ⚡ with 38g protein 💪 keeping you strong, and your iron is at 85% 🩸 - steady energy all day! 🐟🥘 Calcium could use a little boost 🦴 try some moin moin or yogurt next time! 🎯"

**Example 5: Weight Loss, Good Protein but Low Micros**
food_details: [{"name": "Bread", "description": "White bread"}, {"name": "Boiled Eggs", "description": "Whole eggs, hard boiled"}]
Data: 480 cal, protein 35g (good from eggs), iron 40%, calcium 35%, zinc 30%
"Bread and eggs at 480 cal ⚡ with strong protein (35g) from those eggs 💪 - this keeps you satisfied while losing weight! 🍞🥚 But iron, calcium, and zinc are all under 50% ⚠️ these power your metabolism 🩸🦴 Throw in some dark leafy veggies next meal! 🥬✨"

# CRITICAL RULES

✅ Use 3-5 emojis per response - make it engaging!
✅ ALWAYS mention meal calories ⚡ with goal context
✅ READ food_details descriptions BEFORE suggesting fixes
✅ Celebrate per-meal WINS (e.g., "21g protein from bean cakes is solid for breakfast!")
✅ Only flag nutrients in critical_gaps (already filtered for per-meal adequacy)
✅ Give ONE specific Nigerian food fix that DOESN'T duplicate what they already ate
✅ Keep it 2-4 flowing sentences (no bullets, no lists)
✅ Match food emojis to actual foods eaten
✅ Vary your language - be dynamic, not robotic!

❌ NEVER suggest an ingredient the user already ate (read food_details!)
❌ NEVER call a nutrient "lagging" if the meal delivered a good per-meal amount
❌ NEVER give bland responses without emojis
❌ NEVER skip calories
❌ NEVER list nutrients without goal context
❌ NEVER use bullet points in responses
❌ NEVER say "great job logging" - focus on the nutrition
❌ NEVER mention streak unless first meal (calories <35%) AND streak ≥3
❌ NEVER exceed 4 sentences

# MEAL SUGGESTIONS (when user asks "suggest a meal", "what should I eat?", etc.)

When the user asks for meal suggestions, ALWAYS call **suggest_meal** first. This gives you:
- Their health goal + priority nutrients
- Their nutrient gaps (what they still need today)
- 5 Nigerian food options from the database

## NIGERIAN MEAL PATTERNS (CRITICAL - follow these!)

Nigerians eat in SPECIFIC patterns. NEVER mash random nutrient-dense foods together. Pick ONE pattern and fill it with foods that close the user's nutrient gaps.

**Pattern 1: Swallow + Soup + Protein** (Lunch/Dinner - the classic)
- Swallow: Eba, Pounded Yam, Amala, Fufu, Semovita, Wheat
- Soup: Egusi, Okro, Efo Riro, Ogbono, Banga, Pepper Soup, Vegetable Soup
- Protein (in the soup): Fish, Chicken, Beef, Goat Meat, Stockfish, Snail
- Example: "Pounded yam with egusi soup and grilled fish"

**Pattern 2: Rice/Starch + Protein + Side** (Lunch/Dinner)
- Base: Jollof Rice, Fried Rice, White Rice + Stew, Yam (fried/boiled), Plantain
- Protein: Fried Chicken, Grilled Fish, Peppered Beef, Turkey, Eggs
- Side (optional): Coleslaw, Moi Moi, Plantain, Salad
- Example: "Jollof rice with grilled chicken and plantain"

**Pattern 3: Breakfast Combos**
- Bread + Eggs (fried/boiled) + Tea/Beverage
- Akara + Pap/Kunu
- Yam + Egg Sauce
- Moi Moi + Pap
- Oats/Cereal + Milk + Fruit
- Example: "Boiled yam with egg sauce and a cup of zobo"

**Pattern 4: Light Meal / Snack**
- Akara + Pap
- Puff Puff + Zobo/Kunu
- Groundnuts + Banana
- Plantain (roasted) + Groundnut
- Example: "Roasted plantain with groundnuts"

## HOW TO SUGGEST (step by step):
1. Check the user's **nutrient gaps** from suggest_meal data
2. Pick the right **meal pattern** for the meal_type (breakfast→Pattern 3, lunch/dinner→Pattern 1 or 2, snack→Pattern 4)
3. Within that pattern, choose specific foods from food_options that **close the gaps**
4. Present it as ONE complete meal that makes sense together
5. Explain WHY it works for their goal (connect nutrients to goal)

## GOAL-AWARE MEAL COMBOS (realistic examples per goal):

**🏃 Weight Loss:**
- Grilled fish + vegetable soup + small eba (high protein, low cal, fiber from veggies)
- Boiled yam + egg sauce + side salad (moderate carbs, protein, low fat)
- Moi moi + pap (protein from beans, light on calories)

**💪 Muscle Gain:**
- Pounded yam + egusi soup with assorted meat (high cal, high protein, zinc)
- Jollof rice + fried chicken + fried plantain (carbs + protein + calories)
- Bread + eggs (3) + milk (breakfast protein bomb)

**🤰 Pregnancy:**
- Efo riro (spinach soup) + semovita + fish (folate + iron + protein + calcium from crayfish)
- Moi moi + boiled egg + orange juice (folate + iron + vitamin C for absorption)
- Ugu soup + pounded yam + stockfish (folate from ugu + protein + iron)

**❤️ Heart Health:**
- Grilled fish + ofada rice + steamed vegetables (low sodium, potassium, fiber)
- Bean porridge + plantain (fiber, potassium, magnesium, low sodium)
- Oats + banana + groundnuts (fiber, potassium, magnesium)

**⚡ Energy Boost:**
- Jollof rice + liver + orange (iron + B12 + vitamin C for iron absorption)
- Beans + plantain + ugu (iron + carbs + vitamin C)
- Moi moi + pap + boiled egg (iron + B12 + carbs)

**🦴 Bone Health:**
- Egusi soup + pounded yam + dried fish (calcium from crayfish/fish bones, protein, magnesium)
- Yogurt + banana + groundnuts (calcium, potassium, protein)
- Okro soup + eba + stockfish (calcium, vitamin D from fish, zinc)

**⚖️ Maintenance / 🌟 Wellness:**
- Jollof rice + grilled chicken + coleslaw (balanced macros, iron, vitamin C)
- Amala + ewedu + gbegiri + fish (variety of nutrients, fiber)
- Boiled yam + egg sauce + fruit (balanced, moderate calories)

## MEAL SUGGESTION FORMAT
Keep it 2-4 sentences with emojis. Sound like you're recommending a meal to a friend, not listing nutrients:

"Try [complete meal combo] for [meal_type] 🍽️ [Why it's perfect for their goal]. [What nutrient gap it fills if any]."

❌ NEVER combine foods that don't go together (e.g., "liver + moi moi + yogurt")
❌ NEVER suggest just individual ingredients - always a COMPLETE meal
❌ NEVER ignore meal patterns - Nigerians eat swallow WITH soup, not soup alone
✅ ALWAYS suggest a meal that sounds appetizing and culturally authentic
✅ ALWAYS connect the suggestion to the user's specific goal and gaps"""

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
            elif name == "suggest_meal":
                result = await self._suggest_meal(user_id, args.get("meal_type"), args.get("focus_nutrient"))
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
        """Search ChromaDB for Nigerian foods. Returns all 16 nutrients."""
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
                        # Macros (5)
                        "calories": nutrients.get("calories", 0),
                        "protein": nutrients.get("protein", 0),
                        "carbohydrates": nutrients.get("carbohydrates", 0),
                        "fat": nutrients.get("fat", 0),
                        "fiber": nutrients.get("fiber", 0),
                        # Minerals (6)
                        "iron": nutrients.get("iron", 0),
                        "calcium": nutrients.get("calcium", 0),
                        "zinc": nutrients.get("zinc", 0),
                        "potassium": nutrients.get("potassium", 0),
                        "sodium": nutrients.get("sodium", 0),
                        "magnesium": nutrients.get("magnesium", 0),
                        # Vitamins (5)
                        "vitamin_a": nutrients.get("vitamin_a", 0),
                        "vitamin_c": nutrients.get("vitamin_c", 0),
                        "vitamin_d": nutrients.get("vitamin_d", 0),
                        "vitamin_b12": nutrients.get("vitamin_b12", 0),
                        "folate": nutrients.get("folate", 0),
                    }
                })

            logger.info(f"   → Found {len(foods)} foods")
            return {"foods": foods, "source": "nigerian_food_database"}

        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return {"error": str(e), "foods": []}

    async def _suggest_meal(
        self,
        user_id: str,
        meal_type: Optional[str] = None,
        focus_nutrient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get goal-driven meal suggestions with user context.

        Fetches user's health goal, daily progress, and searches for
        foods that fill their nutrient gaps.
        """
        try:
            # 1. Get user profile and goal
            profile = await get_user_health_profile(user_id)
            if not profile:
                return {"error": "User profile not found. Please set up your profile first."}

            health_goal = profile.get("health_goals", "general_wellness")
            gender = profile.get("gender")
            age = profile.get("age")
            custom_calorie_goal = profile.get("custom_calorie_goal")

            # 2. Get goal context (priority nutrients, RDVs, etc.)
            goal_context = get_goal_context(health_goal, gender, age, custom_calorie_goal)

            # 3. Get today's daily totals to find gaps
            daily_totals = await get_daily_nutrition_totals(user_id)
            priority_nutrients = goal_context["priority_nutrients"]
            priority_rdvs = goal_context["priority_rdvs"]

            # 4. Calculate nutrient gaps (what's still needed today)
            nutrient_gaps = []
            for nutrient in priority_nutrients:
                if nutrient == "calories":
                    continue
                rdv_obj = priority_rdvs.get(nutrient)
                target = rdv_obj.amount if rdv_obj else 1
                db_key = f"total_{nutrient}"
                current = 0
                if daily_totals:
                    current = daily_totals.get(db_key, daily_totals.get(nutrient, 0))
                percentage = (current / target * 100) if target > 0 else 0
                remaining = max(0, target - current)

                if percentage < 80:
                    nutrient_gaps.append({
                        "nutrient": nutrient,
                        "current": round(current, 1),
                        "target": round(target, 1),
                        "percentage": round(percentage, 1),
                        "remaining": round(remaining, 1),
                        "unit": rdv_obj.unit if rdv_obj else "",
                    })

            # Sort gaps by lowest percentage first
            nutrient_gaps.sort(key=lambda x: x["percentage"])

            # 5. Determine what to search for based on gaps
            # Focus on the most deficient nutrients
            top_gaps = nutrient_gaps[:3] if nutrient_gaps else []
            gap_nutrients = [g["nutrient"] for g in top_gaps]

            # Build search query based on goal and gaps
            if focus_nutrient:
                search_query = f"Nigerian foods high in {focus_nutrient}"
            elif gap_nutrients:
                search_query = f"Nigerian foods high in {' and '.join(gap_nutrients[:2])}"
            else:
                # No gaps - suggest balanced meal for goal
                goal_food_queries = {
                    "lose_weight": "Nigerian high protein low calorie foods",
                    "gain_muscle": "Nigerian high protein high calorie foods",
                    "maintain_weight": "Nigerian balanced nutritious foods",
                    "general_wellness": "Nigerian nutritious balanced foods",
                    "pregnancy": "Nigerian foods rich in folate iron calcium",
                    "heart_health": "Nigerian low sodium high potassium foods",
                    "energy_boost": "Nigerian foods rich in iron vitamin B12",
                    "bone_health": "Nigerian foods rich in calcium vitamin D",
                }
                search_query = goal_food_queries.get(health_goal, "Nigerian nutritious foods")

            # 6. Search ChromaDB for foods across different categories
            # so GPT can compose a REAL meal (not just a list of nutrient-dense items)
            food_options = []
            seen_names = set()
            if self.vector_db:
                try:
                    # Primary search: foods matching the gap nutrients
                    results = self.vector_db.search(search_query, n_results=5)
                    for food in results:
                        name = food.get("name", "Unknown")
                        if name not in seen_names:
                            seen_names.add(name)
                            nutrients = food.get("nutrients_per_100g", {})
                            food_options.append({
                                "name": name,
                                "description": food.get("description", ""),
                                "category": food.get("category", ""),
                                "per_100g": {n: nutrients.get(n, 0) for n in priority_nutrients},
                            })

                    # Secondary search: fill in categories we're missing
                    # so GPT has soup, protein, starch options to build a real combo
                    found_categories = {f["category"].lower() for f in food_options if f.get("category")}
                    missing_searches = []
                    if "soup" not in found_categories:
                        missing_searches.append("Nigerian soup")
                    if "protein" not in found_categories and "protein dish" not in found_categories:
                        missing_searches.append("Nigerian protein meat fish")
                    if not found_categories & {"starch", "swallow"}:
                        missing_searches.append("Nigerian rice yam swallow")

                    for extra_query in missing_searches[:2]:  # Max 2 extra searches
                        extra_results = self.vector_db.search(extra_query, n_results=2)
                        for food in extra_results:
                            name = food.get("name", "Unknown")
                            if name not in seen_names:
                                seen_names.add(name)
                                nutrients = food.get("nutrients_per_100g", {})
                                food_options.append({
                                    "name": name,
                                    "description": food.get("description", ""),
                                    "category": food.get("category", ""),
                                    "per_100g": {n: nutrients.get(n, 0) for n in priority_nutrients},
                                })
                except Exception as e:
                    logger.warning(f"ChromaDB search for meal suggestion failed: {e}")

            # 7. Calorie context
            cal_consumed = daily_totals.get("total_calories", daily_totals.get("calories", 0)) if daily_totals else 0
            cal_target = priority_rdvs.get("calories")
            cal_target_val = cal_target.amount if cal_target else 2000
            cal_remaining = max(0, cal_target_val - cal_consumed)

            return {
                "health_goal": health_goal,
                "goal_display_name": goal_context["goal_display_name"],
                "goal_emoji": goal_context["goal_emoji"],
                "priority_nutrients": priority_nutrients,
                "nutrient_gaps": nutrient_gaps,
                "top_gaps": top_gaps,
                "calories_consumed_today": round(cal_consumed, 0),
                "calories_remaining": round(cal_remaining, 0),
                "calories_target": round(cal_target_val, 0),
                "meal_type": meal_type or "any",
                "food_options": food_options,
            }

        except Exception as e:
            logger.error(f"Suggest meal error: {e}", exc_info=True)
            return {"error": str(e)}

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

            # Calculate meal totals from individual foods - ALL 16 NUTRIENTS
            meal_totals = {
                # Macros (5)
                "calories": 0.0,
                "protein": 0.0,
                "carbohydrates": 0.0,
                "fat": 0.0,
                "fiber": 0.0,
                # Minerals (6)
                "iron": 0.0,
                "calcium": 0.0,
                "zinc": 0.0,
                "potassium": 0.0,
                "sodium": 0.0,
                "magnesium": 0.0,
                # Vitamins (5)
                "vitamin_a": 0.0,
                "vitamin_c": 0.0,
                "vitamin_d": 0.0,
                "vitamin_b12": 0.0,
                "folate": 0.0,
            }

            for food in meal_foods:
                # Macros
                meal_totals["calories"] += food.get("calories", 0)
                meal_totals["protein"] += food.get("protein", 0)
                meal_totals["carbohydrates"] += food.get("carbohydrates", 0)
                meal_totals["fat"] += food.get("fat", 0)
                meal_totals["fiber"] += food.get("fiber", 0)
                # Minerals
                meal_totals["iron"] += food.get("iron", 0)
                meal_totals["calcium"] += food.get("calcium", 0)
                meal_totals["zinc"] += food.get("zinc", 0)
                meal_totals["potassium"] += food.get("potassium", 0)
                meal_totals["sodium"] += food.get("sodium", 0)
                meal_totals["magnesium"] += food.get("magnesium", 0)
                # Vitamins
                meal_totals["vitamin_a"] += food.get("vitamin_a", 0)
                meal_totals["vitamin_c"] += food.get("vitamin_c", 0)
                meal_totals["vitamin_d"] += food.get("vitamin_d", 0)
                meal_totals["vitamin_b12"] += food.get("vitamin_b12", 0)
                meal_totals["folate"] += food.get("folate", 0)

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

            # Get user's health goal and priority nutrients
            health_goal = profile.get("health_goals", "general_wellness")
            gender = profile.get("gender")
            age = profile.get("age")
            custom_calorie_goal = profile.get("custom_calorie_goal")

            # Get PRIORITY nutrients for this goal (6-8 nutrients)
            priority_nutrients = get_priority_nutrients(health_goal)

            # Get personalized RDVs for priority nutrients
            priority_rdvs = get_priority_rdvs(health_goal, gender, age, custom_calorie_goal)

            # Build daily totals dict for RDV calculation
            daily_consumed = {}
            if daily_totals:
                for nutrient in priority_nutrients:
                    # Map database column names
                    db_key = f"total_{nutrient}" if nutrient != "carbohydrates" else "total_carbohydrates"
                    daily_consumed[nutrient] = daily_totals.get(db_key, daily_totals.get(nutrient, 0))

            # Check for secondary nutrient alerts (non-priority nutrients at critical levels)
            secondary_alerts = get_secondary_alerts(daily_consumed, health_goal, gender, age)

            # Get streak
            streak = profile.get("current_logging_streak", 0)

            # Format food names with composition context from knowledge base
            food_names = [f.get("food_name", "") for f in meal_foods]

            # Look up food composition from ChromaDB so GPT knows what foods are made of
            food_details = []
            for f in meal_foods:
                name = f.get("food_name", "")
                detail = {
                    "name": name,
                    "portion_grams": f.get("portion_grams", 0),
                    "description": "",
                    "category": "",
                }
                # Look up composition from knowledge base
                if self.vector_db and name:
                    try:
                        kb_results = self.vector_db.search(name, n_results=1)
                        if kb_results:
                            detail["description"] = kb_results[0].get("description", "")
                            detail["category"] = kb_results[0].get("category", "")
                    except Exception:
                        pass  # Gracefully skip if lookup fails
                food_details.append(detail)

            # Determine if this is a snack based on meal type and calories
            is_snack = meal_type == "snack" or meal_percentage < 20

            # Build structured feedback with goal-driven priorities
            feedback_structure = self._build_meal_feedback_structure(
                meal_totals=meal_totals,
                daily_totals=daily_totals or {},
                rdv=rdv,
                health_goal=health_goal,
                meal_size=meal_size,
                is_snack=is_snack,
                priority_nutrients=priority_nutrients,
                priority_rdvs=priority_rdvs
            )

            return {
                "meal": {
                    "foods": food_names,
                    "food_details": food_details,
                    "meal_type": meal_type,
                    "meal_time": meal_time,
                    "totals": meal_totals,
                    "meal_size": meal_size,
                    "meal_emoji": meal_emoji,
                    "meal_percentage_of_daily": round(meal_percentage, 1)
                },
                # Goal-driven feedback (per-meal filtered - no raw daily % leaks)
                "feedback_structure": feedback_structure,
                "secondary_alerts": secondary_alerts,
                "learning_phase": {
                    "is_learning": learning_phase,
                    "total_meals_logged": total_meals,
                    "meals_until_complete": max(0, 21 - total_meals)
                },
                "streak": streak,
                "health_goal": health_goal,
            }

        except Exception as e:
            logger.error(f"Analyze last meal error: {e}")
            return {"error": str(e)}

    def _build_meal_feedback_structure(
        self,
        meal_totals: Dict[str, float],
        daily_totals: Dict[str, float],
        rdv: Dict[str, float],
        health_goal: str,
        meal_size: str,
        is_snack: bool = False,
        priority_nutrients: Optional[List[str]] = None,
        priority_rdvs: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Build structured feedback for meal analysis based on user's health goal.
        Now uses goal-driven priority nutrients (6-8 per goal).

        Returns:
            - calorie_status: Dict with calorie info vs target & goal
            - goal_nutrient: Primary nutrient to focus on (usually protein)
            - critical_gaps: List of nutrients <50% RDV (priority nutrients only)
            - moderate_gaps: List of nutrients 50-80% RDV
            - top_win: Best performing nutrient (for motivation)
        """
        # Get nutrient priorities for this goal
        priorities = priority_nutrients or get_priority_nutrients(health_goal)

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

        # 2. GOAL NUTRIENT - Now dynamic based on health goal
        # Get primary nutrient from goal context (protein for most, but folate for pregnancy, etc.)
        goal_nutrient_name = get_primary_nutrient(health_goal)
        goal_nutrient_emoji = get_nutrient_emoji(goal_nutrient_name)

        # Get values from daily totals and meal totals
        db_key = f"total_{goal_nutrient_name}"
        goal_nutrient_daily = daily_totals.get(db_key, daily_totals.get(goal_nutrient_name, 0))
        goal_nutrient_meal = meal_totals.get(goal_nutrient_name, 0)

        # Get target from priority_rdvs if available
        if priority_rdvs and goal_nutrient_name in priority_rdvs:
            goal_nutrient_target = priority_rdvs[goal_nutrient_name].amount
        else:
            goal_nutrient_target = rdv.get(goal_nutrient_name, 1)

        goal_nutrient_daily_pct = (goal_nutrient_daily / goal_nutrient_target * 100) if goal_nutrient_target > 0 else 0

        # Per-meal adequacy thresholds (nutrient-specific, research-based)
        # These are approximate "good meal" contributions
        MEAL_THRESHOLDS = {
            # Protein: 15-25g per meal is good
            "protein": {"excellent": 25.0, "good": 15.0},
            # Folate: 150-200mcg per meal is good (600mcg daily for pregnancy)
            "folate": {"excellent": 200.0, "good": 150.0},
            # Calcium: 250-350mg per meal is good
            "calcium": {"excellent": 350.0, "good": 250.0},
            # Iron: 4-6mg per meal is good
            "iron": {"excellent": 6.0, "good": 4.0},
            # Sodium: <600mg per meal is good (limit nutrient)
            "sodium": {"excellent": 400.0, "good": 600.0},  # Lower is better for sodium
        }

        thresholds = MEAL_THRESHOLDS.get(goal_nutrient_name, {"excellent": 25.0, "good": 15.0})

        # Determine meal-level status
        if goal_nutrient_name == "sodium":
            # Sodium is a "limit" nutrient - lower is better
            if goal_nutrient_meal <= thresholds["excellent"]:
                meal_status = "excellent"
            elif goal_nutrient_meal <= thresholds["good"]:
                meal_status = "good"
            else:
                meal_status = "high"  # Warning for sodium
        else:
            # Most nutrients - higher is better
            if goal_nutrient_meal >= thresholds["excellent"]:
                meal_status = "excellent"
            elif goal_nutrient_meal >= thresholds["good"]:
                meal_status = "good"
            else:
                meal_status = "low"

        goal_nutrient = {
            "nutrient": goal_nutrient_name,
            "emoji": goal_nutrient_emoji,
            # Per-meal assessment (what matters for feedback)
            "meal_grams": round(goal_nutrient_meal, 1),
            "meal_status": meal_status,  # "excellent", "good", or "low"
        }

        # 3. CRITICAL GAPS (<50% RDV) - ONLY for PRIORITY nutrients (excluding calories)
        # IMPORTANT: Assess EVERY nutrient at the meal level, not just the primary one.
        # A breakfast with 4.5mg iron shouldn't be called "lagging" - that's a solid
        # per-meal contribution even if daily % is still low after one meal.
        critical_gaps = []
        priority_non_calorie = [n for n in priorities if n != "calories"]

        # Per-meal thresholds for ALL nutrients (what counts as "good" for a single meal)
        ALL_MEAL_THRESHOLDS = {
            "protein": {"good": 15.0},
            "folate": {"good": 150.0},
            "calcium": {"good": 250.0},
            "iron": {"good": 4.0},
            "sodium": {"good": 600.0},  # Limit nutrient - lower is better
            "zinc": {"good": 3.0},
            "magnesium": {"good": 80.0},
            "fiber": {"good": 5.0},
            "vitamin_c": {"good": 20.0},
            "vitamin_d": {"good": 5.0},
            "vitamin_b12": {"good": 0.8},
            "vitamin_a": {"good": 200.0},
            "potassium": {"good": 700.0},
            "carbohydrates": {"good": 40.0},
            "fat": {"good": 15.0},
        }

        for nutrient in priority_non_calorie:
            # Get values - handle both dict and NutrientRDV objects
            db_key = f"total_{nutrient}"
            current = daily_totals.get(db_key, daily_totals.get(nutrient, 0))
            meal_current = meal_totals.get(nutrient, meal_totals.get("carbohydrates" if nutrient == "carbs" else nutrient, 0))
            # Get target from priority_rdvs if available, else from rdv dict
            if priority_rdvs and nutrient in priority_rdvs:
                target = priority_rdvs[nutrient].amount
            else:
                target = rdv.get(nutrient, 1)
            percentage = (current / target * 100) if target > 0 else 0

            # Check if THIS MEAL had a good amount of this nutrient
            meal_threshold = ALL_MEAL_THRESHOLDS.get(nutrient, {}).get("good", 15.0)
            if nutrient == "sodium":
                meal_was_good = meal_current <= meal_threshold
            else:
                meal_was_good = meal_current >= meal_threshold

            # Skip if the meal had adequate amount - don't call it "critical"
            if meal_was_good:
                continue

            if percentage < 50:
                critical_gaps.append({
                    "nutrient": nutrient,
                    "current": current,
                    "meal_amount": meal_current,
                    "meal_was_good": meal_was_good,
                    "target": target,
                    "percentage": round(percentage, 1),
                    "gap": target - current
                })

        # Sort by priority for this goal
        critical_gaps.sort(key=lambda x: priorities.index(x["nutrient"]) if x["nutrient"] in priorities else 99)

        # 4. MODERATE GAPS (50-80% RDV) - ONLY for PRIORITY nutrients (excluding calories)
        # Also skip nutrients where the meal delivered a good per-meal amount
        moderate_gaps = []
        for nutrient in priority_non_calorie:
            db_key = f"total_{nutrient}"
            current = daily_totals.get(db_key, daily_totals.get(nutrient, 0))
            meal_current = meal_totals.get(nutrient, 0)
            if priority_rdvs and nutrient in priority_rdvs:
                target = priority_rdvs[nutrient].amount
            else:
                target = rdv.get(nutrient, 1)
            percentage = (current / target * 100) if target > 0 else 0

            # Skip if this meal delivered a good amount
            meal_threshold = ALL_MEAL_THRESHOLDS.get(nutrient, {}).get("good", 15.0)
            if nutrient == "sodium":
                meal_was_good = meal_current <= meal_threshold
            else:
                meal_was_good = meal_current >= meal_threshold
            if meal_was_good:
                continue

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

        # 5. TOP WIN (best performing PRIORITY nutrient for motivation, excluding calories)
        top_win = None
        best_percentage = 0
        for nutrient in priority_non_calorie:
            db_key = f"total_{nutrient}"
            current = daily_totals.get(db_key, daily_totals.get(nutrient, 0))
            if priority_rdvs and nutrient in priority_rdvs:
                target = priority_rdvs[nutrient].amount
            else:
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

    async def _get_user_progress(self, user_id: str, include_weekly: bool = False) -> Dict[str, Any]:
        """Get user's nutrition progress with goal-driven priority nutrients."""
        try:
            profile = await get_user_health_profile(user_id)
            daily_totals = await get_daily_nutrition_totals(user_id)

            if not profile:
                return {"error": "User profile not found"}

            rdv = profile.get("rdv", {})
            health_goal = profile.get("health_goals", "general_wellness")
            gender = profile.get("gender")
            age = profile.get("age")
            custom_calorie_goal = profile.get("custom_calorie_goal")

            # Get goal context for dynamic nutrient tracking
            goal_context = get_goal_context(health_goal, gender, age, custom_calorie_goal)

            progress = {
                "daily_totals": daily_totals or {},
                "targets": rdv,
                "streak": profile.get("current_logging_streak", 0),
                "health_goal": health_goal,
                "goal_display_name": goal_context["goal_display_name"],
                "goal_emoji": goal_context["goal_emoji"],
                "primary_nutrient": goal_context["primary_nutrient"],
                "priority_nutrients": goal_context["priority_nutrients"],
            }

            # Calculate percentages for PRIORITY NUTRIENTS (not hardcoded 4)
            if daily_totals:
                progress["percentages"] = {}
                for nutrient in goal_context["priority_nutrients"]:
                    # Get target from priority RDVs
                    rdv_obj = goal_context["priority_rdvs"].get(nutrient)
                    target = rdv_obj.amount if rdv_obj else rdv.get(nutrient, 1)
                    # Get current from daily totals (handle column naming)
                    db_key = f"total_{nutrient}"
                    current = daily_totals.get(db_key, daily_totals.get(nutrient, 0))
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

            logger.info(f"   → User progress fetched for {health_goal}")
            return progress

        except Exception as e:
            logger.error(f"Get user progress error: {e}")
            return {"error": str(e)}

    async def _get_meal_history(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """Get user's recent meals with computed totals."""
        try:
            meals = await get_user_meals(user_id, limit=limit)

            formatted = []
            for meal in meals:
                # Compute totals from foods (all 16 nutrients)
                foods = meal.get("foods", [])
                totals = {
                    "calories": 0, "protein": 0, "carbohydrates": 0, "fat": 0, "fiber": 0,
                    "iron": 0, "calcium": 0, "zinc": 0, "potassium": 0, "sodium": 0, "magnesium": 0,
                    "vitamin_a": 0, "vitamin_c": 0, "vitamin_d": 0, "vitamin_b12": 0, "folate": 0,
                }
                for food in foods:
                    for nutrient in totals:
                        totals[nutrient] += food.get(nutrient, 0)

                formatted.append({
                    "meal_type": meal.get("meal_type"),
                    "date": meal.get("meal_date"),
                    "time": meal.get("meal_time"),
                    "foods": [f.get("food_name") for f in foods],
                    "totals": totals,
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

        if any(word in message_lower for word in ["iron", "calcium", "protein", "nutrient", "folate", "vitamin"]):
            return ["Show me a meal with this nutrient", "How am I doing today?"]
        elif any(word in message_lower for word in ["progress", "doing", "stats"]):
            return ["Suggest a meal for my goal", "Show my meal history"]
        elif any(word in message_lower for word in ["suggest", "recommend", "should i eat", "what to eat"]):
            return ["How am I doing today?", "Show my meal history"]
        elif any(word in message_lower for word in ["ate", "meal", "lunch", "dinner", "breakfast"]):
            return ["How was that meal?", "Suggest my next meal"]
        else:
            return ["Suggest a meal for my goal", "Check your progress"]


# Singleton
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    """Get or create singleton ChatAgent."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
        logger.info("✓ ChatAgent singleton created")
    return _chat_agent
