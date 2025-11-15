"""
User Statistics Operations

Functions for managing user nutrition statistics, food frequency tracking,
and recommendation responses for the dynamic coaching system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .db_setup import get_db

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
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM user_nutrition_stats WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return dict(row)


async def initialize_user_stats(user_id: str) -> Dict:
    """
    Initialize stats entry for new user.

    Args:
        user_id: User ID

    Returns:
        Dict with initialized stats
    """
    async with get_db() as db:
        # Check if already exists
        existing = await get_user_stats(user_id)
        if existing:
            return existing

        # Create new stats entry
        await db.execute("""
            INSERT INTO user_nutrition_stats (user_id)
            VALUES (?)
        """, (user_id,))
        await db.commit()

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

    # Build update query dynamically
    updates = []
    params = []

    if total_meals_logged is not None:
        updates.append("total_meals_logged = ?")
        params.append(total_meals_logged)

    if account_age_days is not None:
        updates.append("account_age_days = ?")
        params.append(account_age_days)

    if learning_phase_complete is not None:
        updates.append("learning_phase_complete = ?")
        params.append(1 if learning_phase_complete else 0)

    if current_logging_streak is not None:
        updates.append("current_logging_streak = ?")
        params.append(current_logging_streak)

    if longest_logging_streak is not None:
        updates.append("longest_logging_streak = ?")
        params.append(longest_logging_streak)

    if last_logged_date is not None:
        updates.append("last_logged_date = ?")
        params.append(last_logged_date)

    # Week 1 averages
    if week1_averages:
        for nutrient, value in week1_averages.items():
            updates.append(f"week1_avg_{nutrient} = ?")
            params.append(value)

    # Week 2 averages
    if week2_averages:
        for nutrient, value in week2_averages.items():
            updates.append(f"week2_avg_{nutrient} = ?")
            params.append(value)

    # Trends
    if trends:
        for nutrient, trend in trends.items():
            updates.append(f"{nutrient}_trend = ?")
            params.append(trend)

    # Always update last_calculated_at
    updates.append("last_calculated_at = CURRENT_TIMESTAMP")

    if not updates:
        return await get_user_stats(user_id)

    params.append(user_id)  # For WHERE clause

    async with get_db() as db:
        query = f"""
            UPDATE user_nutrition_stats
            SET {', '.join(updates)}
            WHERE user_id = ?
        """
        await db.execute(query, params)
        await db.commit()

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
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT *
            FROM user_food_frequency
            WHERE user_id = ?
            ORDER BY count_7d DESC
            LIMIT ?
        """, (user_id, top_n))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


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
    vitamin_a: float = 0,
    zinc: float = 0,
) -> None:
    """
    Update food frequency for a food item.

    Args:
        user_id: User ID
        food_name: Name of the food
        food_category: Category (e.g., 'rice_dishes', 'soups')
        calories: Calories in this serving
        protein: Protein content in this serving
        carbs: Carbohydrates in this serving
        fat: Fat content in this serving
        iron: Iron content in this serving
        calcium: Calcium content in this serving
        vitamin_a: Vitamin A content in this serving
        zinc: Zinc content in this serving
    """
    today = datetime.now().date().isoformat()

    async with get_db() as db:
        # Check if food exists for user
        cursor = await db.execute("""
            SELECT count_7d, count_total,
                   avg_calories_per_serving, avg_protein_per_serving, avg_carbs_per_serving,
                   avg_fat_per_serving, avg_iron_per_serving, avg_calcium_per_serving,
                   avg_vitamin_a_per_serving, avg_zinc_per_serving
            FROM user_food_frequency
            WHERE user_id = ? AND food_name = ?
        """, (user_id, food_name))

        row = await cursor.fetchone()

        if row:
            # Update existing
            count_7d = row[0] + 1
            count_total = row[1] + 1

            # Update running averages for ALL nutrients
            avg_calories_new = (row[2] * row[1] + calories) / count_total
            avg_protein_new = (row[3] * row[1] + protein) / count_total
            avg_carbs_new = (row[4] * row[1] + carbs) / count_total
            avg_fat_new = (row[5] * row[1] + fat) / count_total
            avg_iron_new = (row[6] * row[1] + iron) / count_total
            avg_calcium_new = (row[7] * row[1] + calcium) / count_total
            avg_vitamin_a_new = (row[8] * row[1] + vitamin_a) / count_total
            avg_zinc_new = (row[9] * row[1] + zinc) / count_total

            await db.execute("""
                UPDATE user_food_frequency
                SET count_7d = count_7d + 1,
                    count_total = count_total + 1,
                    last_eaten_date = ?,
                    avg_calories_per_serving = ?,
                    avg_protein_per_serving = ?,
                    avg_carbs_per_serving = ?,
                    avg_fat_per_serving = ?,
                    avg_iron_per_serving = ?,
                    avg_calcium_per_serving = ?,
                    avg_vitamin_a_per_serving = ?,
                    avg_zinc_per_serving = ?
                WHERE user_id = ? AND food_name = ?
            """, (today, avg_calories_new, avg_protein_new, avg_carbs_new, avg_fat_new,
                  avg_iron_new, avg_calcium_new, avg_vitamin_a_new, avg_zinc_new,
                  user_id, food_name))

        else:
            # Insert new
            await db.execute("""
                INSERT INTO user_food_frequency (
                    user_id, food_name, count_7d, count_total, last_eaten_date,
                    avg_calories_per_serving, avg_protein_per_serving, avg_carbs_per_serving,
                    avg_fat_per_serving, avg_iron_per_serving, avg_calcium_per_serving,
                    avg_vitamin_a_per_serving, avg_zinc_per_serving,
                    food_category
                )
                VALUES (?, ?, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, food_name, today, calories, protein, carbs, fat, iron,
                  calcium, vitamin_a, zinc, food_category))

        await db.commit()


async def reset_weekly_food_frequency(user_id: str) -> None:
    """
    Reset count_7d for all foods (called weekly).

    Args:
        user_id: User ID
    """
    async with get_db() as db:
        await db.execute("""
            UPDATE user_food_frequency
            SET count_7d = 0
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

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
        target_nutrient: Nutrient being targeted (iron, protein, etc.)
    """
    today = datetime.now().date().isoformat()

    async with get_db() as db:
        await db.execute("""
            INSERT INTO user_recommendation_responses (
                user_id, recommended_food, recommendation_date,
                recommendation_tier, target_nutrient
            )
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, recommended_food, today, recommendation_tier, target_nutrient))
        await db.commit()

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

    async with get_db() as db:
        # Find most recent recommendation for this food
        cursor = await db.execute("""
            SELECT id, recommendation_date
            FROM user_recommendation_responses
            WHERE user_id = ? AND recommended_food = ? AND followed = 0
            ORDER BY recommendation_date DESC
            LIMIT 1
        """, (user_id, recommended_food))

        row = await cursor.fetchone()

        if row:
            rec_id = row[0]
            rec_date = datetime.fromisoformat(row[1])
            today_date = datetime.fromisoformat(today)
            days_to_follow = (today_date - rec_date).days

            await db.execute("""
                UPDATE user_recommendation_responses
                SET followed = 1,
                    followed_date = ?,
                    days_to_follow = ?
                WHERE id = ?
            """, (today, days_to_follow, rec_id))

            await db.commit()
            logger.info(f"✓ User {user_id} followed recommendation: {recommended_food} (after {days_to_follow} days)")


async def get_recommendation_stats(user_id: str) -> Dict:
    """
    Get recommendation effectiveness stats for user.

    Args:
        user_id: User ID

    Returns:
        Dict with stats like:
        {
            'total_recommendations': 10,
            'total_followed': 3,
            'follow_through_rate': 0.3,
            'avg_days_to_follow': 2.5,
            'by_tier': {...}
        }
    """
    async with get_db() as db:
        # Total stats
        cursor = await db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN followed = 1 THEN 1 ELSE 0 END) as followed,
                AVG(CASE WHEN followed = 1 THEN days_to_follow ELSE NULL END) as avg_days
            FROM user_recommendation_responses
            WHERE user_id = ?
        """, (user_id,))

        row = await cursor.fetchone()
        total = row[0] or 0
        followed = row[1] or 0
        avg_days = row[2] or 0

        # By tier stats
        cursor = await db.execute("""
            SELECT
                recommendation_tier,
                COUNT(*) as total,
                SUM(CASE WHEN followed = 1 THEN 1 ELSE 0 END) as followed
            FROM user_recommendation_responses
            WHERE user_id = ?
            GROUP BY recommendation_tier
        """, (user_id,))

        by_tier = {}
        rows = await cursor.fetchall()
        for row in rows:
            tier = row[0]
            tier_total = row[1]
            tier_followed = row[2]
            by_tier[tier] = {
                "total": tier_total,
                "followed": tier_followed,
                "rate": tier_followed / tier_total if tier_total > 0 else 0
            }

        return {
            "total_recommendations": total,
            "total_followed": followed,
            "follow_through_rate": followed / total if total > 0 else 0,
            "avg_days_to_follow": avg_days,
            "by_tier": by_tier
        }
