"""
Goal-Driven Nutrient Priority Service

Assigns 6-8 priority nutrients per health goal, with personalized RDVs
based on gender, age, and goal. KAI is the nutrition expert - users don't
choose nutrients, the system intelligently assigns them.

Nutrient Pool (16 total):
- Macros (5): calories, protein, carbohydrates, fat, fiber
- Minerals (6): iron, calcium, zinc, potassium, sodium, magnesium
- Vitamins (5): vitamin_a, vitamin_c, vitamin_d, vitamin_b12, folate
"""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum


class HealthGoal(str, Enum):
    """Supported health goals"""
    LOSE_WEIGHT = "lose_weight"
    GAIN_MUSCLE = "gain_muscle"
    MAINTAIN_WEIGHT = "maintain_weight"
    GENERAL_WELLNESS = "general_wellness"
    PREGNANCY = "pregnancy"
    HEART_HEALTH = "heart_health"
    ENERGY_BOOST = "energy_boost"
    BONE_HEALTH = "bone_health"


# =============================================================================
# NUTRIENT EMOJI MAPPING
# Visual icons for each nutrient (used in frontend/API responses)
# =============================================================================

NUTRIENT_EMOJIS: Dict[str, str] = {
    # Macros
    "calories": "🔥",
    "protein": "💪",
    "carbohydrates": "🍚",
    "fat": "🧈",
    "fiber": "🌾",
    # Minerals
    "iron": "🩸",
    "calcium": "🦴",
    "zinc": "⚡",
    "potassium": "🍌",
    "sodium": "🧂",
    "magnesium": "💎",
    # Vitamins
    "vitamin_a": "👁️",
    "vitamin_c": "🍊",
    "vitamin_d": "☀️",
    "vitamin_b12": "🔋",
    "folate": "🧬",
}


def get_nutrient_emoji(nutrient: str) -> str:
    """Get the emoji for a nutrient"""
    return NUTRIENT_EMOJIS.get(nutrient, "📊")


# =============================================================================
# GOAL METADATA
# Display names, emojis, and primary nutrients for each health goal
# =============================================================================

GOAL_METADATA: Dict[str, Dict[str, str]] = {
    "lose_weight": {
        "display_name": "Weight Loss",
        "emoji": "🏃",
        "primary_nutrient": "protein",  # Satiety + muscle preservation
        "description": "Lose weight while preserving muscle mass",
    },
    "gain_muscle": {
        "display_name": "Muscle Gain",
        "emoji": "💪",
        "primary_nutrient": "protein",  # Muscle protein synthesis
        "description": "Build lean muscle with proper nutrition",
    },
    "maintain_weight": {
        "display_name": "Weight Maintenance",
        "emoji": "⚖️",
        "primary_nutrient": "protein",  # Prevents muscle loss
        "description": "Maintain your current healthy weight",
    },
    "general_wellness": {
        "display_name": "General Wellness",
        "emoji": "🌟",
        "primary_nutrient": "protein",  # Foundation for body maintenance
        "description": "Overall health and balanced nutrition",
    },
    "pregnancy": {
        "display_name": "Pregnancy",
        "emoji": "🤰",
        "primary_nutrient": "folate",  # CRITICAL for neural tube development
        "description": "Optimal nutrition for you and baby",
    },
    "heart_health": {
        "display_name": "Heart Health",
        "emoji": "❤️",
        "primary_nutrient": "sodium",  # Blood pressure control (limit it)
        "description": "Cardiovascular health and blood pressure",
    },
    "energy_boost": {
        "display_name": "Energy Boost",
        "emoji": "⚡",
        "primary_nutrient": "iron",  # Oxygen transport = energy
        "description": "Combat fatigue and boost energy levels",
    },
    "bone_health": {
        "display_name": "Bone Health",
        "emoji": "🦴",
        "primary_nutrient": "calcium",  # Primary bone mineral
        "description": "Strong bones and skeletal health",
    },
}


def get_goal_emoji(goal: str) -> str:
    """Get the emoji for a health goal"""
    return GOAL_METADATA.get(goal, {}).get("emoji", "🎯")


def get_goal_display_name(goal: str) -> str:
    """Get the display name for a health goal"""
    return GOAL_METADATA.get(goal, {}).get("display_name", goal.replace("_", " ").title())


def get_primary_nutrient(goal: str) -> str:
    """Get the primary nutrient for a health goal (the one to focus on most)"""
    return GOAL_METADATA.get(goal, {}).get("primary_nutrient", "protein")


@dataclass
class NutrientRDV:
    """Recommended Daily Value for a nutrient"""
    name: str
    amount: float
    unit: str
    display_name: str


# =============================================================================
# GOAL-DRIVEN NUTRIENT MAPPINGS
# Each goal gets 6-8 priority nutrients based on nutritional science
# =============================================================================

GOAL_NUTRIENT_PRIORITIES: Dict[str, List[str]] = {
    # Weight Loss (6 nutrients) - Focus on satiety and metabolic health
    "lose_weight": [
        "calories",      # Primary: caloric deficit
        "protein",       # Preserve muscle, increase satiety
        "fiber",         # Satiety, gut health
        "carbohydrates", # Manage for energy balance
        "fat",           # Essential but controlled
        "sodium",        # Reduce water retention
    ],

    # Muscle Gain (7 nutrients) - Focus on protein synthesis and recovery
    "gain_muscle": [
        "calories",      # Caloric surplus needed
        "protein",       # Primary: muscle synthesis
        "carbohydrates", # Energy for workouts
        "fat",           # Hormone production
        "zinc",          # Testosterone, protein synthesis
        "magnesium",     # Muscle function, recovery
        "vitamin_b12",   # Energy metabolism, red blood cells
    ],

    # Weight Maintenance (6 nutrients) - Balanced tracking
    "maintain_weight": [
        "calories",      # Maintain energy balance
        "protein",       # Maintain muscle mass
        "carbohydrates", # Sustained energy
        "fat",           # Essential fatty acids
        "fiber",         # Digestive health
        "iron",          # Energy and vitality
    ],

    # General Wellness (6 nutrients) - Broad health coverage
    "general_wellness": [
        "calories",      # Energy balance
        "protein",       # Body maintenance
        "fiber",         # Gut health
        "iron",          # Energy, immunity
        "vitamin_c",     # Immunity, antioxidant
        "calcium",       # Bone, muscle function
    ],

    # Pregnancy (8 nutrients) - Maximum nutrients for fetal development
    "pregnancy": [
        "calories",      # Increased energy needs (+300 kcal)
        "protein",       # Fetal growth
        "folate",        # CRITICAL: neural tube development
        "iron",          # Blood volume, prevent anemia
        "calcium",       # Bone development
        "vitamin_d",     # Calcium absorption, immunity
        "zinc",          # Cell division, immune function
        "vitamin_b12",   # Neurological development
    ],

    # Heart Health (7 nutrients) - Cardiovascular focus
    "heart_health": [
        "calories",      # Weight management
        "sodium",        # Blood pressure control (limit)
        "potassium",     # Blood pressure balance
        "fiber",         # Cholesterol management
        "fat",           # Limit saturated fats
        "magnesium",     # Heart rhythm, blood pressure
        "vitamin_c",     # Antioxidant, vascular health
    ],

    # Energy Boost (6 nutrients) - Combat fatigue
    "energy_boost": [
        "calories",      # Adequate energy intake
        "iron",          # Oxygen transport, prevent fatigue
        "vitamin_b12",   # Energy metabolism
        "carbohydrates", # Primary energy source
        "magnesium",     # ATP production
        "vitamin_c",     # Iron absorption
    ],

    # Bone Health (7 nutrients) - Skeletal strength
    "bone_health": [
        "calories",      # Maintain healthy weight
        "calcium",       # Primary bone mineral
        "vitamin_d",     # Calcium absorption
        "protein",       # Bone matrix
        "magnesium",     # Bone structure
        "zinc",          # Bone formation
        "potassium",     # Reduce calcium loss
    ],
}


# =============================================================================
# PERSONALIZED RDV CALCULATIONS
# Based on gender, age, activity level, and goal
# =============================================================================

# Base RDVs by gender (adult defaults)
BASE_RDVS_MALE: Dict[str, tuple] = {
    # (amount, unit, display_name)
    "calories": (2500, "kcal", "Calories"),
    "protein": (56, "g", "Protein"),
    "carbohydrates": (300, "g", "Carbs"),
    "fat": (78, "g", "Fat"),
    "fiber": (38, "g", "Fiber"),
    "iron": (8, "mg", "Iron"),
    "calcium": (1000, "mg", "Calcium"),
    "zinc": (11, "mg", "Zinc"),
    "potassium": (3400, "mg", "Potassium"),
    "sodium": (2300, "mg", "Sodium"),
    "magnesium": (420, "mg", "Magnesium"),
    "vitamin_a": (900, "mcg", "Vitamin A"),
    "vitamin_c": (90, "mg", "Vitamin C"),
    "vitamin_d": (15, "mcg", "Vitamin D"),
    "vitamin_b12": (2.4, "mcg", "Vitamin B12"),
    "folate": (400, "mcg", "Folate"),
}

BASE_RDVS_FEMALE: Dict[str, tuple] = {
    "calories": (2000, "kcal", "Calories"),
    "protein": (46, "g", "Protein"),
    "carbohydrates": (250, "g", "Carbs"),
    "fat": (65, "g", "Fat"),
    "fiber": (25, "g", "Fiber"),
    "iron": (18, "mg", "Iron"),  # Higher for menstruating women
    "calcium": (1000, "mg", "Calcium"),
    "zinc": (8, "mg", "Zinc"),
    "potassium": (2600, "mg", "Potassium"),
    "sodium": (2300, "mg", "Sodium"),
    "magnesium": (320, "mg", "Magnesium"),
    "vitamin_a": (700, "mcg", "Vitamin A"),
    "vitamin_c": (75, "mg", "Vitamin C"),
    "vitamin_d": (15, "mcg", "Vitamin D"),
    "vitamin_b12": (2.4, "mcg", "Vitamin B12"),
    "folate": (400, "mcg", "Folate"),
}

# Goal-specific RDV adjustments (multipliers)
GOAL_RDV_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "lose_weight": {
        "calories": 0.80,     # 20% deficit
        "protein": 1.20,      # Higher protein for satiety
        "sodium": 0.85,       # Reduce sodium
    },
    "gain_muscle": {
        "calories": 1.15,     # 15% surplus
        "protein": 1.60,      # Much higher protein (1.6-2.2g/kg)
        "carbohydrates": 1.20,
        "zinc": 1.10,
    },
    "maintain_weight": {
        # No adjustments - use base RDVs
    },
    "general_wellness": {
        # No adjustments - use base RDVs
    },
    "pregnancy": {
        "calories": 1.15,     # +300 kcal in 2nd/3rd trimester
        "protein": 1.30,      # +25g/day
        "iron": 1.50,         # 27mg vs 18mg
        "folate": 1.50,       # 600mcg vs 400mcg
        "calcium": 1.00,      # Same but critical
        "vitamin_d": 1.00,    # Same but critical
    },
    "heart_health": {
        "sodium": 0.65,       # Max 1500mg
        "potassium": 1.10,    # Increase for BP balance
        "fiber": 1.20,        # More fiber for cholesterol
    },
    "energy_boost": {
        "iron": 1.10,
        "vitamin_b12": 1.10,
        "magnesium": 1.10,
    },
    "bone_health": {
        "calcium": 1.20,      # 1200mg for bone health
        "vitamin_d": 1.33,    # 20mcg for better absorption
    },
}

# Age adjustments
AGE_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "under_30": {},  # Base rates
    "30_50": {
        "calcium": 1.0,
    },
    "over_50": {
        "calcium": 1.20,      # Increased bone loss risk
        "vitamin_d": 1.33,    # Reduced skin synthesis
        "vitamin_b12": 1.25,  # Reduced absorption
        "protein": 1.10,      # Prevent muscle loss
    },
}


def get_age_group(age: Optional[int]) -> str:
    """Determine age group for RDV adjustments"""
    if age is None:
        return "under_30"  # Default
    if age < 30:
        return "under_30"
    if age <= 50:
        return "30_50"
    return "over_50"


def get_priority_nutrients(goal: str) -> List[str]:
    """
    Get the priority nutrients for a health goal.

    Args:
        goal: Health goal (e.g., "lose_weight", "gain_muscle")

    Returns:
        List of 6-8 nutrient names to track for this goal
    """
    return GOAL_NUTRIENT_PRIORITIES.get(goal, GOAL_NUTRIENT_PRIORITIES["general_wellness"])


def get_personalized_rdvs(
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    custom_calorie_goal: Optional[float] = None
) -> Dict[str, NutrientRDV]:
    """
    Calculate personalized RDVs for a user based on their profile.

    Args:
        goal: Health goal
        gender: "male" or "female" (defaults to female for safety)
        age: User's age
        custom_calorie_goal: Override calorie goal if set by user

    Returns:
        Dict mapping nutrient name to NutrientRDV with personalized values
    """
    # Start with base RDVs by gender
    base_rdvs = BASE_RDVS_MALE if gender == "male" else BASE_RDVS_FEMALE

    # Get adjustments
    goal_adj = GOAL_RDV_ADJUSTMENTS.get(goal, {})
    age_group = get_age_group(age)
    age_adj = AGE_ADJUSTMENTS.get(age_group, {})

    personalized = {}

    for nutrient, (base_amount, unit, display_name) in base_rdvs.items():
        # Apply goal adjustment
        amount = base_amount * goal_adj.get(nutrient, 1.0)

        # Apply age adjustment
        amount = amount * age_adj.get(nutrient, 1.0)

        # Override calories if custom goal set
        if nutrient == "calories" and custom_calorie_goal:
            amount = custom_calorie_goal

        personalized[nutrient] = NutrientRDV(
            name=nutrient,
            amount=round(amount, 1),
            unit=unit,
            display_name=display_name
        )

    return personalized


def get_priority_rdvs(
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    custom_calorie_goal: Optional[float] = None
) -> Dict[str, NutrientRDV]:
    """
    Get personalized RDVs for only the priority nutrients of a goal.

    Args:
        goal: Health goal
        gender: "male" or "female"
        age: User's age
        custom_calorie_goal: Override calorie goal

    Returns:
        Dict with only the priority nutrients and their RDVs
    """
    all_rdvs = get_personalized_rdvs(goal, gender, age, custom_calorie_goal)
    priority_nutrients = get_priority_nutrients(goal)

    return {
        nutrient: all_rdvs[nutrient]
        for nutrient in priority_nutrients
        if nutrient in all_rdvs
    }


def calculate_rdv_percentages(
    consumed: Dict[str, float],
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    custom_calorie_goal: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate what percentage of RDV has been consumed for priority nutrients.

    Args:
        consumed: Dict of nutrient name to amount consumed
        goal: Health goal
        gender: User's gender
        age: User's age
        custom_calorie_goal: Override calorie goal

    Returns:
        Dict mapping nutrient name to percentage of RDV (0-100+)
    """
    rdvs = get_priority_rdvs(goal, gender, age, custom_calorie_goal)

    percentages = {}
    for nutrient, rdv in rdvs.items():
        consumed_amount = consumed.get(nutrient, 0.0)
        if rdv.amount > 0:
            percentages[nutrient] = round((consumed_amount / rdv.amount) * 100, 1)
        else:
            percentages[nutrient] = 0.0

    return percentages


def get_secondary_alerts(
    consumed: Dict[str, float],
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    Check secondary (non-priority) nutrients for critical levels.
    Only alert if >120% (excess) or <30% (severely deficient) at end of day.

    Args:
        consumed: Dict of nutrient name to amount consumed
        goal: Health goal (to know which are secondary)
        gender: User's gender
        age: User's age

    Returns:
        List of alert dicts with nutrient, level, percentage, and message
    """
    all_rdvs = get_personalized_rdvs(goal, gender, age)
    priority_nutrients = set(get_priority_nutrients(goal))

    alerts = []

    for nutrient, rdv in all_rdvs.items():
        # Skip priority nutrients - they're always shown
        if nutrient in priority_nutrients:
            continue

        consumed_amount = consumed.get(nutrient, 0.0)
        if rdv.amount <= 0:
            continue

        percentage = (consumed_amount / rdv.amount) * 100

        # Critical high (>120%)
        if percentage > 120:
            alerts.append({
                "nutrient": nutrient,
                "display_name": rdv.display_name,
                "level": "high",
                "percentage": round(percentage, 1),
                "message": f"{rdv.display_name} is high ({round(percentage)}% of daily limit)"
            })

        # Critical low (<30%) - only meaningful at end of day
        elif percentage < 30:
            alerts.append({
                "nutrient": nutrient,
                "display_name": rdv.display_name,
                "level": "low",
                "percentage": round(percentage, 1),
                "message": f"{rdv.display_name} is very low ({round(percentage)}% of daily need)"
            })

    return alerts


def format_nutrient_summary(
    consumed: Dict[str, float],
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    custom_calorie_goal: Optional[float] = None
) -> str:
    """
    Format a human-readable summary of nutrient intake vs goals.
    Used by chat agent for meal feedback.

    Args:
        consumed: Dict of nutrient name to amount consumed today
        goal: Health goal
        gender: User's gender
        age: User's age
        custom_calorie_goal: Override calorie goal

    Returns:
        Formatted string summary
    """
    rdvs = get_priority_rdvs(goal, gender, age, custom_calorie_goal)
    percentages = calculate_rdv_percentages(consumed, goal, gender, age, custom_calorie_goal)

    lines = []
    for nutrient in get_priority_nutrients(goal):
        if nutrient not in rdvs:
            continue
        rdv = rdvs[nutrient]
        pct = percentages.get(nutrient, 0)
        consumed_amt = consumed.get(nutrient, 0)

        # Status indicator
        if pct >= 90 and pct <= 110:
            status = "ok"
        elif pct > 110:
            status = "high" if nutrient != "sodium" else "limit"
        else:
            status = "low"

        lines.append(
            f"{rdv.display_name}: {consumed_amt:.1f}/{rdv.amount:.0f}{rdv.unit} ({pct:.0f}%)"
        )

    return "\n".join(lines)


# =============================================================================
# GOAL CONTEXT - SINGLE SOURCE OF TRUTH
# One function to get everything the chat agent needs
# =============================================================================

def get_goal_context(
    goal: str,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    custom_calorie_goal: Optional[float] = None
) -> Dict:
    """
    Get complete goal context for chat agent and API.

    This is the SINGLE SOURCE OF TRUTH for goal-driven nutrition.
    Call this once and you have everything you need.

    Args:
        goal: Health goal (e.g., "lose_weight", "pregnancy")
        gender: "male" or "female"
        age: User's age
        custom_calorie_goal: Override calorie goal if set

    Returns:
        Dict with all goal context:
        - goal: str (goal key)
        - goal_display_name: str (e.g., "Weight Loss")
        - goal_emoji: str (e.g., "🏃")
        - primary_nutrient: str (e.g., "protein" or "folate")
        - primary_nutrient_emoji: str (e.g., "💪")
        - priority_nutrients: List[str] (6-8 nutrients)
        - priority_rdvs: Dict[str, NutrientRDV]
        - nutrient_emojis: Dict[str, str] (emoji for each priority nutrient)
    """
    # Get goal metadata
    metadata = GOAL_METADATA.get(goal, GOAL_METADATA["general_wellness"])

    # Get priority nutrients and RDVs
    priority_nutrients = get_priority_nutrients(goal)
    priority_rdvs = get_priority_rdvs(goal, gender, age, custom_calorie_goal)

    # Build nutrient emoji map for priority nutrients
    nutrient_emojis = {
        nutrient: get_nutrient_emoji(nutrient)
        for nutrient in priority_nutrients
    }

    # Primary nutrient info
    primary_nutrient = metadata.get("primary_nutrient", "protein")

    return {
        "goal": goal,
        "goal_display_name": metadata.get("display_name", goal.replace("_", " ").title()),
        "goal_emoji": metadata.get("emoji", "🎯"),
        "goal_description": metadata.get("description", ""),
        "primary_nutrient": primary_nutrient,
        "primary_nutrient_emoji": get_nutrient_emoji(primary_nutrient),
        "priority_nutrients": priority_nutrients,
        "priority_rdvs": priority_rdvs,
        "nutrient_emojis": nutrient_emojis,
    }


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GOAL-DRIVEN NUTRIENT PRIORITY SERVICE")
    print("=" * 60)

    # Test each goal
    for goal in GOAL_NUTRIENT_PRIORITIES:
        nutrients = get_priority_nutrients(goal)
        print(f"\n{goal.upper()} ({len(nutrients)} nutrients):")
        print(f"  {', '.join(nutrients)}")

    # Test personalized RDVs
    print("\n" + "=" * 60)
    print("PERSONALIZED RDVs - Female, 28yo, lose_weight")
    print("=" * 60)

    rdvs = get_priority_rdvs("lose_weight", gender="female", age=28)
    for nutrient, rdv in rdvs.items():
        print(f"  {rdv.display_name}: {rdv.amount} {rdv.unit}")

    # Test percentage calculation
    print("\n" + "=" * 60)
    print("RDV PERCENTAGES - Sample meal logged")
    print("=" * 60)

    consumed = {
        "calories": 1200,
        "protein": 45,
        "fiber": 15,
        "carbohydrates": 150,
        "fat": 40,
        "sodium": 1800,
    }

    percentages = calculate_rdv_percentages(consumed, "lose_weight", "female", 28)
    for nutrient, pct in percentages.items():
        print(f"  {nutrient}: {pct}%")

    print("\nService test complete!")
