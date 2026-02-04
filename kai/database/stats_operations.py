"""
User Statistics Operations - Supabase

Functions for managing user nutrition statistics, food frequency tracking,
and recommendation responses for the dynamic coaching system.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from .db_setup import get_supabase

logger = logging.getLogger(__name__)


# =============================================================================
# User Nutrition Stats Operations
# =============================================================================

async def get_user_stats(user_id: str) -> Optional[Dict]:
    """
    Get pre-computed user nutrition statistics.

    Args:
        user_id: User ID

    Returns:
        Dict with user stats or None if not found
    """
    client = get_supabase()

    result = client.table("user_nutrition_stats").select("*").eq("user_id", user_id).execute()

    if not result.data:
        return None

    return result.data[0]


async def initialize_user_stats(user_id: str) -> Dict:
    """
    Initialize stats entry for new user.

    Args:
        user_id: User ID

    Returns:
        Dict with initialized stats
    """
    existing = await get_user_stats(user_id)
    if existing:
        return existing

    client = get_supabase()

    client.table("user_nutrition_stats").insert({
        "user_id": user_id,
    }).execute()

    logger.info(f"✓ Initialized stats for user {user_id}")
    return await get_user_stats(user_id)


async def update_user_stats(
    user_id: str,
    total_meals_logged: Optional[int] = None,
    account_age_days: Optional[int] = None,
    learning_phase_complete: Optional[bool] = None,
    current_logging_streak: Optional[int] = None,
    longest_logging_streak: Optional[int] = None,
    last_logged_date: Optional[str] = None,
    week1_averages: Optional[Dict[str, float]] = None,
    week2_averages: Optional[Dict[str, float]] = None,
    trends: Optional[Dict[str, str]] = None,
) -> Dict:
    """
    Update user nutrition statistics.

    Args:
        user_id: User ID
        total_meals_logged: Total meals logged count
        account_age_days: Account age in days
        learning_phase_complete: Whether learning phase is complete
        current_logging_streak: Current consecutive days logged
        longest_logging_streak: Longest streak ever
        last_logged_date: Last date user logged a meal
        week1_averages: Dict of Week 1 nutrient averages
        week2_averages: Dict of Week 2 nutrient averages
        trends: Dict of nutrient trends

    Returns:
        Updated user stats dict
    """
    # Ensure user stats exist
    await initialize_user_stats(user_id)

    client = get_supabase()

    updates = {"last_calculated_at": datetime.now().isoformat()}

    if total_meals_logged is not None:
        updates["total_meals_logged"] = total_meals_logged
    if account_age_days is not None:
        updates["account_age_days"] = account_age_days
    if learning_phase_complete is not None:
        updates["learning_phase_complete"] = learning_phase_complete
    if current_logging_streak is not None:
        updates["current_logging_streak"] = current_logging_streak
    if longest_logging_streak is not None:
        updates["longest_logging_streak"] = longest_logging_streak
    if last_logged_date is not None:
        updates["last_logged_date"] = last_logged_date

    # Week 1 averages
    if week1_averages:
        for nutrient, value in week1_averages.items():
            updates[f"week1_avg_{nutrient}"] = value

    # Week 2 averages
    if week2_averages:
        for nutrient, value in week2_averages.items():
            updates[f"week2_avg_{nutrient}"] = value

    # Trends
    if trends:
        for nutrient, trend in trends.items():
            updates[f"{nutrient}_trend"] = trend

    client.table("user_nutrition_stats").update(updates).eq("user_id", user_id).execute()

    return await get_user_stats(user_id)


# =============================================================================
# Food Frequency Operations
# =============================================================================

async def get_user_food_frequency(user_id: str, top_n: int = 10) -> List[Dict]:
    """
    Get user's most frequently eaten foods.

    Args:
        user_id: User ID
        top_n: Number of top foods to return

    Returns:
        List of food frequency dicts, ordered by count_7d DESC
    """
    client = get_supabase()

    result = client.table("user_food_frequency").select("*").eq(
        "user_id", user_id
    ).order("count_7d", desc=True).limit(top_n).execute()

    return result.data


async def update_food_frequency(
    user_id: str,
    food_name: str,
    food_category: Optional[str] = None,
    calories: float = 0,
    protein: float = 0,
    carbs: float = 0,
    fat: float = 0,
    iron: float = 0,
    calcium: float = 0,
    potassium: float = 0,
    zinc: float = 0,
) -> None:
    """
    Update food frequency for a food item.

    Args:
        user_id: User ID
        food_name: Name of the food
        food_category: Category
        calories, protein, carbs, fat, iron, calcium, potassium, zinc: nutrient values
    """
    today = datetime.now().date().isoformat()
    client = get_supabase()

    # Check if food exists for user
    existing = client.table("user_food_frequency").select("*").eq(
        "user_id", user_id
    ).eq("food_name", food_name).execute()

    if existing.data:
        row = existing.data[0]
        count_total = (row["count_total"] or 0) + 1

        # Update running averages
        old_total = row["count_total"] or 1
        avg_calories = ((row.get("avg_calories_per_serving", 0) or 0) * old_total + calories) / count_total
        avg_protein = ((row.get("avg_protein_per_serving", 0) or 0) * old_total + protein) / count_total
        avg_carbs = ((row.get("avg_carbs_per_serving", 0) or 0) * old_total + carbs) / count_total
        avg_fat = ((row.get("avg_fat_per_serving", 0) or 0) * old_total + fat) / count_total
        avg_iron = ((row.get("avg_iron_per_serving", 0) or 0) * old_total + iron) / count_total
        avg_calcium = ((row.get("avg_calcium_per_serving", 0) or 0) * old_total + calcium) / count_total
        avg_potassium = ((row.get("avg_potassium_per_serving", 0) or 0) * old_total + potassium) / count_total
        avg_zinc = ((row.get("avg_zinc_per_serving", 0) or 0) * old_total + zinc) / count_total

        client.table("user_food_frequency").update({
            "count_7d": (row["count_7d"] or 0) + 1,
            "count_total": count_total,
            "last_eaten_date": today,
            "avg_calories_per_serving": avg_calories,
            "avg_protein_per_serving": avg_protein,
            "avg_carbs_per_serving": avg_carbs,
            "avg_fat_per_serving": avg_fat,
            "avg_iron_per_serving": avg_iron,
            "avg_calcium_per_serving": avg_calcium,
            "avg_potassium_per_serving": avg_potassium,
            "avg_zinc_per_serving": avg_zinc,
        }).eq("user_id", user_id).eq("food_name", food_name).execute()

    else:
        # Insert new
        client.table("user_food_frequency").insert({
            "user_id": user_id,
            "food_name": food_name,
            "count_7d": 1,
            "count_total": 1,
            "last_eaten_date": today,
            "avg_calories_per_serving": calories,
            "avg_protein_per_serving": protein,
            "avg_carbs_per_serving": carbs,
            "avg_fat_per_serving": fat,
            "avg_iron_per_serving": iron,
            "avg_calcium_per_serving": calcium,
            "avg_potassium_per_serving": potassium,
            "avg_zinc_per_serving": zinc,
            "food_category": food_category,
        }).execute()


async def reset_weekly_food_frequency(user_id: str) -> None:
    """
    Reset count_7d for all foods (called weekly).

    Args:
        user_id: User ID
    """
    client = get_supabase()

    client.table("user_food_frequency").update({
        "count_7d": 0,
    }).eq("user_id", user_id).execute()

    logger.info(f"✓ Reset weekly food frequency for user {user_id}")


# =============================================================================
# Recommendation Response Operations
# =============================================================================

async def log_recommendation(
    user_id: str,
    recommended_food: str,
    recommendation_tier: str,
    target_nutrient: str,
) -> None:
    """
    Log a recommendation given to user.

    Args:
        user_id: User ID
        recommended_food: Name of recommended food
        recommendation_tier: Tier (quick_win, easy_upgrade, full_dish, budget_friendly)
        target_nutrient: Nutrient being targeted
    """
    today = datetime.now().date().isoformat()
    client = get_supabase()

    client.table("user_recommendation_responses").insert({
        "user_id": user_id,
        "recommended_food": recommended_food,
        "recommendation_date": today,
        "recommendation_tier": recommendation_tier,
        "target_nutrient": target_nutrient,
    }).execute()

    logger.info(f"✓ Logged recommendation: {recommended_food} ({recommendation_tier}) for {user_id}")


async def mark_recommendation_followed(
    user_id: str,
    recommended_food: str,
) -> None:
    """
    Mark a recommendation as followed (user ate the recommended food).

    Args:
        user_id: User ID
        recommended_food: Name of recommended food that was eaten
    """
    today = datetime.now().date().isoformat()
    client = get_supabase()

    # Find most recent unfollowed recommendation for this food
    result = client.table("user_recommendation_responses").select(
        "id, recommendation_date"
    ).eq("user_id", user_id).eq(
        "recommended_food", recommended_food
    ).eq("followed", False).order(
        "recommendation_date", desc=True
    ).limit(1).execute()

    if result.data:
        rec = result.data[0]
        rec_date = datetime.fromisoformat(rec["recommendation_date"])
        today_date = datetime.fromisoformat(today)
        days_to_follow = (today_date - rec_date).days

        client.table("user_recommendation_responses").update({
            "followed": True,
            "followed_date": today,
            "days_to_follow": days_to_follow,
        }).eq("id", rec["id"]).execute()

        logger.info(f"✓ User {user_id} followed recommendation: {recommended_food} (after {days_to_follow} days)")


async def get_recommendation_stats(user_id: str) -> Dict:
    """
    Get recommendation effectiveness stats for user.

    Args:
        user_id: User ID

    Returns:
        Dict with stats
    """
    client = get_supabase()

    # Get all recommendations
    result = client.table("user_recommendation_responses").select("*").eq(
        "user_id", user_id
    ).execute()

    all_recs = result.data
    total = len(all_recs)
    followed = sum(1 for r in all_recs if r.get("followed"))
    followed_recs = [r for r in all_recs if r.get("followed") and r.get("days_to_follow") is not None]
    avg_days = sum(r["days_to_follow"] for r in followed_recs) / len(followed_recs) if followed_recs else 0

    # By tier
    by_tier = {}
    for rec in all_recs:
        tier = rec.get("recommendation_tier", "unknown")
        if tier not in by_tier:
            by_tier[tier] = {"total": 0, "followed": 0}
        by_tier[tier]["total"] += 1
        if rec.get("followed"):
            by_tier[tier]["followed"] += 1

    for tier_data in by_tier.values():
        tier_data["rate"] = tier_data["followed"] / tier_data["total"] if tier_data["total"] > 0 else 0

    return {
        "total_recommendations": total,
        "total_followed": followed,
        "follow_through_rate": followed / total if total > 0 else 0,
        "avg_days_to_follow": avg_days,
        "by_tier": by_tier,
    }
