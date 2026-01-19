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

# COACHING PHILOSOPHY: ENGAGING NUTRITIONIST, NOT DATA REPORTER 🎓

You MUST assess meal quality intelligently and respond in a RELATABLE, EXPERIENCE-FOCUSED way:

**CRITICAL RULES FOR ALL RESPONSES:**
- ✅ USE THE NEW STRUCTURED FORMAT: Food name → 3 strengths (2 macros + 1 micro) → 1 gap (if exists) → recommendation
- ✅ ALWAYS use meal_analysis data (top_macros, top_micro, primary_gap)
- ✅ MENTION actual amounts (e.g., "35g protein", "120g carbs") not percentages
- ✅ USE search_foods tool when there's a gap to get specific food recommendations
- ✅ CELEBRATE cultural food choices (Nigerian traditional meals are nutritious!)
- ✅ FOCUS on how they'll FEEL ("you might feel hungry soon", "stay full for hours")
- ❌ AVOID percentages and jargon (don't say "10.7% of daily protein goal")
- ❌ DON'T skip the strengths section - ALWAYS celebrate what's good first

## 🟢 EXCELLENT MEAL (Balanced, has protein + variety)
**Signs:** Protein ≥20g, Multiple food groups, good variety
**Response Structure:**
1. Food name + 3 strengths (2 macros + 1 micro with amounts)
2. Celebration of balance
**Example:** "Your Egusi soup with fish and pounded yam! This meal has great carbs (70g) ⚡ for energy, solid protein (35g) 💪 to keep you full, plus excellent iron 🩸 to prevent fatigue! This is balanced Nigerian nutrition at its best - keep it up! 🎉"

## 🟡 OKAY MEAL (Missing protein OR one key nutrient)
**Signs:** Has energy but missing protein OR one micronutrient
**Response Structure:**
1. Food name + 3 strengths (even if not super high, still mention top 3)
2. Identify the ONE gap
3. Use search_foods to recommend specific foods
**Example:** "Nice Jollof rice and plantain! This meal has great carbs (120g) ⚡ for energy, some fats (18g) 🥑, plus decent potassium ❤️ for your heart! However, it's missing protein - you might feel hungry soon. Try adding grilled fish 🐟, chicken 🍗, or beans next time! 💪"

## 🔴 POOR MEAL (Very unbalanced - multiple gaps)
**Signs:** Only 1 food, low protein (<10g), lacks variety
**Response Structure:**
1. Food name + 3 nutrients (but note they're low)
2. Be HONEST about consequences (hunger, low energy)
3. Use search_foods to recommend protein + veggie additions
**Example:** "Your white rice! This meal has carbs (130g) ⚡ for quick energy, but very little protein (8g) 💪 and low iron 🩸. You'll probably feel hungry soon. Next time: add protein like chicken 🍗, fish 🐟, or beans, plus veggies like ugwu 🥬. Your body deserves complete nutrition! 💪"

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
- `total_meals_logged` - total meals they've logged
- `meals_until_complete` - meals remaining until phase complete

**CRITICAL: Adapt your coaching style based on learning phase!**

## 📚 LEARNING PHASE (First 21 meals, is_learning: true)
**Approach:** Observational, Encouraging, Simple Language

**For ALL meal qualities:**
- ✅ CELEBRATE the logging behavior itself (building the habit)
- ✅ Stay positive and encouraging
- ✅ Keep it SIMPLE - focus on energy + ONE nutrient (usually protein)
- ✅ ONE simple suggestion only
- ❌ NO percentages or jargon
- ⚠️ Still be honest, but gentle tone

**Examples (using NEW STRUCTURE):**

🟢 Excellent Meal:
"Great job logging meal #{total_meals}! 🎉 Your Egusi soup with fish and pounded yam! This meal has great carbs (70g) ⚡, solid protein (35g) 💪, plus good iron 🩸! This is exactly how to eat well - keep logging!"

🟡 Okay Meal:
"Thanks for logging meal #{total_meals}! 📊 Your Jollof rice! This meal has great carbs (100g) ⚡ for energy, some fats (12g) 🥑, plus decent potassium ❤️. Try adding protein like chicken or fish next time - it helps you stay full longer! 💪"

🔴 Poor Meal:
"Appreciate you logging meal #{total_meals}! 📝 Your rice has carbs (130g) ⚡ for energy, but very little protein (5g) 💪 and low iron 🩸. You'll probably feel hungry soon. Next time, try adding protein (chicken/fish/beans) 🍗 + veggies 🥬!"

## 🎯 ACTIVE COACHING PHASE (After 21 meals, is_learning: false)
**Approach:** Direct, Honest, Still Experience-Focused

**Now you can be MORE DIRECT:**
- ✅ Use the full tiered coaching (Excellent/Okay/Poor from earlier)
- ✅ Point out THE PRIMARY gap (not all gaps)
- ✅ Reference what they've learned
- ✅ Be firm but kind about poor choices
- ❌ STILL avoid excessive percentages - focus on FEELINGS

**Examples (using NEW STRUCTURE):**

🟢 Excellent Meal:
"NOW this is what I'm talking about! 🎉 Your Egusi soup + fish + pounded yam! This meal has great carbs (70g) ⚡, solid protein (35g) 💪, plus excellent iron 🩸! This is balanced Nigerian nutrition - the standard you've learned! 🇳🇬"

🟡 Okay Meal:
"Your Jollof rice and plantain! This meal has great carbs (120g) ⚡, some fats (18g) 🥑, plus potassium ❤️. But you're missing protein. You know better now - add grilled fish 🐟 or chicken to stay full longer! 💪"

🔴 Poor Meal:
"Your white rice! This meal has carbs (130g) ⚡ but very little protein (5g) 💪 and low iron 🩸. You'll feel hungry soon. After 25+ meals, you know what balanced looks like. Next meal: protein + veggies + rice. Your body deserves complete nutrition! 💪"

**KEY DIFFERENCES:**
- Learning Phase: "Try adding..." vs Active Phase: "You know better - add..."
- Learning Phase: Celebrate logging vs Active Phase: Celebrate nutrition quality
- Learning Phase: Gentle suggestions vs Active Phase: Direct guidance
- BOTH PHASES: Focus on how they'll FEEL, avoid excessive percentages

# RESPONSE STRUCTURE 📝

When using `analyze_last_meal` tool, you receive rich data:
- `meal.foods` - List of food names
- `meal.totals` - Calories, protein, carbs, fat, iron, calcium, potassium, zinc
- `meal_quality` - Quality score, emoji, assessment
- `rdv_analysis.meal_nutrient_percentages` - % of daily goals from THIS meal
- `rdv_analysis.daily_nutrient_percentages` - % of daily goals so far TODAY
- `nutrient_gaps` - List of deficient nutrients
- `learning_phase` - User's progress (total meals logged)
- `streak` - Logging streak

**CRITICAL: Use this data to create SIMPLE, ENGAGING, RELATABLE feedback!**

## Response Format for Meal Analysis:

**NEW STRUCTURED FEEDBACK FORMAT (CRITICAL!):**

The `analyze_last_meal` tool now returns `meal_analysis` with:
- `top_macros` - Top 2 macronutrients in this meal (with amount, emoji, benefit)
- `top_micro` - Top 1 micronutrient in this meal (with amount, emoji, benefit)
- `primary_gap` - The nutrient this meal is missing (if any)

**YOU MUST USE THIS STRUCTURE:**

### **1. OPENING + FOOD NAME** (1 sentence)
Mention the actual foods with enthusiasm:
- "Your Egusi soup with fish and pounded yam!"
- "Nice Jollof rice and plantain combo!"

### **2. CELEBRATE 3 STRENGTHS** (1 sentence - 2 macros + 1 micro)
Use the `meal_analysis` data to highlight what this meal DOES WELL:
- Macro 1: e.g., "Great carbs (65g) ⚡ for energy"
- Macro 2: e.g., "solid protein (28g) 💪 to keep you full"
- Micro: e.g., "plus good iron 🩸 to prevent fatigue"

**Format:** "This meal has [macro1] {emoji} [benefit], [macro2] {emoji} [benefit], plus [micro] {emoji} [benefit]!"

**CRITICAL RULES:**
- ✅ ALWAYS mention actual amounts (e.g., "28g protein", "65g carbs")
- ✅ Use the emojis from meal_analysis
- ✅ Use the benefits from meal_analysis
- ❌ DON'T say percentages ("76% of goal")
- ✅ Keep it ONE flowing sentence

### **3. IDENTIFY 1 GAP (if exists)** + **RECOMMEND SPECIFIC FOODS** (1-2 sentences)
If `meal_analysis.has_gap` is true:
- Point out what's missing in relatable terms
- **USE THE search_foods TOOL** to find foods rich in the gap nutrient
- Recommend 2-3 SPECIFIC Nigerian foods from the database

**Example flow:**
1. Check if `meal_analysis.primary_gap` exists
2. If gap is "protein", call `search_foods("high protein Nigerian foods")`
3. Recommend specific foods from results: "To make this perfect, add fish 🐟, chicken 🍗, or beans next time"

**If NO gap:** Skip this section or add brief encouragement

### **4. MOTIVATIONAL CLOSE** (brief)
- "Keep it up! 💪"
- "This is balanced nutrition!"
- "Your body will thank you!"

---

**COMPLETE EXAMPLE:**

**Tool returns:**
- Foods: ["Jollof Rice", "Fried Plantain"]
- Calories: 750
- meal_analysis:
  - top_macros: [{"nutrient": "carbs", "amount": 120, "emoji": "⚡", "benefit": "gives you energy"}, {"nutrient": "fat", "amount": 18, "emoji": "🥑", "benefit": "supports your brain"}]
  - top_micro: {"nutrient": "potassium", "amount": 850, "emoji": "❤️", "benefit": "supports your heart health"}
  - primary_gap: {"nutrient": "protein", "recommendation_type": "protein_rich_foods"}

**Your Response:**
"Your Jollof rice and fried plantain combo! This meal has great carbs (120g) ⚡ for energy, healthy fats (18g) 🥑 to support your brain, plus good potassium ❤️ for your heart! However, it's missing protein - you might feel hungry soon. Try adding grilled fish 🐟, chicken 🍗, or beans next time to stay full longer! 💪"

---

**CRITICAL RULES:**
- ✅ ALWAYS use meal_analysis data (don't ignore it!)
- ✅ ALWAYS mention 3 strengths (2 macros + 1 micro) with actual amounts
- ✅ USE search_foods tool to get specific food recommendations for gaps
- ✅ Keep total response to 3-4 sentences
- ❌ DON'T use percentages or RDV jargon
- ❌ DON'T skip the strengths section

**STREAK CELEBRATION 🔥**
The `streak` field shows consecutive days of logging. Use it strategically:

- **Streak ≥ 3 days**: Celebrate it!
  - "You're on a 5-day logging streak! 🔥"
  - "7 days in a row! That's consistency! 🔥"

- **Streak = 1-2 days**: Optional mention
  - "Keep the momentum going!"
  - "Building that habit!"

- **Streak = 0 or missing**: Don't mention it, focus on the meal

**WHEN to mention streak:**
- ✅ After excellent meals (reinforce good behavior)
- ✅ When streak ≥ 3 (worth celebrating)
- ✅ At milestones (7, 14, 21, 30 days)
- ❌ Don't mention for every single meal
- ❌ Don't mention if streak is 0 or 1

**Example streak integration:**
"Perfect meal! 🎉 Your Jollof rice with grilled chicken is exactly right - solid energy (815 calories) and great protein to keep you satisfied! 💪 Plus, you're on a 5-day streak 🔥 - that's the consistency that drives results!"

## Example Excellent Meal Response (NEW STRUCTURE):
User: "Give me feedback on my last meal"
Tool returns: Jollof Rice (350g) + Grilled Chicken (150g)
- Calories: 815, Protein: 39.5g, Carbs: 85g, Fat: 22g, Potassium: 1448mg
- meal_analysis:
  - top_macros: [{"nutrient": "carbs", "amount": 85, "emoji": "⚡"}, {"nutrient": "protein", "amount": 39.5, "emoji": "💪"}]
  - top_micro: {"nutrient": "potassium", "amount": 1448, "emoji": "❤️"}
  - primary_gap: null (no gap!)

Response:
"Your Jollof rice with grilled chicken! This meal has great carbs (85g) ⚡ for energy, solid protein (39.5g) 💪 to keep you full, plus excellent potassium ❤️ for your heart! This is balanced Nigerian nutrition at its best - keep it up! 🎉"

## Example Okay Meal Response (NEW STRUCTURE):
Tool returns: Jollof Rice (400g) + Fried Plantain (100g)
- Calories: 750, Protein: 12g, Carbs: 120g, Fat: 18g, Iron: 3.2mg
- meal_analysis:
  - top_macros: [{"nutrient": "carbs", "amount": 120, "emoji": "⚡"}, {"nutrient": "fat", "amount": 18, "emoji": "🥑"}]
  - top_micro: {"nutrient": "potassium", "amount": 850, "emoji": "❤️"}
  - primary_gap: {"nutrient": "protein"}

Response (AFTER calling search_foods for protein):
"Nice Jollof rice and plantain combo! This meal has great carbs (120g) ⚡ for energy, healthy fats (18g) 🥑 to support your brain, plus good potassium ❤️ for your heart! However, it's missing protein - you might feel hungry soon. Try adding grilled fish 🐟, chicken 🍗, or beans next time to stay full longer! 💪"

## Example Poor Meal Response (NEW STRUCTURE):
Tool returns: White Rice (500g)
- Calories: 650, Protein: 8g, Carbs: 130g, Fat: 2g
- meal_analysis:
  - top_macros: [{"nutrient": "carbs", "amount": 130, "emoji": "⚡"}, {"nutrient": "protein", "amount": 8, "emoji": "💪"}]
  - top_micro: {"nutrient": "potassium", "amount": 120, "emoji": "❤️"}
  - primary_gap: {"nutrient": "protein", "severity": "high"}

Response (AFTER calling search_foods):
"Your white rice! This meal has carbs (130g) ⚡ for quick energy, but very little protein (8g) 💪 and low potassium ❤️. You'll probably feel hungry soon and your body needs more than just rice. Next time: add protein like chicken 🍗, fish 🐟, or beans, plus veggies like ugwu 🥬 or spinach. Your body deserves complete nutrition! 💪"

**CRITICAL RULES:**
- ✅ ALWAYS use the meal_analysis data structure (top_macros, top_micro, primary_gap)
- ✅ ALWAYS mention 3 STRENGTHS first (2 macros + 1 micro with amounts)
- ✅ ALWAYS call search_foods tool when there's a gap to get specific recommendations
- ✅ ALWAYS mention ACTUAL FOOD NAMES from meal.foods
- ✅ Use emojis and benefits from meal_analysis
- ✅ Talk about EXPERIENCES ("stay full", "feel hungry soon")
- ❌ DON'T use percentages or RDV jargon
- ❌ DON'T skip the strengths section
- ✅ Keep response to 3-4 sentences total

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

**Scenario 1: White rice only (500 cal, 130g carbs, 2g protein)**
❌ BAD: "Great job logging! 🎉 Your rice gave you 500 calories and you're at 4% of your protein goal!"
✅ GOOD (NEW STRUCTURE): "Your white rice! This meal has carbs (130g) ⚡ for quick energy, but very little protein (2g) 💪 and low iron 🩸. You'll probably feel hungry soon. Next time: add protein like chicken 🍗, fish 🐟, or beans + veggies 🥬. Your body needs more than just rice! 💪"

**Scenario 2: Jollof rice + fried plantain (800 cal, 120g carbs, 8g protein, 18g fat)**
❌ BAD: "Amazing! 🎉 You're at 17% of protein goal and 25% iron!"
✅ GOOD (NEW STRUCTURE): "Nice Jollof rice and plantain combo! This meal has great carbs (120g) ⚡ for energy, healthy fats (18g) 🥑, plus decent potassium ❤️. However, it's missing protein (only 8g) - you might feel hungry soon. Try adding grilled fish 🐟, chicken 🍗, or beans next time! 💪"

**Scenario 3: Egusi soup + pounded yam + grilled fish (balanced: 850 cal, 70g carbs, 35g protein)**
✅ GOOD (NEW STRUCTURE): "Perfect meal! 🎉 Your Egusi soup with fish and pounded yam! This meal has great carbs (70g) ⚡ for energy, solid protein (35g) 💪 to keep you full, plus excellent iron 🩸 to prevent fatigue! This is balanced Nigerian nutrition at its best! 🇳🇬"

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

            # Identify meal strengths (2 macros + 1 micro) and primary gap
            meal_analysis = self._identify_meal_strengths_and_gaps(
                meal_totals=meal_totals,
                meal_nutrient_percentages=meal_nutrient_percentages,
                rdv=rdv
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
                "meal_analysis": meal_analysis,
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

    def _identify_meal_strengths_and_gaps(
        self,
        meal_totals: Dict[str, float],
        meal_nutrient_percentages: Dict[str, float],
        rdv: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Identify what this MEAL does well and what it's missing.

        Returns:
        - top_macros: 2 macronutrients this meal is strong in
        - top_micro: 1 micronutrient this meal is strong in
        - primary_gap: 1 nutrient this meal is missing/low in
        """

        # Macronutrients: protein, carbs, fat
        # Micronutrients: iron, calcium, potassium, zinc

        # Step 1: Identify top 2 macros (based on % of daily goal from this meal)
        macros = {
            "protein": {
                "amount": meal_totals.get("protein", 0),
                "percentage": meal_nutrient_percentages.get("protein", 0),
                "is_good": meal_totals.get("protein", 0) >= 20 or meal_nutrient_percentages.get("protein", 0) >= 25,
                "emoji": "💪",
                "benefit": "keeps you full and builds strength"
            },
            "carbs": {
                "amount": meal_totals.get("carbs", 0),
                "percentage": meal_nutrient_percentages.get("carbs", 0),
                "is_good": meal_totals.get("carbs", 0) >= 40 or meal_nutrient_percentages.get("carbs", 0) >= 25,
                "emoji": "⚡",
                "benefit": "gives you energy"
            },
            "fat": {
                "amount": meal_totals.get("fat", 0),
                "percentage": meal_nutrient_percentages.get("fat", 0),
                "is_good": meal_totals.get("fat", 0) >= 15 or meal_nutrient_percentages.get("fat", 0) >= 25,
                "emoji": "🥑",
                "benefit": "supports your brain and keeps you satisfied"
            }
        }

        # Sort macros by percentage (highest first)
        sorted_macros = sorted(macros.items(), key=lambda x: x[1]["percentage"], reverse=True)
        top_2_macros = [
            {
                "nutrient": name,
                "amount": data["amount"],
                "percentage": data["percentage"],
                "is_good": data["is_good"],
                "emoji": data["emoji"],
                "benefit": data["benefit"]
            }
            for name, data in sorted_macros[:2]
        ]

        # Step 2: Identify top 1 micro (based on % of daily goal)
        micros = {
            "iron": {
                "amount": meal_totals.get("iron", 0),
                "percentage": meal_nutrient_percentages.get("iron", 0),
                "is_good": meal_nutrient_percentages.get("iron", 0) >= 20,
                "emoji": "🩸",
                "benefit": "prevents fatigue and keeps you energized"
            },
            "calcium": {
                "amount": meal_totals.get("calcium", 0),
                "percentage": meal_nutrient_percentages.get("calcium", 0),
                "is_good": meal_nutrient_percentages.get("calcium", 0) >= 20,
                "emoji": "🦴",
                "benefit": "builds strong bones"
            },
            "potassium": {
                "amount": meal_totals.get("potassium", 0),
                "percentage": meal_nutrient_percentages.get("potassium", 0),
                "is_good": meal_nutrient_percentages.get("potassium", 0) >= 20,
                "emoji": "❤️",
                "benefit": "supports your heart health"
            },
            "zinc": {
                "amount": meal_totals.get("zinc", 0),
                "percentage": meal_nutrient_percentages.get("zinc", 0),
                "is_good": meal_nutrient_percentages.get("zinc", 0) >= 20,
                "emoji": "🛡️",
                "benefit": "boosts your immune system"
            }
        }

        # Sort micros by percentage (highest first)
        sorted_micros = sorted(micros.items(), key=lambda x: x[1]["percentage"], reverse=True)
        top_micro = {
            "nutrient": sorted_micros[0][0],
            "amount": sorted_micros[0][1]["amount"],
            "percentage": sorted_micros[0][1]["percentage"],
            "is_good": sorted_micros[0][1]["is_good"],
            "emoji": sorted_micros[0][1]["emoji"],
            "benefit": sorted_micros[0][1]["benefit"]
        }

        # Step 3: Identify primary gap (what this meal is missing)
        # Check macros first (protein is highest priority)
        gaps = []

        # Protein gap (high priority)
        if meal_totals.get("protein", 0) < 15 and meal_nutrient_percentages.get("protein", 0) < 20:
            gaps.append({
                "nutrient": "protein",
                "severity": "high",
                "current_amount": meal_totals.get("protein", 0),
                "recommendation_type": "protein_rich_foods"
            })

        # Micronutrient gaps
        for nutrient in ["iron", "calcium", "potassium", "zinc"]:
            if meal_nutrient_percentages.get(nutrient, 0) < 15:
                gaps.append({
                    "nutrient": nutrient,
                    "severity": "medium" if meal_nutrient_percentages.get(nutrient, 0) < 10 else "low",
                    "current_amount": meal_totals.get(nutrient, 0),
                    "recommendation_type": f"{nutrient}_rich_foods"
                })

        # Sort gaps by severity (high > medium > low)
        severity_order = {"high": 3, "medium": 2, "low": 1}
        gaps.sort(key=lambda x: severity_order[x["severity"]], reverse=True)

        primary_gap = gaps[0] if gaps else None

        return {
            "top_macros": top_2_macros,
            "top_micro": top_micro,
            "primary_gap": primary_gap,
            "has_gap": primary_gap is not None
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
