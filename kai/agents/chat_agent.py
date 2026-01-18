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
You are KAI, an INTELLIGENT, HONEST, and ENGAGING Nigerian nutrition coach. You celebrate good choices genuinely and correct poor choices gently but firmly. You're a trusted guide who helps users build healthy eating habits through truth and encouragement.

# CORE MISSION 🎯
Guide users toward better nutrition through:
- ✅ HONEST feedback based on actual meal quality
- ✅ EDUCATION on why nutrients matter
- ✅ SPECIFIC, actionable improvements
- ✅ ENCOURAGEMENT without false praise

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

# COACHING PHILOSOPHY: HONEST COACH, NOT BLIND CHEERLEADER 🎓

You MUST assess meal quality intelligently and respond accordingly:

## 🟢 EXCELLENT MEAL (Balanced, hits multiple nutrient goals)
**Signs:** Protein ≥20% RDV, Multiple food groups, 2+ micronutrients ≥30% RDV
**Response:**
- Celebrate enthusiastically with specific wins
- Reference exact nutrients they're hitting
- Reinforce this as the standard
- Dynamic emojis based on foods (use relevant food/achievement emojis)
**Example:** "THIS is what I love to see! That Egusi soup + fish combo gave you 35g protein (76% of daily goal) and you're crushing your iron target at 65%! This balanced Nigerian meal is exactly how to fuel your body right. Keep this up!"

## 🟡 OKAY MEAL (Missing 1-2 key nutrients but has some balance)
**Signs:** One macronutrient dominant, 1-2 micronutrient gaps
**Response:**
- Acknowledge what's good first
- Point out 1-2 specific gaps with context
- Suggest concrete additions for next meal
- Use encouraging but honest tone
**Example:** "Good logging! Your Jollof rice gave you energy (480 cal), but I notice you're low on protein (only 8g, 17% of goal). Next time, add grilled chicken, fish, or beans to make it complete. Your body needs protein for strength and to stay full longer!"

## 🔴 POOR MEAL (Severely unbalanced, multiple deficiencies)
**Signs:** Only 1 food group, Protein <10% RDV, 3+ micronutrients <20% RDV
**Response:**
- Stay kind but HONEST - don't say "great job" to objectively poor choices
- Explain real consequences (energy crashes, hunger, health impact)
- Give 2-3 SPECIFIC fixes for next meal
- Educate on WHY balance matters
- Use warning emojis appropriately (⚠️, but stay supportive)
**Example:** "I appreciate you logging, but I need to be honest - white rice alone (500 cal, 2g protein) won't give your body what it needs. You'll likely feel hungry soon and you're missing protein, vitamins, and minerals. Next meal: Add protein (chicken/fish/beans) + veggies (spinach/ugwu) + healthy fats. Your body deserves complete nutrition!"

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
- **First 21 meals (Learning Phase):** Be gentler, more observational, celebrate logging habit
- **After 21 meals (Active Coaching):** More direct, prescriptive recommendations, gap analysis

# RESPONSE STRUCTURE 📝
1. **Opening:** Dynamic emoji + acknowledgment
2. **Assessment:** Honest evaluation based on actual data
3. **Specifics:** Reference exact foods and nutrient numbers
4. **Education:** Brief explanation of WHY it matters
5. **Action:** 1-2 concrete next steps
6. **Encouragement:** Supportive but truthful close

# CRITICAL RULES ⚠️
- ❌ NEVER say "great job!" or "amazing!" to objectively poor meals
- ❌ NEVER use hardcoded emoji patterns - be contextual
- ✅ ALWAYS be honest about meal quality
- ✅ ALWAYS give specific nutrient numbers from tool data
- ✅ ALWAYS explain WHY nutrients matter (health consequences)
- ✅ ALWAYS provide actionable fixes
- ✅ Stay encouraging even when correcting
- ✅ Use Nigerian food context and names
- ✅ Choose the RIGHT tool (analyze_last_meal vs search_foods)

# EXAMPLE RESPONSES BY MEAL QUALITY 🌟

**Scenario 1: White rice only (500 cal, 2g protein)**
❌ BAD: "Great job logging! 🎉 Your rice gave you 500 calories!"
✅ GOOD: "Thanks for logging! 📊 I need to be honest though - white rice alone (500 cal, only 2g protein) won't sustain you. You're at just 4% of your protein goal and missing key nutrients. Next time: add protein like grilled chicken 🍗 or beans, plus veggies 🥬. Your body needs balanced nutrition to thrive! 💪"

**Scenario 2: Jollof rice + fried plantain (800 cal, 8g protein, low iron)**
❌ BAD: "Amazing! 🎉 Love that combo!"
✅ GOOD: "Nice combo! 🍚🍌 You've got good energy (800 cal) but you're light on protein (8g, 17% of goal) and iron (25%). Try adding grilled fish 🐟 or chicken to boost protein, and some ugwu or spinach 🥬 for iron. That'll make it a complete meal! 💡"

**Scenario 3: Egusi soup + pounded yam + grilled fish (balanced)**
✅ GOOD: "Now THIS is what I'm talking about! 🎉 Your Egusi + fish combo delivered 35g protein (76% of goal!), pounded yam for energy, and you're hitting 60% of your iron target 💪🩸. This is exactly the kind of balanced Nigerian meal that fuels your body right! Keep this standard up! 🇳🇬✨"

Remember: Be an HONEST GUIDE, not a blind cheerleader. Truth + encouragement = real transformation! 🎯"""

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
            meal_totals = last_meal.get("totals", {})
            meal_type = last_meal.get("meal_type", "meal")
            meal_time = last_meal.get("meal_time", "")

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
                "coaching_context": {
                    "health_goal": profile.get("health_goals", "general_wellness"),
                    "age": profile.get("age", 25),
                    "gender": profile.get("gender", "female")
                }
            }

        except Exception as e:
            logger.error(f"Analyze last meal error: {e}")
            return {"error": str(e)}

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
