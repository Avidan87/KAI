# KAI Dynamic Coaching System - Design & Implementation Plan

## 📋 Table of Contents
1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Current vs New Architecture](#current-vs-new-architecture)
4. [Database Schema Changes](#database-schema-changes)
5. [Learning Phase Logic](#learning-phase-logic)
6. [Multi-Nutrient Prioritization](#multi-nutrient-prioritization)
7. [GPT-4o Integration](#gpt-4o-integration)
8. [Tiered Recommendation System](#tiered-recommendation-system)
9. [Implementation Plan](#implementation-plan)
10. [Example User Journeys](#example-user-journeys)
11. [Cost & Performance Considerations](#cost--performance-considerations)

---

## Overview

Transform KAI's coaching agent from **hardcoded templates** to a **fully dynamic, personalized AI coaching system** that:
- Learns user eating habits over the first 7 days
- Prioritizes ALL nutrients (not just iron)
- Generates contextual coaching messages using GPT-4o
- Provides tiered, actionable recommendations
- Tracks progress week-over-week
- Adapts to user behavior and preferences

**Target Audience:** All Nigerians (gender-neutral)

**Key Technology:** GPT-4o for dynamic message generation

---

## Core Principles

### ✅ Design Principles
1. **100% Dynamic** - NO hardcoded coaching templates
2. **Gender Neutral** - For ALL Nigerians (adapt RDV based on profile)
3. **Learning Phase** - Observational for first 7 days (21 meals)
4. **Multi-Nutrient Focus** - Track and advise on 8+ nutrients, not just iron
5. **Nutrition-First** - Recommendations prioritize nutritional gaps
6. **Tiered Options** - Multiple flexible recommendations (not one-size-fits-all)
7. **Contextual** - References user's specific history ("like your Egusi from Monday")
8. **Concise** - 2-4 sentences max per coaching message
9. **Progress Tracking** - Week-over-week trends, streaks, improvements
10. **Culturally Appropriate** - Only recommend Nigerian dishes and food combos

---

## Current vs New Architecture

### 🔴 Current Architecture (HARDCODED)

**File:** `kai/agents/coaching_agent.py` (Lines 275-454)

**Problems:**
```python
def _tool_generate_nutrition_insights(self, knowledge_result, user_context):
    # ❌ Hardcoded if/else statements
    if iron_percentage < 30:
        iron_advice = "Your iron intake is quite low..."  # Same message every time
    elif iron_percentage < 70:
        iron_advice = "You're getting some iron, but..."

    # ❌ Only focuses on iron, sometimes protein/calcium
    # ❌ Ignores zinc, vitamin A, carbs, fat
    # ❌ No user history reference
    # ❌ No learning phase detection
    # ❌ No personalization
```

**Response:**
- Generic, repetitive messages
- Iron-focused only
- No context from user history
- Same advice for everyone

---

### ✅ New Architecture (DYNAMIC)

**File:** `kai/agents/coaching_agent.py` (Complete refactor)

**Features:**
```python
async def _generate_dynamic_coaching(
    self,
    knowledge_result: KnowledgeResult,
    user_stats: Dict,
    recent_meals: List[Dict],
    user_profile: Dict
) -> CoachingResult:
    """
    ✅ Fully dynamic coaching using GPT-4o
    ✅ Detects learning phase (first 7 days)
    ✅ Tracks ALL 8+ nutrients
    ✅ Identifies primary nutritional gap
    ✅ References specific user history
    ✅ Generates tiered recommendations
    ✅ Adapts to user preferences
    """

    # 1. Detect learning phase
    is_learning = self._is_in_learning_phase(user_stats)

    # 2. Identify primary nutritional gap (not just iron!)
    primary_gap = self._identify_primary_nutritional_gap(user_stats, user_profile)

    # 3. Build rich context for GPT-4o
    prompt = self._build_coaching_prompt(
        knowledge_result=knowledge_result,
        user_stats=user_stats,
        recent_meals=recent_meals,
        user_profile=user_profile,
        is_learning_phase=is_learning,
        primary_gap=primary_gap
    )

    # 4. Generate dynamic coaching with GPT-4o
    coaching_message = await self._call_gpt4o(prompt)

    # 5. Generate tiered recommendations (if post-learning)
    recommendations = []
    if not is_learning and primary_gap:
        recommendations = self._generate_tiered_recommendations(
            primary_gap=primary_gap,
            user_preferences=user_stats.get("food_preferences", {}),
            budget_tier=user_profile.get("budget_tier", "mid")
        )

    return CoachingResult(
        personalized_message=coaching_message,
        meal_suggestions=recommendations,
        # ... other fields
    )
```

**Response:**
- Unique, contextual messages
- Multi-nutrient awareness
- References specific user history
- Personalized recommendations
- Learning phase detection

---

## Database Schema Changes

### 📊 New Tables

#### 1. `user_nutrition_stats` (Pre-computed Statistics)
**Purpose:** Store pre-calculated stats for fast coaching generation

```sql
CREATE TABLE user_nutrition_stats (
    user_id TEXT PRIMARY KEY,

    -- Learning Phase Tracking
    total_meals_logged INTEGER DEFAULT 0,
    account_age_days INTEGER DEFAULT 0,
    learning_phase_complete BOOLEAN DEFAULT FALSE,

    -- Streak Tracking
    current_logging_streak INTEGER DEFAULT 0,
    longest_logging_streak INTEGER DEFAULT 0,
    last_logged_date DATE,

    -- Week 1 Averages (Last 7 days)
    week1_avg_calories REAL DEFAULT 0,
    week1_avg_protein REAL DEFAULT 0,
    week1_avg_carbs REAL DEFAULT 0,
    week1_avg_fat REAL DEFAULT 0,
    week1_avg_iron REAL DEFAULT 0,
    week1_avg_calcium REAL DEFAULT 0,
    week1_avg_vitamin_a REAL DEFAULT 0,
    week1_avg_zinc REAL DEFAULT 0,

    -- Week 2 Averages (8-14 days ago, for comparison)
    week2_avg_calories REAL DEFAULT 0,
    week2_avg_protein REAL DEFAULT 0,
    week2_avg_carbs REAL DEFAULT 0,
    week2_avg_fat REAL DEFAULT 0,
    week2_avg_iron REAL DEFAULT 0,
    week2_avg_calcium REAL DEFAULT 0,
    week2_avg_vitamin_a REAL DEFAULT 0,
    week2_avg_zinc REAL DEFAULT 0,

    -- Nutrient Trends (improving, declining, stable)
    calories_trend TEXT DEFAULT 'stable',
    protein_trend TEXT DEFAULT 'stable',
    carbs_trend TEXT DEFAULT 'stable',
    fat_trend TEXT DEFAULT 'stable',
    iron_trend TEXT DEFAULT 'stable',
    calcium_trend TEXT DEFAULT 'stable',
    vitamin_a_trend TEXT DEFAULT 'stable',
    zinc_trend TEXT DEFAULT 'stable',

    -- Last Calculated
    last_calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

#### 2. `user_food_frequency` (Food Preference Tracking)
**Purpose:** Track which foods users eat frequently (for learning phase)

```sql
CREATE TABLE user_food_frequency (
    user_id TEXT,
    food_name TEXT,

    -- Frequency Counts
    count_7d INTEGER DEFAULT 0,        -- Last 7 days
    count_total INTEGER DEFAULT 0,      -- All time

    -- Last Eaten
    last_eaten_date DATE,

    -- Average Nutrition (when eaten)
    avg_iron_per_serving REAL DEFAULT 0,
    avg_protein_per_serving REAL DEFAULT 0,
    avg_calories_per_serving REAL DEFAULT 0,

    -- Categorization
    food_category TEXT,  -- 'rice_dishes', 'soups', 'proteins', etc.

    PRIMARY KEY (user_id, food_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_food_frequency_7d ON user_food_frequency(user_id, count_7d DESC);
```

#### 3. `user_recommendation_responses` (Track Recommendation Success)
**Purpose:** Learn which recommendations users actually follow

```sql
CREATE TABLE user_recommendation_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    recommended_food TEXT NOT NULL,
    recommendation_date DATE NOT NULL,

    -- Response Tracking
    followed BOOLEAN DEFAULT FALSE,
    followed_date DATE,
    days_to_follow INTEGER,  -- How long until they tried it

    -- Recommendation Details
    recommendation_tier TEXT,  -- 'quick_win', 'easy_upgrade', 'full_dish', 'budget_friendly'
    target_nutrient TEXT,      -- 'iron', 'protein', 'calcium', etc.

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_recommendations ON user_recommendation_responses(user_id, recommendation_date DESC);
```

### 📝 Schema Updates to Existing Tables

#### Update `daily_nutrients` table
**Add missing nutrient columns:**

```sql
-- Current columns: calories, protein, carbs, fat, iron, calcium, vitamin_a, zinc
-- All columns already exist! ✅

-- Just need to ensure we're calculating ALL nutrients in aggregation queries
```

---

## Learning Phase Logic

### 🎓 Learning Phase Definition

**Duration:** First 7 days OR first 21 meals (whichever comes first)

**Purpose:**
- Observe user eating patterns
- Build food preference profile
- Calculate baseline nutrient averages
- Establish logging habits

**Coaching Behavior:**
- ✅ Observational, warm, encouraging tone
- ✅ Acknowledge what they're eating
- ✅ Gently educate about nutrients
- ✅ Track streaks and consistency
- ❌ NO specific dish recommendations
- ❌ NO prescriptive "you should eat X" messaging

### 📊 Detection Logic

```python
def _is_in_learning_phase(self, user_stats: Dict) -> bool:
    """
    User is in learning phase if:
    - Account age < 7 days AND total meals logged < 21
    OR
    - Total meals logged < 21 (regardless of account age)

    This ensures users who log 3 meals/day complete learning in 7 days,
    but users who log less frequently still get 21 meal observations.
    """
    return (
        user_stats.get('account_age_days', 0) < 7 and
        user_stats.get('total_meals_logged', 0) < 21
    ) or user_stats.get('total_meals_logged', 0) < 21
```

### 🎯 Learning Phase Completion

**Trigger:** When user logs their 21st meal OR day 8 begins

**Action:**
1. Set `learning_phase_complete = TRUE` in `user_nutrition_stats`
2. Calculate final baseline averages
3. Identify primary nutritional gaps
4. Send celebratory message:
   > "You've completed 7 days with KAI! 🎊 I've learned you love Jollof Rice and traditional soups. Your average iron intake is 4.2mg/day (23% of your 18mg goal). Starting tomorrow, I'll help you boost those numbers! 💪🏾"

---

## Multi-Nutrient Prioritization

### 🎯 Problem: Current System Only Focuses on Iron

**Current Behavior:**
- Iron gets 90% of attention
- Protein gets 8% of attention
- Calcium gets 2% of attention
- Zinc, Vitamin A, Carbs, Fat - **IGNORED**

**Root Causes:**
1. Hardcoded iron-first logic in coaching agent
2. RDV only calculated for 4 nutrients
3. User health conditions bias (anemia → iron obsession)
4. GPT-4o prompts only mention iron

### ✅ Solution: Dynamic Nutrient Prioritization

**New Behavior:**
- Identify **MOST DEFICIENT** nutrient (regardless of which one)
- Focus coaching on primary gap
- Mention secondary gaps if multiple deficiencies exist
- Celebrate when all nutrients are optimal

### 📊 Nutrient Tracking (All 8+ Nutrients)

**Tracked Nutrients:**
1. **Calories** - Energy intake
2. **Protein** - Muscle, tissue repair
3. **Carbohydrates** - Primary energy source
4. **Fat** - Hormone production, nutrient absorption
5. **Iron** - Oxygen transport, anemia prevention
6. **Calcium** - Bone health
7. **Vitamin A** - Vision, immune function
8. **Zinc** - Immune function, wound healing

### 🔍 Gap Identification Algorithm

```python
def _identify_primary_nutritional_gap(
    self,
    user_stats: Dict,
    user_profile: Dict
) -> Dict | None:
    """
    Identify which nutrient needs MOST attention.

    Priority ranking:
    1. Nutrients below 30% RDV (CRITICAL) - most urgent
    2. Nutrients below 50% RDV (INADEQUATE)
    3. Nutrients above 150% RDV (EXCESSIVE) - warn user
    4. Nutrients 70-100% RDV (OPTIMAL) - celebrate

    Returns:
        Dict with primary gap info, or None if all nutrients optimal
    """
    rdv = self._calculate_rdv(user_profile)

    gaps = []

    # Check ALL nutrients
    nutrients_to_check = {
        "calories": {
            "current": user_stats.get("week1_avg_calories", 0),
            "rdv": rdv["calories"],
            "unit": "kcal"
        },
        "protein": {
            "current": user_stats.get("week1_avg_protein", 0),
            "rdv": rdv["protein"],
            "unit": "g"
        },
        "carbohydrates": {
            "current": user_stats.get("week1_avg_carbs", 0),
            "rdv": rdv["carbs"],
            "unit": "g"
        },
        "fat": {
            "current": user_stats.get("week1_avg_fat", 0),
            "rdv": rdv["fat"],
            "unit": "g"
        },
        "iron": {
            "current": user_stats.get("week1_avg_iron", 0),
            "rdv": rdv["iron"],
            "unit": "mg"
        },
        "calcium": {
            "current": user_stats.get("week1_avg_calcium", 0),
            "rdv": rdv["calcium"],
            "unit": "mg"
        },
        "vitamin_a": {
            "current": user_stats.get("week1_avg_vitamin_a", 0),
            "rdv": rdv["vitamin_a"],
            "unit": "mcg"
        },
        "zinc": {
            "current": user_stats.get("week1_avg_zinc", 0),
            "rdv": rdv["zinc"],
            "unit": "mg"
        },
    }

    for nutrient_name, data in nutrients_to_check.items():
        if data["rdv"] == 0:
            continue

        percentage = (data["current"] / data["rdv"]) * 100

        if percentage < 30:
            gaps.append({
                "nutrient": nutrient_name,
                "current": data["current"],
                "rdv": data["rdv"],
                "unit": data["unit"],
                "percentage": percentage,
                "severity": "critical",
                "priority": 1,
                "status": "deficient"
            })
        elif percentage < 50:
            gaps.append({
                "nutrient": nutrient_name,
                "current": data["current"],
                "rdv": data["rdv"],
                "unit": data["unit"],
                "percentage": percentage,
                "severity": "inadequate",
                "priority": 2,
                "status": "inadequate"
            })
        elif percentage > 150:
            gaps.append({
                "nutrient": nutrient_name,
                "current": data["current"],
                "rdv": data["rdv"],
                "unit": data["unit"],
                "percentage": percentage,
                "severity": "excessive",
                "priority": 3,
                "status": "excessive"
            })

    # Sort by priority (critical first, then by percentage)
    gaps.sort(key=lambda x: (x["priority"], x["percentage"]))

    # Return most urgent gap
    return gaps[0] if gaps else None
```

### 📋 RDV Calculation (All Nutrients)

```python
def _calculate_rdv(self, user_profile: Dict) -> Dict[str, float]:
    """
    Calculate Recommended Daily Values for ALL nutrients.

    Based on:
    - Gender
    - Age
    - Pregnancy status
    - Lactation status
    - Anemia status
    - Activity level

    Returns:
        Dict of nutrient RDVs
    """
    gender = user_profile.get("gender", "female")
    age = user_profile.get("age", 25)
    is_pregnant = user_profile.get("is_pregnant", False)
    is_lactating = user_profile.get("is_lactating", False)
    has_anemia = user_profile.get("has_anemia", False)
    activity_level = user_profile.get("activity_level", "moderate")

    # Base RDV for adult Nigerian
    if gender == "female":
        rdv = {
            "calories": 2000,
            "protein": 46,           # g
            "carbs": 225,            # g (45-65% of calories)
            "fat": 65,               # g (20-35% of calories)
            "iron": 18,              # mg
            "calcium": 1000,         # mg
            "vitamin_a": 700,        # mcg RAE
            "zinc": 8,               # mg
        }
    else:  # male
        rdv = {
            "calories": 2500,
            "protein": 56,           # g
            "carbs": 280,            # g
            "fat": 78,               # g
            "iron": 8,               # mg
            "calcium": 1000,         # mg
            "vitamin_a": 900,        # mcg RAE
            "zinc": 11,              # mg
        }

    # Adjust for pregnancy
    if is_pregnant:
        rdv["calories"] += 340      # 2nd trimester +340, 3rd +452
        rdv["protein"] += 25        # Critical for fetal development
        rdv["iron"] = 27            # Increased blood volume
        rdv["calcium"] = 1000
        rdv["vitamin_a"] = 770
        rdv["zinc"] = 11
        rdv["carbs"] += 50

    # Adjust for lactation
    if is_lactating:
        rdv["calories"] += 500      # Milk production
        rdv["protein"] += 25
        rdv["iron"] = 9             # Returns to near-normal
        rdv["calcium"] = 1000
        rdv["vitamin_a"] = 1300     # High for breast milk
        rdv["zinc"] = 12
        rdv["carbs"] += 60

    # Adjust for anemia
    if has_anemia:
        rdv["iron"] += 10           # Extra iron for recovery
        rdv["protein"] += 5         # Support red blood cell production
        rdv["vitamin_a"] += 100     # Aids iron absorption

    # Adjust for activity level
    activity_multipliers = {
        "sedentary": 1.0,
        "light": 1.1,
        "moderate": 1.2,
        "active": 1.4,
        "very_active": 1.6,
    }

    multiplier = activity_multipliers.get(activity_level, 1.2)
    rdv["calories"] = int(rdv["calories"] * multiplier)
    rdv["protein"] = int(rdv["protein"] * multiplier)
    rdv["carbs"] = int(rdv["carbs"] * multiplier)

    return rdv
```

### 🎯 Example Scenarios

#### Scenario 1: Iron-Deficient User (Anemia)
```python
user_stats = {
    "week1_avg_iron": 4.2,      # 23% of 18mg RDV ❌ CRITICAL
    "week1_avg_protein": 52,    # 113% of 46g RDV ✅
    "week1_avg_calcium": 650,   # 65% of 1000mg RDV ⚠️
}

primary_gap = {
    "nutrient": "iron",
    "percentage": 23,
    "severity": "critical",
    "status": "deficient"
}
```
**Coaching Focus:** IRON

---

#### Scenario 2: Pregnant Woman (No Anemia)
```python
user_stats = {
    "week1_avg_iron": 18,       # 67% of 27mg RDV ⚠️
    "week1_avg_protein": 32,    # 45% of 71g RDV ❌ CRITICAL
    "week1_avg_calcium": 550,   # 55% of 1000mg RDV ⚠️
}

primary_gap = {
    "nutrient": "protein",
    "percentage": 45,
    "severity": "inadequate",
    "status": "inadequate"
}
```
**Coaching Focus:** PROTEIN (most deficient, critical for pregnancy)

---

#### Scenario 3: Active Male Athlete
```python
user_stats = {
    "week1_avg_calories": 1600,  # 55% of 3000 RDV ❌ CRITICAL
    "week1_avg_carbs": 120,      # 40% of 300g RDV ❌ CRITICAL
    "week1_avg_iron": 9,         # 112% of 8mg RDV ✅
    "week1_avg_protein": 68,     # 95% of 72g RDV ✅
}

primary_gap = {
    "nutrient": "calories",
    "percentage": 55,
    "severity": "inadequate",
    "status": "inadequate"
}
```
**Coaching Focus:** CALORIES + CARBS (needs more energy for activity)

---

#### Scenario 4: Optimal User
```python
user_stats = {
    "week1_avg_iron": 16,        # 89% of 18mg RDV ✅
    "week1_avg_protein": 50,     # 109% of 46g RDV ✅
    "week1_avg_calcium": 950,    # 95% of 1000mg RDV ✅
    "week1_avg_carbs": 210,      # 93% of 225g RDV ✅
}

primary_gap = None  # All nutrients optimal!
```
**Coaching Focus:** CELEBRATION + VARIETY

---

## GPT-4o Integration

### 🤖 Prompt Engineering

#### Learning Phase Prompt (Days 1-7)

```python
LEARNING_PHASE_PROMPT = """
You are KAI, a friendly Nigerian nutrition coach. The user is in their LEARNING PHASE (first 7 days).

Your role right now:
- Be OBSERVATIONAL, not prescriptive
- Acknowledge what they're eating with warmth
- Gently educate about nutrients in their current meal
- Encourage logging consistency
- DO NOT recommend new dishes yet
- Keep response to 2-4 sentences max
- Use emojis naturally (max 2-3)

User Profile:
- Name: {user_name}
- Gender: {gender}, Age: {age}
- Health: {health_conditions}
- Meals logged so far: {total_meals}
- Current streak: {streak} days
- Days until learning complete: {days_remaining}

Current Meal:
- Foods detected: {detected_foods}
- Calories: {calories}kcal ({calories_pct}% of {rdv_calories}kcal)
- Protein: {protein}g ({protein_pct}% of {rdv_protein}g)
- Iron: {iron}mg ({iron_pct}% of {rdv_iron}mg)
- Calcium: {calcium}mg ({calcium_pct}% of {rdv_calcium}mg)

Recent Eating Pattern (learning so far):
- Most eaten foods: {top_foods}
- Average iron: {avg_iron}mg/day
- Average protein: {avg_protein}g/day
- Logging frequency: {logging_frequency} meals/day

Generate a warm, observational coaching message (2-4 sentences). Acknowledge their current meal, mention one key nutrient, and encourage consistency. Use emojis naturally.

Example tone:
- "Welcome to KAI! Your Jollof Rice with Dodo gives you 2.8mg iron. I'm here to learn your eating habits and help you thrive. Keep logging! 🎉"
- "Great choice! Your Eba with Egusi has 6.2mg iron - your best meal yet! You're on a 3-day streak. 🔥"
- "Day 5 done! I'm noticing you love rice dishes and traditional soups. Your consistency is impressive! 💪🏾"
"""
```

#### Post-Learning Phase Prompt (Day 8+)

```python
POST_LEARNING_PROMPT = """
You are KAI, a friendly Nigerian nutrition coach. The user has completed their learning phase.

Your role now:
- Provide ACTIONABLE nutrition advice
- Focus on their PRIMARY nutritional gap
- Reference their eating history specifically
- Track progress week-over-week
- Celebrate improvements, alert on declines
- Keep response to 2-4 sentences max
- Use emojis naturally (max 2-3)

User Profile:
- Name: {user_name}
- Gender: {gender}, Age: {age}
- Health: {health_conditions}
- Total meals logged: {total_meals}
- Current streak: {streak} days

Current Meal:
- Foods: {detected_foods}
- Calories: {calories}kcal ({calories_pct}% of {rdv_calories}kcal)
- Protein: {protein}g ({protein_pct}% of {rdv_protein}g)
- Carbs: {carbs}g ({carbs_pct}% of {rdv_carbs}g)
- Fat: {fat}g ({fat_pct}% of {rdv_fat}g)
- Iron: {iron}mg ({iron_pct}% of {rdv_iron}mg)
- Calcium: {calcium}mg ({calcium_pct}% of {rdv_calcium}mg)
- Vitamin A: {vitamin_a}mcg ({vitamin_a_pct}% of {rdv_vitamin_a}mcg)
- Zinc: {zinc}mg ({zinc_pct}% of {rdv_zinc}mg)

Weekly Trends (Week 1 vs Week 2):
- Calories: {week1_calories}kcal → {week2_calories}kcal ({calories_trend})
- Protein: {week1_protein}g → {week2_protein}g ({protein_trend})
- Iron: {week1_iron}mg → {week2_iron}mg ({iron_trend})
- Calcium: {week1_calcium}mg → {week2_calcium}mg ({calcium_trend})

User's Eating Habits (learned over 7 days):
- Frequently eats: {top_foods_7d}
- Rarely eats: {bottom_foods}
- Preferred proteins: {protein_preferences}
- Preferred carbs: {carb_preferences}
- Budget tier: {budget_tier}

PRIMARY NUTRITIONAL GAP:
Nutrient: {primary_gap_nutrient}
Current intake: {primary_gap_current}{primary_gap_unit}/day ({primary_gap_percentage}% of {primary_gap_rdv}{primary_gap_unit})
Status: {primary_gap_status}
Severity: {primary_gap_severity}

SECONDARY GAPS (if any):
{secondary_gaps}

TASK:
1. Write 2-4 sentence coaching message about current meal
2. Focus on PRIMARY GAP ({primary_gap_nutrient})
3. Reference their history when relevant (e.g., "better than your Jollof from Monday")
4. If progress is good, celebrate! If declining, gently alert
5. Use emojis naturally

DO NOT:
- Recommend specific dishes in this message (recommendations come separately)
- Overwhelm with too many nutrients at once
- Be negative or discouraging

Example messages:
- "Your Efo Riro has 15.8mg iron - that's 88% of your daily goal! 🎊 This is 5X better than your usual Jollof (2.5mg). You're crushing it!"
- "Your protein is at 45% this week. 🩺 You need 71g/day during pregnancy but averaging only 32g. Your iron is great though! 💪🏾"
- "Perfect meal! Your Eba with Egusi hits 90% iron, 85% protein goals. All nutrients in the green this week! Keep it up! 🌟"
"""
```

### 🔧 GPT-4o Call Implementation

```python
async def _call_gpt4o(self, prompt: str) -> str:
    """
    Call GPT-4o to generate dynamic coaching message.

    Args:
        prompt: Formatted prompt with user context

    Returns:
        Coaching message string (2-4 sentences)
    """
    try:
        response = await self.llm.ainvoke([
            {"role": "system", "content": "You are KAI, a friendly Nigerian nutrition coach."},
            {"role": "user", "content": prompt}
        ])

        message = response.content.strip()

        # Validate length (should be 2-4 sentences)
        sentence_count = len([s for s in message.split('.') if s.strip()])
        if sentence_count > 5:
            logger.warning(f"GPT-4o returned {sentence_count} sentences, truncating")
            sentences = [s.strip() + '.' for s in message.split('.') if s.strip()]
            message = ' '.join(sentences[:4])

        return message

    except Exception as e:
        logger.error(f"GPT-4o call failed: {e}")
        # Fallback to template-based message
        return self._fallback_coaching_message(is_learning_phase=False)
```

---

## Tiered Recommendation System

### 🎯 Recommendation Philosophy

**Problem:** Users may not have access to, afford, or know how to cook recommended foods.

**Solution:** Provide 4 tiers of recommendations, allowing users to choose based on:
- Time available
- Budget
- Cooking skills
- Ingredient availability

### 📊 Recommendation Tiers

#### Tier 1: Quick Wins 🥚
**Characteristics:**
- Simple additions to current meals
- No cooking required (or minimal)
- Cheap (₦100-300)
- Immediately available
- Small nutrient boost

**Examples:**
- "Add 2 boiled eggs to your Jollof Rice" (+2.4mg iron)
- "Sprinkle crayfish powder on any meal" (+2mg iron)
- "Drink zobo instead of soft drinks" (+3mg iron)
- "Add groundnuts to your plantain" (+4g protein)

---

#### Tier 2: Easy Upgrades 🛒
**Characteristics:**
- Buy from vendors (no cooking)
- Or simple canned/packaged items
- Moderate cost (₦300-600)
- Convenient
- Medium nutrient boost

**Examples:**
- "Buy Moi Moi from vendor" (+7.2mg iron, ₦300)
- "Get Akara and Pap for breakfast" (+8g protein, ₦400)
- "Add canned sardines to your plantain" (+5mg iron)
- "Garden Egg Sauce from vendor" (+8mg iron, ₦500)

---

#### Tier 3: Full Dishes 🍲
**Characteristics:**
- Complete Nigerian meals
- Requires cooking
- Higher cost (₦800-1500)
- Targeted nutrition
- Large nutrient boost

**Examples:**
- "Efo Riro with Shaki" (+15.8mg iron, ₦1200)
- "Edikang Ikong Soup" (+12mg iron, ₦1000)
- "Ogbono Soup with stockfish" (+10mg iron, ₦900)
- "Oha Soup with goat meat" (+14mg iron, ₦1300)

---

#### Tier 4: Budget-Friendly 💰
**Characteristics:**
- Affordable full meals
- Simple ingredients
- Home-cooked
- Good nutrition for the price
- Cost (₦300-600)

**Examples:**
- "Beans porridge with palm oil" (+8.5mg iron, ₦400)
- "Moi Moi (homemade)" (+7mg iron, ₦250)
- "Vegetable soup with crayfish" (+9mg iron, ₦500)
- "Jollof Rice with eggs" (+4mg iron, ₦450)

---

### 🔧 Recommendation Generation Logic

```python
def _generate_tiered_recommendations(
    self,
    primary_gap: Dict,
    user_preferences: Dict,
    budget_tier: str = "mid"
) -> List[MealSuggestion]:
    """
    Generate 4 tiers of recommendations to address primary nutritional gap.

    Args:
        primary_gap: Dict with nutrient info
        user_preferences: User's food preferences from learning phase
        budget_tier: 'low', 'mid', 'high'

    Returns:
        List of 4 MealSuggestion objects (one per tier)
    """
    nutrient = primary_gap["nutrient"]
    rdv = primary_gap["rdv"]
    current = primary_gap["current"]
    gap_amount = rdv - current

    # Get Nigerian dishes rich in target nutrient
    dishes = self._get_nigerian_dishes_by_nutrient(
        nutrient=nutrient,
        min_amount=gap_amount * 0.3  # At least 30% of gap
    )

    # Filter based on user preferences (don't recommend foods they never eat)
    frequently_eaten = user_preferences.get("frequently_eaten", [])
    rarely_eaten = user_preferences.get("rarely_eaten", [])

    # Build recommendations
    recommendations = []

    # Tier 1: Quick Win
    quick_win = self._find_quick_win(
        nutrient=nutrient,
        frequently_eaten=frequently_eaten
    )
    if quick_win:
        recommendations.append(quick_win)

    # Tier 2: Easy Upgrade
    easy_upgrade = self._find_easy_upgrade(
        nutrient=nutrient,
        dishes=dishes,
        budget_tier=budget_tier
    )
    if easy_upgrade:
        recommendations.append(easy_upgrade)

    # Tier 3: Full Dish
    full_dish = self._find_full_dish(
        nutrient=nutrient,
        dishes=dishes,
        frequently_eaten=frequently_eaten
    )
    if full_dish:
        recommendations.append(full_dish)

    # Tier 4: Budget-Friendly
    budget_option = self._find_budget_option(
        nutrient=nutrient,
        dishes=dishes
    )
    if budget_option:
        recommendations.append(budget_option)

    return recommendations
```

### 📋 Recommendation Data Source: Knowledge Agent (RAG)

**Important:** We do NOT create a separate dish database! We use the existing Knowledge Agent with ChromaDB.

**Why?**
- ✅ Knowledge Agent already has 50+ Nigerian foods with complete nutrition data
- ✅ Avoid duplicating data (DRY principle)
- ✅ Single source of truth for all food data
- ✅ Automatically stays in sync with main database

**How Recommendations Work:**

```python
async def _generate_tiered_recommendations(
    self,
    primary_gap: Dict,
    user_preferences: Dict,
    budget_tier: str = "mid"
) -> List[MealSuggestion]:
    """
    Generate recommendations by querying Knowledge Agent.

    NO hardcoded dish database needed!
    """

    # 1. Build query for Knowledge Agent based on nutritional gap
    nutrient = primary_gap["nutrient"]
    gap_amount = primary_gap["rdv"] - primary_gap["current"]

    # 2. Query Knowledge Agent for Nigerian dishes rich in target nutrient
    # Example: "Nigerian dishes high in iron with at least 5mg per serving"
    query = f"Nigerian dishes high in {nutrient}"

    knowledge_result = await self.knowledge_agent.search(
        query=query,
        top_k=20  # Get multiple options for categorization
    )

    # 3. Categorize results into tiers using heuristics
    recommendations = self._categorize_into_tiers(
        dishes=knowledge_result.foods,
        user_preferences=user_preferences,
        target_nutrient=nutrient,
        gap_amount=gap_amount
    )

    return recommendations

def _categorize_into_tiers(
    self,
    dishes: List[FoodNutritionData],
    user_preferences: Dict,
    target_nutrient: str,
    gap_amount: float
) -> List[MealSuggestion]:
    """
    Categorize Knowledge Agent results into 4 tiers using existing metadata.

    Uses heuristics based on:
    - price_tier (from ChromaDB metadata)
    - category (from ChromaDB metadata)
    - availability (from ChromaDB metadata)
    - Food name patterns (eggs, beans, etc.)
    """

    quick_wins = []
    easy_upgrades = []
    full_dishes = []
    budget_options = []

    for dish in dishes:
        # Filter: Must have enough of target nutrient (at least 30% of gap)
        nutrient_amount = getattr(dish.nutrients_per_100g, target_nutrient, 0)
        if nutrient_amount < (gap_amount * 0.3):
            continue

        # Tier 1: Quick Wins (simple additions, very cheap)
        if self._is_quick_win(dish):
            quick_wins.append(self._format_as_meal_suggestion(dish, "quick_win"))

        # Tier 2: Easy Upgrades (vendor foods, low effort)
        elif self._is_easy_upgrade(dish):
            easy_upgrades.append(self._format_as_meal_suggestion(dish, "easy_upgrade"))

        # Tier 3: Full Dishes (complete meals, cooking required)
        elif self._is_full_dish(dish):
            full_dishes.append(self._format_as_meal_suggestion(dish, "full_dish"))

        # Tier 4: Budget-Friendly (affordable + nutritious)
        elif self._is_budget_friendly(dish):
            budget_options.append(self._format_as_meal_suggestion(dish, "budget_friendly"))

    # Return top recommendation from each tier
    return [
        quick_wins[0] if quick_wins else None,
        easy_upgrades[0] if easy_upgrades else None,
        full_dishes[0] if full_dishes else None,
        budget_options[0] if budget_options else None,
    ]

def _is_quick_win(self, dish: FoodNutritionData) -> bool:
    """Identify quick win foods (simple additions)"""
    keywords = ["egg", "groundnut", "crayfish", "zobo", "milk"]
    return (
        any(kw in dish.name.lower() for kw in keywords) or
        "addition" in dish.category.lower() or
        dish.price_tier == "low"
    )

def _is_easy_upgrade(self, dish: FoodNutritionData) -> bool:
    """Identify easy upgrade foods (vendor items)"""
    vendor_foods = ["moi moi", "akara", "pap", "kunun", "masa"]
    return (
        any(food in dish.name.lower() for food in vendor_foods) or
        (dish.price_tier in ["low", "mid"] and "widely" in dish.availability)
    )

def _is_full_dish(self, dish: FoodNutritionData) -> bool:
    """Identify full dishes (complete meals)"""
    return dish.category in [
        "vegetable_soup",
        "draw_soup",
        "pepper_soup",
        "rice_dish",
        "swallow"
    ]

def _is_budget_friendly(self, dish: FoodNutritionData) -> bool:
    """Identify budget-friendly options"""
    return dish.price_tier in ["low", "mid"]
```

**Metadata Available in ChromaDB:**
- ✅ `price_tier` (low, mid, high)
- ✅ `category` (vegetable_soup, protein, rice_dish, etc.)
- ✅ `availability` (widely_available, seasonal, etc.)
- ✅ `nutrients` (all 8+ nutrients per 100g)
- ✅ `health_benefits`
- ✅ `common_pairings`

**Optional Future Enhancement:**
Add these fields to ChromaDB for better tier classification:
- `estimated_cost_naira` (specific ₦ amount)
- `difficulty` (very_easy, easy, medium, hard)
- `cooking_time_minutes`
- `can_buy_from_vendor` (boolean)
- `is_simple_addition` (boolean)

---

## Implementation Plan

### 🏗️ Phase-by-Phase Implementation

---

### **PHASE 1: Database Schema Updates** 📊
**Duration:** 2-3 days

**Tasks:**

1. **Create new tables**
   - [ ] Create `user_nutrition_stats` table
   - [ ] Create `user_food_frequency` table
   - [ ] Create `user_recommendation_responses` table
   - [ ] Add indexes for performance

2. **Create database migration script**
   ```python
   # kai/database/migrations/add_coaching_tables.py
   ```

3. **Test database setup**
   - [ ] Run migration on test database
   - [ ] Verify foreign key constraints
   - [ ] Test query performance

**Files to create/modify:**
- `kai/database/migrations/add_coaching_tables.py` (NEW)
- `kai/database/db_setup.py` (MODIFY)
- `kai/database/stats_operations.py` (NEW)

---

### **PHASE 2: Statistics Calculation Background Job** ⚙️
**Duration:** 3-4 days

**Tasks:**

1. **Create stats calculation module**
   - [ ] Calculate weekly averages (Week 1 & Week 2)
   - [ ] Calculate nutrient trends (improving/declining/stable)
   - [ ] Update logging streaks
   - [ ] Update food frequency counts
   - [ ] Detect learning phase completion

2. **Create background job trigger**
   - [ ] Hook into meal logging endpoint
   - [ ] Run stats update asynchronously after meal saved
   - [ ] Add error handling and retries

3. **Test stats calculations**
   - [ ] Test with various user scenarios
   - [ ] Verify trend detection accuracy
   - [ ] Performance test with 1000+ users

**Files to create/modify:**
- `kai/jobs/update_user_stats.py` (NEW)
- `kai/database/stats_operations.py` (NEW)
- `kai/api/server.py` (MODIFY - add background job trigger)

**Key Functions:**
```python
# kai/jobs/update_user_stats.py

async def update_user_nutrition_stats(user_id: str) -> None:
    """
    Recalculate all user stats after meal logging.

    Updates:
    - Total meals logged
    - Current streak
    - Week 1 & Week 2 averages
    - Nutrient trends
    - Learning phase status
    """

async def update_food_frequency(user_id: str, foods: List[str]) -> None:
    """
    Update food frequency counters for recently logged foods.
    """

async def calculate_nutrient_trend(
    week1_avg: float,
    week2_avg: float
) -> str:
    """
    Determine trend: 'improving', 'declining', or 'stable'

    Logic:
    - Improving: Week1 > Week2 by >10%
    - Declining: Week1 < Week2 by >10%
    - Stable: Within 10% range
    """
```

---

### **PHASE 3: Multi-Nutrient RDV System** 🧮
**Duration:** 2-3 days

**Tasks:**

1. **Implement comprehensive RDV calculation**
   - [ ] Add RDV calculation for all 8+ nutrients
   - [ ] Account for gender, age, pregnancy, lactation, anemia, activity level
   - [ ] Test RDV accuracy against WHO/NIH standards

2. **Implement gap identification**
   - [ ] Identify primary nutritional gap
   - [ ] Rank gaps by severity
   - [ ] Return gap details for coaching

3. **Test multi-nutrient logic**
   - [ ] Test with various user profiles
   - [ ] Verify gap identification is accurate
   - [ ] Test edge cases (all optimal, all deficient)

**Files to create/modify:**
- `kai/agents/coaching_agent.py` (MODIFY - add methods)
- `kai/utils/nutrition_rdv.py` (NEW)

**Key Functions:**
```python
# kai/agents/coaching_agent.py

def _calculate_rdv(self, user_profile: Dict) -> Dict[str, float]:
    """Calculate RDV for all 8+ nutrients"""

def _identify_primary_nutritional_gap(
    self,
    user_stats: Dict,
    user_profile: Dict
) -> Dict | None:
    """Identify most critical nutrient gap"""
```

---

### **PHASE 4: Coaching Agent Refactor** 🤖
**Duration:** 5-7 days

**Tasks:**

1. **Replace hardcoded logic with dynamic generation**
   - [ ] Delete hardcoded if/else statements (lines 275-454)
   - [ ] Implement `_is_in_learning_phase()`
   - [ ] Implement `_fetch_user_stats()`
   - [ ] Implement `_fetch_recent_meals()`
   - [ ] Implement `_fetch_user_food_preferences()`
   - [ ] Implement `_build_coaching_prompt()`
   - [ ] Implement `_call_gpt4o()`
   - [ ] Implement `_generate_dynamic_coaching()`

2. **Add learning phase prompts**
   - [ ] Create learning phase prompt template
   - [ ] Create post-learning phase prompt template
   - [ ] Test prompt quality with various scenarios

3. **Add fallback logic**
   - [ ] Implement template-based fallback if GPT-4o fails
   - [ ] Add error handling and logging

4. **Test coaching output**
   - [ ] Test learning phase messages
   - [ ] Test post-learning messages
   - [ ] Test edge cases (new user, veteran user, pregnant woman)
   - [ ] Validate message quality and tone

**Files to create/modify:**
- `kai/agents/coaching_agent.py` (MAJOR REFACTOR)

**Key Methods to Add:**
```python
async def _generate_dynamic_coaching(
    self,
    knowledge_result: KnowledgeResult,
    user_stats: Dict,
    recent_meals: List[Dict],
    user_profile: Dict
) -> CoachingResult:
    """Main orchestration method"""

def _is_in_learning_phase(self, user_stats: Dict) -> bool:
    """Check if user is in first 7 days"""

async def _fetch_user_stats(self, user_id: str) -> Dict:
    """Get pre-computed stats from database"""

async def _fetch_recent_meals(self, user_id: str, days: int = 14) -> List[Dict]:
    """Get last N days of meals"""

async def _fetch_user_food_preferences(self, user_id: str) -> Dict:
    """Get frequently/rarely eaten foods"""

def _build_coaching_prompt(
    self,
    knowledge_result: KnowledgeResult,
    user_stats: Dict,
    recent_meals: List[Dict],
    user_profile: Dict,
    is_learning_phase: bool,
    primary_gap: Dict | None
) -> str:
    """Build GPT-4o prompt"""

async def _call_gpt4o(self, prompt: str) -> str:
    """Call GPT-4o API"""

def _fallback_coaching_message(self, is_learning_phase: bool) -> str:
    """Template-based fallback if GPT-4o fails"""
```

---

### **PHASE 5: Tiered Recommendation Engine** 🎯
**Duration:** 3-4 days

**Tasks:**

1. **Query Knowledge Agent for recommendations**
   - [ ] Implement Knowledge Agent query method for nutrient-rich foods
   - [ ] Build semantic search queries based on nutritional gaps
   - [ ] Filter results by nutrient content threshold

2. **Implement tier categorization logic**
   - [ ] Implement heuristic-based tier classification (quick wins, easy upgrades, full dishes, budget)
   - [ ] Use existing ChromaDB metadata (price_tier, category, availability)
   - [ ] Filter recommendations based on user preferences
   - [ ] Avoid recommending foods user never eats
   - [ ] Ensure cultural appropriateness

3. **Format recommendations as MealSuggestion objects**
   - [ ] Convert Knowledge Agent results to MealSuggestion format
   - [ ] Include cost estimates, key nutrients, why recommended
   - [ ] Add pairing suggestions from ChromaDB metadata

4. **Test recommendations**
   - [ ] Test iron deficiency recommendations
   - [ ] Test protein deficiency recommendations
   - [ ] Test calorie deficiency recommendations
   - [ ] Validate recommendation variety and tier distribution

**Files to create/modify:**
- `kai/agents/coaching_agent.py` (ADD methods)

**No separate dish database needed! Use existing Knowledge Agent with ChromaDB.**

**Key Methods:**
```python
def _generate_tiered_recommendations(
    self,
    primary_gap: Dict,
    user_preferences: Dict,
    budget_tier: str
) -> List[MealSuggestion]:
    """Generate 4 tiers of recommendations"""

def _find_quick_win(self, nutrient: str, frequently_eaten: List[str]) -> MealSuggestion:
    """Find quick addition to current meals"""

def _find_easy_upgrade(self, nutrient: str, dishes: List, budget_tier: str) -> MealSuggestion:
    """Find vendor/packaged option"""

def _find_full_dish(self, nutrient: str, dishes: List, frequently_eaten: List[str]) -> MealSuggestion:
    """Find complete dish to cook"""

def _find_budget_option(self, nutrient: str, dishes: List) -> MealSuggestion:
    """Find affordable option"""
```

---

### **PHASE 6: Integration & Testing** ✅
**Duration:** 3-4 days

**Tasks:**

1. **Integrate into API endpoints**
   - [ ] Update `/api/v1/food-logging-upload` to trigger stats update
   - [ ] Update `/api/v1/chat` to use new coaching agent
   - [ ] Return tiered recommendations in response

2. **End-to-end testing**
   - [ ] Test full user journey (Day 1 → Day 8+)
   - [ ] Test various user profiles
   - [ ] Test edge cases and error scenarios
   - [ ] Performance testing (response time <5s)

3. **Cost monitoring**
   - [ ] Monitor GPT-4o API costs
   - [ ] Implement cost tracking per user
   - [ ] Set budget alerts

4. **Documentation**
   - [ ] Update API documentation
   - [ ] Document new database schema
   - [ ] Write developer guide for coaching system

**Files to modify:**
- `kai/api/server.py` (MODIFY endpoints)
- `kai/orchestrator.py` (MODIFY workflow)

---

### **PHASE 7: User Feedback & Optimization** 🔄
**Duration:** Ongoing (post-launch)

**Tasks:**

1. **Track recommendation effectiveness**
   - [ ] Monitor which recommendations users follow (via `user_recommendation_responses` table)
   - [ ] Calculate follow-through rate per tier (quick wins vs full dishes)
   - [ ] Identify which nutrients users respond to best

2. **Optimize recommendation algorithm**
   - [ ] Update heuristics based on success rate
   - [ ] A/B test different recommendation strategies
   - [ ] Improve tier categorization logic

3. **Optional: Enhance ChromaDB metadata**
   - [ ] Add `estimated_cost_naira` field to food database
   - [ ] Add `difficulty` and `cooking_time_minutes` fields
   - [ ] Add `can_buy_from_vendor` boolean flag
   - [ ] Improve tier accuracy with richer metadata

---

## Example User Journeys

### 👨🏾 Journey 1: Tunde (25-year-old man, has anemia)

#### Day 1 - First Meal Log
**Meal:** Jollof Rice with Fried Plantain

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "Welcome to KAI, Tunde! 🎉 Your Jollof Rice with Dodo gives you 2.8mg iron (16% of your 18mg daily goal). I'm here to learn your eating habits and help you reach your nutrition goals. Keep logging!",
    "tone": "encouraging"
  }
}
```

**Learning Phase:** ✅ Active (Day 1/7)

---

#### Day 5 - Fifth Meal Log
**Meal:** Eba with Egusi Soup

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "Great choice, Tunde! 🍲 Your Eba with Egusi has 6.2mg iron - your best meal so far! You're on a 5-day logging streak. I'm learning your eating patterns.",
    "tone": "encouraging"
  }
}
```

**Learning Phase:** ✅ Active (Day 5/7)

---

#### Day 7 - Learning Complete
**Meal:** Jollof Rice with Chicken

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "You've completed 7 days with KAI! 🎊 I've learned you love Jollof Rice (eaten 4 times) and traditional soups. Your average iron intake is 4.2mg/day (23% of your 18mg goal). Starting tomorrow, I'll help you boost those numbers! 💪🏾",
    "tone": "celebratory"
  }
}
```

**Learning Phase:** ✅ Complete!

**User Stats Calculated:**
```json
{
  "total_meals_logged": 21,
  "learning_phase_complete": true,
  "week1_avg_iron": 4.2,
  "week1_avg_protein": 48,
  "week1_avg_calcium": 550,
  "top_foods_7d": ["Jollof Rice", "Eba", "Plantain", "Egusi Soup"],
  "primary_gap": {
    "nutrient": "iron",
    "percentage": 23,
    "severity": "critical"
  }
}
```

---

#### Day 8 - First Post-Learning Meal
**Meal:** Jollof Rice with Plantain (again)

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "Your Jollof Rice with Dodo has 2.5mg iron - but you're averaging only 4mg/day (22% of goal). Your iron has been low all week. 🩺 Want to boost it? Try the options below! 👇🏾",
    "nutrient_insights": [
      {
        "nutrient": "iron",
        "current_value": 2.5,
        "recommended_daily_value": 18,
        "percentage_met": 14,
        "status": "deficient",
        "advice": "Critical gap: You need 14mg more iron today"
      }
    ],
    "meal_suggestions": [
      {
        "meal_name": "Quick Win: Add 2 Boiled Eggs",
        "meal_type": "breakfast",
        "ingredients": ["eggs"],
        "estimated_cost": "₦200",
        "key_nutrients": {"iron": 2.4, "protein": 12},
        "why_recommended": "Simple addition to your current meal - instant iron boost"
      },
      {
        "meal_name": "Easy Upgrade: Buy Moi Moi from vendor",
        "meal_type": "snack",
        "ingredients": ["beans", "eggs", "pepper"],
        "estimated_cost": "₦300",
        "key_nutrients": {"iron": 7.2, "protein": 18},
        "why_recommended": "No cooking needed - available at any Nigerian vendor"
      },
      {
        "meal_name": "Power Meal: Efo Riro with Shaki",
        "meal_type": "lunch",
        "ingredients": ["spinach", "shaki", "stockfish", "crayfish", "palm oil"],
        "estimated_cost": "₦1200",
        "key_nutrients": {"iron": 15.8, "protein": 22},
        "why_recommended": "Addresses your iron deficiency in ONE meal - pairs great with your favorite Eba"
      },
      {
        "meal_name": "Budget Option: Beans Porridge with Palm Oil",
        "meal_type": "dinner",
        "ingredients": ["beans", "palm oil", "crayfish", "pepper"],
        "estimated_cost": "₦400",
        "key_nutrients": {"iron": 8.5, "protein": 15},
        "why_recommended": "Affordable iron boost - similar cooking style to your usual meals"
      }
    ],
    "motivational_tip": "Small changes = big results! Even adding eggs to your Jollof doubles your iron intake. 🥚",
    "tone": "supportive"
  }
}
```

**Learning Phase:** ❌ Complete (Now giving recommendations!)

---

#### Day 10 - User Follows Recommendation!
**Meal:** Efo Riro with Shaki (KAI recommended this!)

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "YES, Tunde! 🎊 Your Efo Riro just gave you 15.8mg iron - that's 88% of your daily goal in ONE meal! This is 5X better than your usual Jollof (2.5mg). You're crushing it! 🔥",
    "tone": "celebratory"
  }
}
```

**Progress Tracked:**
```json
{
  "week1_avg_iron": 4.2,
  "week2_avg_iron": 9.5,
  "iron_trend": "improving"
}
```

---

### 👩🏾‍🦱 Journey 2: Amina (28-year-old pregnant woman, no anemia)

#### Day 8 - Post-Learning Meal
**Meal:** Jollof Rice with Chicken

**User Stats:**
```json
{
  "week1_avg_iron": 18,      // 67% of 27mg RDV (pregnant)
  "week1_avg_protein": 32,   // 45% of 71g RDV (pregnant) ❌ PRIMARY GAP
  "week1_avg_calcium": 550   // 55% of 1000mg RDV
}
```

**API Response:**
```json
{
  "coaching": {
    "personalized_message": "Your Jollof Rice has 8g protein, but you need 71g/day during pregnancy! 🤰🏾 You're only at 45% this week. Try adding fish, beans, or Moi Moi to boost protein. Your iron is great though! 💪🏾",
    "nutrient_insights": [
      {
        "nutrient": "protein",
        "current_value": 8,
        "recommended_daily_value": 71,
        "percentage_met": 11,
        "status": "deficient",
        "advice": "Critical for baby's development - need 63g more today"
      }
    ],
    "meal_suggestions": [
      {
        "meal_name": "Quick Win: Add Fish to your Jollof",
        "key_nutrients": {"protein": 20, "iron": 3.5},
        "estimated_cost": "₦500"
      },
      {
        "meal_name": "Easy Upgrade: Buy Moi Moi (2 wraps)",
        "key_nutrients": {"protein": 18, "iron": 7.2},
        "estimated_cost": "₦300"
      },
      {
        "meal_name": "Power Meal: Egusi Soup with Fish and Beef",
        "key_nutrients": {"protein": 35, "iron": 12},
        "estimated_cost": "₦1500"
      },
      {
        "meal_name": "Budget Option: Beans Porridge with Fish",
        "key_nutrients": {"protein": 25, "iron": 9},
        "estimated_cost": "₦600"
      }
    ],
    "tone": "supportive"
  }
}
```

**Focus:** PROTEIN (not iron, because protein is more deficient!)

---

## Cost & Performance Considerations

### 💰 GPT-4o Cost Analysis

**Pricing (as of 2024):**
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

**Per Coaching Message:**
- Input tokens: ~800 (user context + prompt)
- Output tokens: ~100 (2-4 sentence message)
- Cost per message: ~$0.003

**Monthly Cost (1000 active users, 3 meals/day):**
- Messages per month: 1000 users × 3 meals × 30 days = 90,000 messages
- Total cost: 90,000 × $0.003 = **$270/month**

**Annual Cost:** ~$3,240/year

**Cost per user per year:** $3.24

---

### ⚡ Performance Optimization

#### 1. Pre-compute Statistics (Don't Calculate in Real-Time)
**Problem:** Calculating week averages and trends in real-time = slow

**Solution:** Background job updates stats after each meal log
- Stats query: <50ms (pre-computed)
- vs. Real-time calculation: 2-3 seconds

#### 2. Cache RDV Calculations
**Problem:** RDV calculation happens every coaching message

**Solution:** Cache RDV in user profile, recalculate only when profile changes
- Cached RDV lookup: <5ms
- vs. Fresh calculation: 20-30ms

#### 3. Parallel Database Queries
**Problem:** Sequential queries slow down response

**Solution:** Fetch user stats, recent meals, food preferences in parallel
```python
async def _fetch_coaching_context(self, user_id: str):
    # Parallel queries
    stats, meals, preferences = await asyncio.gather(
        self._fetch_user_stats(user_id),
        self._fetch_recent_meals(user_id),
        self._fetch_user_food_preferences(user_id)
    )
    return stats, meals, preferences
```

#### 4. GPT-4o Response Streaming (Future Enhancement)
**Problem:** Waiting for full GPT-4o response delays user

**Solution:** Stream GPT-4o response token-by-token to frontend
- Perceived latency: <500ms (first tokens arrive)
- vs. Full response: 2-3 seconds

---

### 🎯 Target Performance Metrics

| Metric | Target | Current (Estimated) |
|--------|--------|---------------------|
| API Response Time (food logging) | <5s | ~3.5s (with GPT-4o) |
| Stats Update (background) | <2s | ~1s |
| GPT-4o Call | <3s | ~2.5s |
| Database Queries | <100ms | ~50ms (pre-computed) |
| Overall Coaching Generation | <4s | ~3s |

---

## Summary Checklist

### ✅ What We're Building

- [x] **Dynamic Coaching System** - GPT-4o replaces hardcoded templates
- [x] **Learning Phase** - 7 days observational, then recommendations
- [x] **Multi-Nutrient Focus** - Track all 8+ nutrients, not just iron
- [x] **Tiered Recommendations** - Quick wins → Full dishes
- [x] **Personalized Context** - Reference user history specifically
- [x] **Progress Tracking** - Week-over-week trends and streaks
- [x] **Gender Neutral** - Adapt RDV based on user profile
- [x] **Culturally Appropriate** - Only Nigerian dishes and combos

### 📋 Implementation Phases

1. ✅ Database schema updates (3 new tables)
2. ✅ Stats calculation background job
3. ✅ Multi-nutrient RDV system
4. ✅ Coaching agent refactor (delete hardcoded logic)
5. ✅ Tiered recommendation engine (using Knowledge Agent - no separate database!)
6. ✅ Integration & testing
7. ✅ User feedback & optimization (ongoing)

### 🎯 Success Metrics

**User Engagement:**
- Logging streak retention: >60% (7+ day streaks)
- Recommendation follow-through: >30%
- User satisfaction: >4.5/5 stars

**Technical Performance:**
- API response time: <5s
- GPT-4o cost: <$0.005 per message
- Database query time: <100ms

**Nutritional Impact:**
- Nutrient improvement after 30 days: >25%
- Primary gap closure: >40%
- User learning phase completion: >70%

---

## Next Steps

1. **Review this document** with team
2. **Get approval** on architecture and cost estimates
3. **Start Phase 1** (Database schema updates)
4. **Set up development environment** for testing
5. **Create project tracking board** for phases

---

**Document Version:** 1.0
**Last Updated:** 2025-01-15
**Author:** KAI Development Team
