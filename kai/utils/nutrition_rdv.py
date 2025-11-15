"""
Multi-Nutrient RDV (Recommended Daily Value) Calculator

Calculates personalized RDV for all 8 nutrients based on:
- Gender (male/female)
- Age (19-50, 51+)
- Activity level (sedentary, light, moderate, active, very_active)

Note: Pregnancy, lactation, and anemia adjustments are NOT included in this version.
These will be added in future iterations.
"""

from typing import Dict


# =============================================================================
# Base RDV Values (Adult 19-50 years)
# =============================================================================

BASE_RDV = {
    # Male base values
    "male": {
        "calories": 2500,       # kcal
        "protein": 56,          # g
        "carbs": 300,           # g
        "fat": 70,              # g
        "iron": 8,              # mg
        "calcium": 1000,        # mg
        "vitamin_a": 900,       # mcg RAE
        "zinc": 11,             # mg
    },
    # Female base values
    "female": {
        "calories": 2000,       # kcal
        "protein": 46,          # g
        "carbs": 225,           # g
        "fat": 60,              # g
        "iron": 18,             # mg (higher due to menstruation)
        "calcium": 1000,        # mg
        "vitamin_a": 700,       # mcg RAE
        "zinc": 8,              # mg
    },
}


# =============================================================================
# Age Adjustment Factors
# =============================================================================

AGE_ADJUSTMENTS = {
    # Age 51+ adjustments (multiply by base)
    "51+": {
        "male": {
            "calories": 0.9,        # 10% reduction for lower metabolism
            "iron": 1.0,            # Same (no menstruation factor)
            "calcium": 1.2,         # Increased for bone health
            "vitamin_a": 1.0,       # Same
        },
        "female": {
            "calories": 0.9,        # 10% reduction
            "iron": 0.44,           # Reduced to 8mg (post-menopause)
            "calcium": 1.2,         # Increased for bone health
            "vitamin_a": 1.0,       # Same
        },
    }
}


# =============================================================================
# Activity Level Multipliers
# =============================================================================

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.0,       # Base (little to no exercise)
    "light": 1.1,           # Light exercise 1-3 days/week
    "moderate": 1.25,       # Moderate exercise 3-5 days/week
    "active": 1.4,          # Hard exercise 6-7 days/week
    "very_active": 1.6,     # Very hard exercise, physical job
}


# =============================================================================
# RDV Calculation Function
# =============================================================================

def calculate_user_rdv(user_profile: Dict) -> Dict[str, float]:
    """
    Calculate personalized RDV for all 8 nutrients.

    Args:
        user_profile: Dict with user info:
            {
                "gender": "male" | "female",
                "age": 25,
                "activity_level": "sedentary" | "light" | "moderate" | "active" | "very_active"
            }

    Returns:
        Dict with personalized RDV values:
        {
            "calories": 2750.0,
            "protein": 61.6,
            "carbs": 330.0,
            "fat": 77.0,
            "iron": 8.8,
            "calcium": 1100.0,
            "vitamin_a": 990.0,
            "zinc": 12.1
        }
    """
    gender = user_profile.get("gender", "female")
    age = user_profile.get("age", 25)
    activity_level = user_profile.get("activity_level", "moderate")

    # Start with base RDV for gender
    rdv = BASE_RDV.get(gender, BASE_RDV["female"]).copy()

    # Apply age adjustments if 51+
    if age >= 51:
        age_adj = AGE_ADJUSTMENTS["51+"][gender]
        for nutrient, multiplier in age_adj.items():
            if nutrient in rdv:
                rdv[nutrient] *= multiplier

    # Apply activity level multiplier
    # (Applies to energy nutrients: calories, protein, carbs, fat)
    activity_multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.25)

    # Energy nutrients scale with activity
    energy_nutrients = ["calories", "protein", "carbs", "fat"]
    for nutrient in energy_nutrients:
        rdv[nutrient] *= activity_multiplier

    # Micronutrients scale SLIGHTLY with activity (10% max boost for very active)
    # This accounts for increased nutrient needs during intense exercise
    micro_multiplier = 1.0
    if activity_level == "active":
        micro_multiplier = 1.05
    elif activity_level == "very_active":
        micro_multiplier = 1.1

    micronutrients = ["iron", "calcium", "vitamin_a", "zinc"]
    for nutrient in micronutrients:
        rdv[nutrient] *= micro_multiplier

    # Round all values for readability
    for nutrient in rdv:
        rdv[nutrient] = round(rdv[nutrient], 1)

    return rdv


def get_nutrient_gap_priority(
    current_intake: Dict[str, float],
    user_rdv: Dict[str, float]
) -> Dict[str, Dict]:
    """
    Identify which nutrients have the biggest gaps.

    Args:
        current_intake: User's current average intake (from week1_averages)
        user_rdv: User's personalized RDV values

    Returns:
        Dict of nutrients with their gaps, sorted by severity:
        {
            "iron": {
                "current": 8.5,
                "target": 18.0,
                "percent_met": 47.2,
                "gap": 9.5,
                "priority": "high"
            },
            ...
        }
    """
    gaps = {}

    for nutrient, target in user_rdv.items():
        current = current_intake.get(nutrient, 0)

        # Calculate percent of RDV met
        percent_met = (current / target * 100) if target > 0 else 100

        # Calculate absolute gap
        gap = max(0, target - current)

        # Determine priority level
        if percent_met < 50:
            priority = "high"
        elif percent_met < 75:
            priority = "medium"
        elif percent_met < 90:
            priority = "low"
        else:
            priority = "met"

        gaps[nutrient] = {
            "current": round(current, 1),
            "target": round(target, 1),
            "percent_met": round(percent_met, 1),
            "gap": round(gap, 1),
            "priority": priority
        }

    # Sort by gap size (largest first)
    sorted_gaps = dict(sorted(
        gaps.items(),
        key=lambda x: x[1]["gap"],
        reverse=True
    ))

    return sorted_gaps


def get_primary_nutritional_gap(gaps: Dict[str, Dict]) -> str:
    """
    Get the single most important nutrient to focus on.

    Args:
        gaps: Output from get_nutrient_gap_priority()

    Returns:
        Name of primary nutrient to target (e.g., "iron")
    """
    # Filter to only high and medium priority gaps
    priority_gaps = {
        nutrient: data
        for nutrient, data in gaps.items()
        if data["priority"] in ["high", "medium"]
    }

    if not priority_gaps:
        # All nutrients met - focus on protein (general health)
        return "protein"

    # Return nutrient with largest gap
    primary = max(priority_gaps.items(), key=lambda x: x[1]["gap"])
    return primary[0]


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Multi-Nutrient RDV Calculator - Test Suite")
    print("="*60 + "\n")

    # Test Case 1: Young active male
    print("Test 1: 25-year-old active male")
    print("-" * 40)
    profile1 = {
        "gender": "male",
        "age": 25,
        "activity_level": "active"
    }
    rdv1 = calculate_user_rdv(profile1)
    print(f"Gender: {profile1['gender']}, Age: {profile1['age']}, Activity: {profile1['activity_level']}")
    print("\nPersonalized RDV:")
    for nutrient, value in rdv1.items():
        print(f"  {nutrient}: {value}")

    # Test Case 2: Older sedentary female
    print("\n\nTest 2: 55-year-old sedentary female")
    print("-" * 40)
    profile2 = {
        "gender": "female",
        "age": 55,
        "activity_level": "sedentary"
    }
    rdv2 = calculate_user_rdv(profile2)
    print(f"Gender: {profile2['gender']}, Age: {profile2['age']}, Activity: {profile2['activity_level']}")
    print("\nPersonalized RDV:")
    for nutrient, value in rdv2.items():
        print(f"  {nutrient}: {value}")
    print("\nNote: Iron reduced (post-menopause), Calcium increased (bone health)")

    # Test Case 3: Gap analysis
    print("\n\nTest 3: Gap Analysis for Active Male")
    print("-" * 40)
    current_intake = {
        "calories": 2200,
        "protein": 55,
        "carbs": 280,
        "fat": 65,
        "iron": 6.5,      # Low
        "calcium": 650,   # Low
        "vitamin_a": 500, # Low
        "zinc": 9.5,
    }
    gaps = get_nutrient_gap_priority(current_intake, rdv1)
    print("\nNutritional Gaps (sorted by severity):\n")
    for nutrient, data in gaps.items():
        print(f"{nutrient}:")
        print(f"  Current: {data['current']} | Target: {data['target']} | {data['percent_met']}% met")
        print(f"  Gap: {data['gap']} | Priority: {data['priority']}")
        print()

    primary_gap = get_primary_nutritional_gap(gaps)
    print(f">> PRIMARY FOCUS: {primary_gap.upper()}")
    print(f"   This is the nutrient with the largest gap that needs attention.\n")

    print("="*60)
    print("All tests complete!")
    print("="*60 + "\n")
