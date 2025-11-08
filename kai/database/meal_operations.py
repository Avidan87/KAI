"""
Meal Logging Database Operations

Operations for logging meals, tracking foods, and calculating daily nutrition totals.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import uuid

from .db_setup import get_db

logger = logging.getLogger(__name__)


async def log_meal(
    user_id: str,
    meal_type: str,
    foods: List[Dict[str, Any]],
    meal_date: Optional[str] = None,
    image_url: Optional[str] = None,
    user_description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a meal with detected foods and nutrition data.

    Args:
        user_id: User identifier
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        foods: List of food dicts with nutrition data
        meal_date: Date of meal (ISO format YYYY-MM-DD), defaults to today
        image_url: Optional URL of meal image
        user_description: Optional user description

    Returns:
        dict: Logged meal data with totals

    Example foods format:
        [
            {
                "food_name": "Jollof Rice",
                "food_id": "nigerian-jollof-rice",
                "portion_grams": 250.0,
                "calories": 350.0,
                "protein": 8.5,
                "carbohydrates": 65.0,
                "fat": 7.2,
                "iron": 2.5,
                "calcium": 45.0,
                "vitamin_a": 120.0,
                "zinc": 1.2,
                "confidence": 0.92
            }
        ]
    """
    meal_date = meal_date or date.today().isoformat()
    meal_time = datetime.now().time().isoformat()
    meal_id = f"meal_{uuid.uuid4().hex}"

    async with get_db() as db:
        # Insert meal record
        await db.execute(
            """
            INSERT INTO meals (meal_id, user_id, meal_type, meal_date, meal_time, image_url, user_description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (meal_id, user_id, meal_type, meal_date, meal_time, image_url, user_description, datetime.now().isoformat())
        )

        # Insert foods
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_iron = 0.0
        total_calcium = 0.0
        total_vitamin_a = 0.0
        total_zinc = 0.0

        for food in foods:
            await db.execute(
                """
                INSERT INTO meal_foods (
                    meal_id, food_name, food_id, portion_grams,
                    calories, protein, carbohydrates, fat,
                    iron, calcium, vitamin_a, zinc, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    food["food_name"],
                    food.get("food_id"),
                    food["portion_grams"],
                    food["calories"],
                    food["protein"],
                    food["carbohydrates"],
                    food["fat"],
                    food["iron"],
                    food["calcium"],
                    food["vitamin_a"],
                    food["zinc"],
                    food.get("confidence", 1.0)
                )
            )

            # Accumulate totals
            total_calories += food["calories"]
            total_protein += food["protein"]
            total_carbs += food["carbohydrates"]
            total_fat += food["fat"]
            total_iron += food["iron"]
            total_calcium += food["calcium"]
            total_vitamin_a += food["vitamin_a"]
            total_zinc += food["zinc"]

        # Update daily nutrient totals
        await _update_daily_nutrients(
            db, user_id, meal_date,
            total_calories, total_protein, total_carbs, total_fat,
            total_iron, total_calcium, total_vitamin_a, total_zinc
        )

        await db.commit()

        logger.info(f"✓ Logged meal: {meal_id} for user {user_id} ({len(foods)} foods)")

        return {
            "meal_id": meal_id,
            "user_id": user_id,
            "meal_type": meal_type,
            "meal_date": meal_date,
            "meal_time": meal_time,
            "foods_count": len(foods),
            "totals": {
                "calories": round(total_calories, 1),
                "protein": round(total_protein, 1),
                "carbohydrates": round(total_carbs, 1),
                "fat": round(total_fat, 1),
                "iron": round(total_iron, 2),
                "calcium": round(total_calcium, 1),
                "vitamin_a": round(total_vitamin_a, 1),
                "zinc": round(total_zinc, 2),
            }
        }


async def _update_daily_nutrients(
    db,
    user_id: str,
    date: str,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    iron: float,
    calcium: float,
    vitamin_a: float,
    zinc: float
) -> None:
    """
    Update or create daily nutrient totals.

    Args:
        db: Database connection
        user_id: User identifier
        date: Date (ISO format)
        calories, protein, carbs, fat, iron, calcium, vitamin_a, zinc: Nutrient amounts to add
    """
    # Check if record exists
    cursor = await db.execute(
        "SELECT id FROM daily_nutrients WHERE user_id = ? AND date = ?",
        (user_id, date)
    )
    existing = await cursor.fetchone()

    if existing:
        # Update existing record
        await db.execute(
            """
            UPDATE daily_nutrients SET
                total_calories = total_calories + ?,
                total_protein = total_protein + ?,
                total_carbohydrates = total_carbohydrates + ?,
                total_fat = total_fat + ?,
                total_iron = total_iron + ?,
                total_calcium = total_calcium + ?,
                total_vitamin_a = total_vitamin_a + ?,
                total_zinc = total_zinc + ?,
                meal_count = meal_count + 1,
                updated_at = ?
            WHERE user_id = ? AND date = ?
            """,
            (calories, protein, carbs, fat, iron, calcium, vitamin_a, zinc,
             datetime.now().isoformat(), user_id, date)
        )
    else:
        # Create new record
        await db.execute(
            """
            INSERT INTO daily_nutrients (
                user_id, date,
                total_calories, total_protein, total_carbohydrates, total_fat,
                total_iron, total_calcium, total_vitamin_a, total_zinc,
                meal_count, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (user_id, date, calories, protein, carbs, fat, iron, calcium, vitamin_a, zinc,
             datetime.now().isoformat())
        )


async def get_user_meals(
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get user's recent meals.

    Args:
        user_id: User identifier
        limit: Number of meals to return
        offset: Number of meals to skip

    Returns:
        List[dict]: List of meals with foods
    """
    async with get_db() as db:
        # Get meals
        cursor = await db.execute(
            """
            SELECT meal_id, meal_type, meal_date, meal_time, image_url, user_description, created_at
            FROM meals
            WHERE user_id = ?
            ORDER BY meal_date DESC, meal_time DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )

        meals = []
        async for row in cursor:
            meal = dict(row)

            # Get foods for this meal
            foods_cursor = await db.execute(
                """
                SELECT food_name, food_id, portion_grams,
                       calories, protein, carbohydrates, fat,
                       iron, calcium, vitamin_a, zinc, confidence
                FROM meal_foods
                WHERE meal_id = ?
                """,
                (meal["meal_id"],)
            )

            meal["foods"] = [dict(food_row) async for food_row in foods_cursor]
            meals.append(meal)

        return meals


async def get_meals_by_date(
    user_id: str,
    start_date: str,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get meals for a date range.

    Args:
        user_id: User identifier
        start_date: Start date (ISO format YYYY-MM-DD)
        end_date: End date (ISO format), defaults to start_date

    Returns:
        List[dict]: Meals in date range
    """
    end_date = end_date or start_date

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT meal_id, meal_type, meal_date, meal_time, image_url, user_description
            FROM meals
            WHERE user_id = ? AND meal_date BETWEEN ? AND ?
            ORDER BY meal_date ASC, meal_time ASC
            """,
            (user_id, start_date, end_date)
        )

        meals = []
        async for row in cursor:
            meal = dict(row)

            # Get foods
            foods_cursor = await db.execute(
                """
                SELECT food_name, food_id, portion_grams,
                       calories, protein, carbohydrates, fat,
                       iron, calcium, vitamin_a, zinc, confidence
                FROM meal_foods
                WHERE meal_id = ?
                """,
                (meal["meal_id"],)
            )

            meal["foods"] = [dict(food_row) async for food_row in foods_cursor]
            meals.append(meal)

        return meals


async def get_daily_nutrition_totals(
    user_id: str,
    date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get daily nutrition totals for a specific date.

    Args:
        user_id: User identifier
        date: Date (ISO format), defaults to today

    Returns:
        dict: Daily nutrition totals or None if no meals logged
    """
    date = date or datetime.today().date().isoformat()

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT *
            FROM daily_nutrients
            WHERE user_id = ? AND date = ?
            """,
            (user_id, date)
        )

        row = await cursor.fetchone()

        if not row:
            return None

        return dict(row)


async def get_nutrition_history(
    user_id: str,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get nutrition history for the past N days.

    Args:
        user_id: User identifier
        days: Number of days to retrieve

    Returns:
        List[dict]: Daily nutrition totals for each day
    """
    from datetime import timedelta

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days - 1)

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT *
            FROM daily_nutrients
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat())
        )

        history = [dict(row) async for row in cursor]
        return history


async def delete_meal(meal_id: str) -> bool:
    """
    Delete a meal and recalculate daily totals.

    Args:
        meal_id: Meal identifier

    Returns:
        bool: True if deleted, False if not found
    """
    async with get_db() as db:
        # Get meal info before deleting
        cursor = await db.execute(
            "SELECT user_id, meal_date FROM meals WHERE meal_id = ?",
            (meal_id,)
        )
        meal = await cursor.fetchone()

        if not meal:
            return False

        user_id = meal["user_id"]
        meal_date = meal["meal_date"]

        # Get meal food totals
        cursor = await db.execute(
            """
            SELECT
                SUM(calories) as calories,
                SUM(protein) as protein,
                SUM(carbohydrates) as carbs,
                SUM(fat) as fat,
                SUM(iron) as iron,
                SUM(calcium) as calcium,
                SUM(vitamin_a) as vitamin_a,
                SUM(zinc) as zinc
            FROM meal_foods
            WHERE meal_id = ?
            """,
            (meal_id,)
        )
        totals = await cursor.fetchone()

        # Delete meal (foods will cascade)
        await db.execute("DELETE FROM meals WHERE meal_id = ?", (meal_id,))

        # Update daily totals (subtract this meal)
        if totals:
            await db.execute(
                """
                UPDATE daily_nutrients SET
                    total_calories = MAX(0, total_calories - ?),
                    total_protein = MAX(0, total_protein - ?),
                    total_carbohydrates = MAX(0, total_carbohydrates - ?),
                    total_fat = MAX(0, total_fat - ?),
                    total_iron = MAX(0, total_iron - ?),
                    total_calcium = MAX(0, total_calcium - ?),
                    total_vitamin_a = MAX(0, total_vitamin_a - ?),
                    total_zinc = MAX(0, total_zinc - ?),
                    meal_count = MAX(0, meal_count - 1),
                    updated_at = ?
                WHERE user_id = ? AND date = ?
                """,
                (totals["calories"] or 0, totals["protein"] or 0, totals["carbs"] or 0, totals["fat"] or 0,
                 totals["iron"] or 0, totals["calcium"] or 0, totals["vitamin_a"] or 0, totals["zinc"] or 0,
                 datetime.now().isoformat(), user_id, meal_date)
            )

        await db.commit()

        logger.info(f"✓ Deleted meal: {meal_id}")
        return True


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from .db_setup import initialize_database
    from .user_operations import create_user
    import uuid

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_meal_operations():
        """Test meal logging operations"""
        print("\n" + "="*60)
        print("Testing Meal Operations")
        print("="*60 + "\n")

        # Initialize database
        await initialize_database()

        # Create test user
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        await create_user(test_user_id, name="Test User", gender="female", age=28)

        # Log a meal
        foods = [
            {
                "food_name": "Jollof Rice",
                "food_id": "nigerian-jollof-rice",
                "portion_grams": 250.0,
                "calories": 350.0,
                "protein": 8.5,
                "carbohydrates": 65.0,
                "fat": 7.2,
                "iron": 2.5,
                "calcium": 45.0,
                "vitamin_a": 120.0,
                "zinc": 1.2,
                "confidence": 0.92
            },
            {
                "food_name": "Fried Plantain",
                "food_id": "nigerian-fried-plantain",
                "portion_grams": 100.0,
                "calories": 116.0,
                "protein": 1.2,
                "carbohydrates": 28.0,
                "fat": 0.4,
                "iron": 0.6,
                "calcium": 3.0,
                "vitamin_a": 1127.0,
                "zinc": 0.1,
                "confidence": 0.95
            }
        ]

        meal = await log_meal(
            user_id=test_user_id,
            meal_type="lunch",
            foods=foods,
            user_description="Delicious lunch!"
        )
        print(f"\nLogged meal: {meal['meal_id']}")
        print(f"  Foods: {meal['foods_count']}")
        print(f"  Total calories: {meal['totals']['calories']}")
        print(f"  Total protein: {meal['totals']['protein']}g")
        print(f"  Total iron: {meal['totals']['iron']}mg")

        # Get daily totals
        totals = await get_daily_nutrition_totals(test_user_id)
        print(f"\nDaily totals:")
        print(f"  Calories: {totals['total_calories']:.1f}")
        print(f"  Protein: {totals['total_protein']:.1f}g")
        print(f"  Iron: {totals['total_iron']:.2f}mg")
        print(f"  Meals logged: {totals['meal_count']}")

        # Get user meals
        meals = await get_user_meals(test_user_id, limit=10)
        print(f"\nRetrieved {len(meals)} meals")

        # Get nutrition history
        history = await get_nutrition_history(test_user_id, days=7)
        print(f"\n7-day nutrition history: {len(history)} days with data")

        print("\n✓ Meal operations test complete!\n")

    asyncio.run(test_meal_operations())
