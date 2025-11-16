# KAI Coaching Agent API Guide

**Last Updated:** November 15, 2025

## Overview

The KAI Coaching Agent provides **personalized, stats-based nutrition coaching** using GPT-4o. It adapts to user history, detects learning phases, and provides culturally-aware Nigerian nutrition guidance.

---

## Quick Start

### Basic Usage (with user stats)

```python
from kai.agents.coaching_agent import CoachingAgent
from kai.models import KnowledgeResult

# Initialize coaching agent
coaching_agent = CoachingAgent()

# Generate coaching for a user
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",  # Required for personalized coaching
    knowledge_result=knowledge_result,  # From Knowledge Agent
    user_context={
        "budget": "mid",  # Optional: "low" | "mid" | "high"
        "activity_level": "moderate",  # Optional: for RDV calculation
        "use_web_research": True  # Optional: enable Tavily MCP enrichment
    }
)

print(coaching_result.personalized_message)
# "Great job logging Egusi soup and Eba! Your iron intake has improved 15%
#  from last week - that's fantastic progress."
```

### Anonymous User (fallback mode)

```python
# For users without login/history
coaching_result = await coaching_agent.provide_coaching(
    user_id="anonymous",  # Uses default profile
    knowledge_result=knowledge_result,
    user_context={"budget": "mid"}
)
```

---

## API Reference

### CoachingAgent.provide_coaching()

**Signature:**
```python
async def provide_coaching(
    self,
    user_id: str,
    knowledge_result: KnowledgeResult,
    user_context: Optional[Dict[str, Any]] = None
) -> CoachingResult
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | `str` | ✅ Yes | User ID to fetch stats for. Use `"anonymous"` for users without login. |
| `knowledge_result` | `KnowledgeResult` | ✅ Yes | Nutrition data from Knowledge Agent containing foods and nutrients. |
| `user_context` | `Dict[str, Any]` | ❌ No | Optional context overrides (budget, activity_level, use_web_research). |

**user_context Options:**

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `budget` | `str` | `"mid"` | `"low"` \| `"mid"` \| `"high"` | User's budget tier for meal recommendations |
| `activity_level` | `str` | `"moderate"` | `"sedentary"` \| `"light"` \| `"moderate"` \| `"active"` \| `"very_active"` | User's activity level for RDV calculation |
| `use_web_research` | `bool` | `False` | `True` \| `False` | Enable Tavily MCP for web research enrichment |

**Returns:**

`CoachingResult` object with:
- `personalized_message` (str): Warm, context-aware coaching message
- `nutrient_insights` (List[NutrientInsight]): Insights for 3-5 key nutrients
- `meal_suggestions` (List[MealSuggestion]): Meal recommendations (Phase 5)
- `motivational_tip` (str): Encouraging tip based on user progress
- `next_steps` (List[str]): 3-5 actionable next steps
- `tone` (str): Tone of coaching ("encouraging", "educational", etc.)

---

## Data Models

### CoachingResult

```python
from kai.models import CoachingResult

result = CoachingResult(
    personalized_message="Great job logging your meal!",
    nutrient_insights=[...],
    meal_suggestions=[...],
    motivational_tip="You're on a 5-day streak!",
    next_steps=[
        "Add calcium-rich foods to your next meal",
        "Keep logging meals to maintain your streak"
    ],
    tone="encouraging"
)
```

### NutrientInsight

```python
from kai.models import NutrientInsight

insight = NutrientInsight(
    nutrient="iron",
    current_value=15.5,
    recommended_daily_value=18.0,
    percentage_met=86.1,
    status="adequate",  # "deficient" | "adequate" | "optimal"
    advice="You're doing well with iron! Keep eating iron-rich foods."
)
```

---

## Coaching Modes

### Learning Phase Mode (First 7 days OR 21 meals)

**Behavior:**
- **Observational**, not prescriptive
- Celebrates logging behavior
- Gently educates about nutrients
- Builds trust and rapport
- Avoids overwhelming with recommendations

**Example Output:**
```python
CoachingResult(
    personalized_message="Great job logging your meal: Jollof rice and chicken! Keep tracking your meals to help me learn your eating patterns.",

    nutrient_insights=[
        # Simple, educational insights
        NutrientInsight(
            nutrient="protein",
            current_value=45.0,
            recommended_daily_value=57.5,
            percentage_met=78.3,
            status="adequate",
            advice="Protein helps build and repair your muscles. You're doing well!"
        )
    ],

    motivational_tip="You're building a healthy habit by logging your meals. Consistency is key!",

    next_steps=[
        "Log your next meal to build your tracking history",
        "Keep eating a variety of foods",
        "You're doing great - keep it up!"
    ]
)
```

### Post-Learning Phase Mode

**Behavior:**
- **Prescriptive** and actionable
- Identifies primary nutritional gap
- References user history and trends
- Provides specific recommendations
- Tracks week-over-week progress

**Example Output:**
```python
CoachingResult(
    personalized_message="Great job logging Egusi soup and Eba! Your iron intake has improved 15% from last week - that's fantastic progress. Let's focus on calcium next - you're at 60% of your target.",

    nutrient_insights=[
        # Primary gap (calcium)
        NutrientInsight(
            nutrient="calcium",
            current_value=600.0,
            recommended_daily_value=1000.0,
            percentage_met=60.0,
            status="deficient",
            advice="Your calcium is at 60% of target. Add more yogurt, milk, or dairy to boost calcium. Foods like yogurt, milk, and leafy greens are great sources."
        ),

        # Improving nutrient (iron)
        NutrientInsight(
            nutrient="iron",
            current_value=15.5,
            recommended_daily_value=18.0,
            percentage_met=86.1,
            status="adequate",
            advice="Great progress! Your iron intake improved 15% from last week. Keep eating iron-rich foods like your Egusi soup."
        ),

        # Other important nutrients
        NutrientInsight(
            nutrient="protein",
            current_value=52.0,
            recommended_daily_value=57.5,
            percentage_met=90.4,
            status="optimal",
            advice="You're meeting your protein needs consistently. Well done!"
        )
    ],

    motivational_tip="You're on a 5-day logging streak! Your iron intake is trending up - keep it going!",

    next_steps=[
        "Add calcium-rich foods like yogurt or milk to your next meal",
        "Try adding more leafy greens (e.g., spinach, kale) for vitamin A",
        "Keep logging meals to maintain your 5-day streak",
        "Great job with iron - let's focus on calcium next"
    ]
)
```

---

## Integration Examples

### Full Food Logging Flow

```python
from kai.orchestrator import handle_user_request

# User uploads food image
response = await handle_user_request(
    user_message="What did I eat for lunch?",
    image_base64=base64_image_data,
    user_id="user123",
    user_gender="female",
    user_age=28
)

# Response contains:
# - vision: VisionResult (detected foods)
# - nutrition: KnowledgeResult (nutrition data)
# - coaching: CoachingResult (personalized coaching)
# - daily_totals: Dict (today's totals)

print(response["coaching"].personalized_message)
print(response["coaching"].nutrient_insights)
print(response["coaching"].next_steps)
```

### Nutrition Query Flow

```python
# User asks nutrition question
response = await handle_user_request(
    user_message="How much iron is in Egusi soup?",
    user_id="user123"
)

# Response contains:
# - nutrition: KnowledgeResult (nutrition data for Egusi)
# - coaching: CoachingResult (personalized answer + recommendations)

print(response["coaching"].personalized_message)
# "Egusi soup contains about 5mg of iron per serving. Based on your history,
#  you're averaging 12mg/day, which is 67% of your 18mg target. Adding Egusi
#  soup more often could help boost your iron intake!"
```

### Health Coaching Flow

```python
# User asks health question
response = await handle_user_request(
    user_message="How can I improve my iron intake?",
    user_id="user123"
)

# Response contains:
# - coaching: CoachingResult (personalized coaching)

print(response["coaching"].personalized_message)
# "Your iron intake has been averaging 12mg/day (67% of your 18mg target).
#  To improve, try adding more iron-rich Nigerian foods like Egusi soup,
#  beans, or leafy greens. Based on your history, you already eat Egusi
#  soup 3x/week - try increasing to 5x/week!"
```

---

## Personalized RDV Calculation

The coaching agent automatically calculates **personalized RDV** for each user based on:
- Gender (male/female)
- Age (19-50 vs 51+)
- Activity level (sedentary → very active)

**Example:**

```python
# Female, 28 years old, moderate activity
# RDV will be:
# - Calories: 2500 kcal (2000 base × 1.25 activity)
# - Protein: 57.5g (46 base × 1.25)
# - Iron: 22.5mg (18 base × 1.25)
# - Calcium: 1000mg
# - ... (all 8 nutrients)

# Male, 55 years old, sedentary activity
# RDV will be:
# - Calories: 2250 kcal (2500 base × 0.9 age adjustment)
# - Protein: 56g (no change)
# - Iron: 8mg (lower for males)
# - Calcium: 1200mg (higher for 51+)
# - ... (all 8 nutrients)
```

**Nutrients Tracked:**
1. Calories (kcal)
2. Protein (g)
3. Carbohydrates (g)
4. Fat (g)
5. Iron (mg)
6. Calcium (mg)
7. Vitamin A (mcg RAE)
8. Zinc (mg)

---

## Gap Analysis

The coaching agent identifies **nutritional gaps** and prioritizes them:

**Priority Levels:**
- **High:** < 50% of RDV met
- **Medium:** 50-75% of RDV met
- **Low:** 75-90% of RDV met
- **Met:** ≥ 90% of RDV met

**Primary Gap:**
The nutrient with the **largest absolute gap** among high/medium priority nutrients.

**Example:**
```python
# User stats:
# - Iron: 12mg / 18mg (67%) → Medium priority, gap = 6mg
# - Calcium: 500mg / 1000mg (50%) → Medium priority, gap = 500mg
# - Protein: 52g / 57.5g (90%) → Met

# Primary gap: CALCIUM (largest absolute gap = 500mg)
# Coaching will focus on calcium recommendations
```

---

## Trend Awareness

The coaching agent tracks **week-over-week trends** for all 8 nutrients:

**Trends:**
- **Improving:** Intake increased >10% from last week
- **Declining:** Intake decreased >10% from last week
- **Stable:** Intake changed <10% from last week

**Example:**
```python
# Week 2 (8-14 days ago): Iron = 10mg/day
# Week 1 (last 7 days): Iron = 12mg/day
# Trend: Improving (+20%)

# Coaching message:
# "Great progress! Your iron intake improved 20% from last week."
```

---

## Tavily MCP Enrichment

When `use_web_research: True` is set, the coaching agent can enrich responses with **web research** via Tavily MCP:

**When Triggered:**
- User explicitly requests web research
- Deficiency detected (any nutrient < 70% of RDV)

**Example:**
```python
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",
    knowledge_result=knowledge_result,
    user_context={"use_web_research": True}
)

# If user has iron deficiency:
# - Tavily query: "Nigerian foods to improve iron"
# - Result enriches coaching message with research insights
# - Sources added to next_steps

print(coaching_result.personalized_message)
# "Your iron is at 60% of target. Research insight: Dark leafy greens like
#  spinach and ewedu are excellent sources of iron for Nigerians."

print(coaching_result.next_steps)
# [
#   "Add iron-rich foods like spinach, beans, or liver to your next meal",
#   "Source: Iron-Rich Nigerian Foods - https://example.com/...",
#   "Source: Boosting Iron Naturally - https://example.com/..."
# ]
```

---

## Best Practices

### 1. Always Provide user_id
```python
# ✅ Good: Personalized coaching with user stats
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",
    knowledge_result=knowledge_result
)

# ❌ Bad: Anonymous fallback (less personalized)
coaching_result = await coaching_agent.provide_coaching(
    user_id="anonymous",
    knowledge_result=knowledge_result
)
```

### 2. Set activity_level for Accurate RDV
```python
# ✅ Good: Accurate RDV based on user activity
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",
    knowledge_result=knowledge_result,
    user_context={"activity_level": "very_active"}  # User is athlete
)
```

### 3. Use Web Research for Deficiencies
```python
# ✅ Good: Enrich coaching with research for deficient users
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",
    knowledge_result=knowledge_result,
    user_context={"use_web_research": True}  # Enable Tavily MCP
)
```

### 4. Handle Stats Updates Before Coaching
```python
# ✅ Good: Update stats BEFORE generating coaching
from kai.jobs import calculate_and_update_user_stats

# Log meal first
await log_meal(user_id, meal_type, foods)

# Update stats (so coaching has latest data)
await calculate_and_update_user_stats(user_id)

# Generate coaching (uses fresh stats)
coaching_result = await coaching_agent.provide_coaching(
    user_id=user_id,
    knowledge_result=knowledge_result
)
```

---

## Error Handling

```python
try:
    coaching_result = await coaching_agent.provide_coaching(
        user_id="user123",
        knowledge_result=knowledge_result
    )
except Exception as e:
    logger.error(f"Coaching generation failed: {e}")

    # Fallback: Simple generic coaching
    coaching_result = CoachingResult(
        personalized_message="Thanks for logging your meal!",
        nutrient_insights=[],
        meal_suggestions=[],
        motivational_tip="Keep tracking your meals for better insights.",
        next_steps=["Log your next meal", "Stay consistent"],
        tone="encouraging"
    )
```

---

## Migration Guide (Phase 3 → Phase 4)

### Old Signature (Deprecated)
```python
# Phase 3 (deprecated)
coaching_result = await coaching_agent.provide_coaching(
    knowledge_result=knowledge_result,
    user_context={
        "is_pregnant": False,
        "health_goals": ["increase_iron"],
        "budget": "mid"
    }
)
```

### New Signature (Current)
```python
# Phase 4 (current)
coaching_result = await coaching_agent.provide_coaching(
    user_id="user123",  # ← NEW: Required for stats-based coaching
    knowledge_result=knowledge_result,
    user_context={
        "budget": "mid",
        "activity_level": "moderate",  # ← NEW: For RDV calculation
        "use_web_research": True  # ← NEW: Enable Tavily MCP
    }
)
```

**Breaking Changes:**
- ✅ `user_id` is now **required** (use `"anonymous"` for fallback)
- ❌ `is_pregnant` removed (will be added in future phase)
- ❌ `health_goals` removed (inferred from stats)
- ✅ `activity_level` added (for personalized RDV)
- ✅ `use_web_research` added (for Tavily MCP)

---

## Testing

```python
import asyncio
from kai.agents.coaching_agent import CoachingAgent
from kai.models import KnowledgeResult

async def test_coaching():
    """Test coaching agent"""
    agent = CoachingAgent()

    # Mock knowledge result
    knowledge_result = KnowledgeResult(
        foods=[...],
        total_calories=1850,
        total_protein=45,
        total_iron=12,
        total_calcium=600,
        query_interpretation="Egusi soup and Eba",
        sources_used=["ChromaDB"]
    )

    # Generate coaching
    result = await agent.provide_coaching(
        user_id="test_user_001",
        knowledge_result=knowledge_result,
        user_context={"budget": "mid", "activity_level": "moderate"}
    )

    print(f"Message: {result.personalized_message}")
    print(f"Insights: {len(result.nutrient_insights)}")
    print(f"Next steps: {len(result.next_steps)}")

# Run test
asyncio.run(test_coaching())
```

---

## Performance

- **Average latency:** 2-4 seconds (GPT-4o generation)
- **Tavily MCP enrichment:** +1-2 seconds (optional)
- **Stats calculation:** <500ms (runs in background)
- **RDV calculation:** <50ms (fast utility function)

**Optimization Tips:**
- Cache user stats for 5-10 minutes
- Use `timeout=45.0` for GPT-4o calls
- Handle stats updates asynchronously
- Fallback to simple template if GPT-4o fails

---

## Support

**Documentation:**
- [Implementation Status](../IMPLEMENTATION_STATUS.md)
- [RDV Calculator Guide](../kai/utils/nutrition_rdv.py)
- [Stats Job Guide](../kai/jobs/update_user_stats.py)

**Issues:**
- GitHub: [Create Issue](https://github.com/your-repo/issues)
- Email: support@kai.com

---

**Last Updated:** November 15, 2025
**Version:** Phase 4
