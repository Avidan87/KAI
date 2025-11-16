"""
Create Test User with Meal History for Coaching Testing
"""
import asyncio
from datetime import datetime, timedelta
from kai.database import (
    create_user,
    log_meal,
)
from kai.jobs import calculate_and_update_user_stats

async def create_test_user():
    """Create test user with 10 days of meal history."""
    user_id = "coaching_test_user_001"

    print(f"\n{'='*60}")
    print(f"Creating Test User with Meal History")
    print(f"{'='*60}\n")

    # Step 1: Create user
    try:
        user = await create_user(
            user_id=user_id,
            email="coaching_test@kai.com",
            name="Coaching Test User",
            gender="female",
            age=28
        )
        print(f"✓ Created user: {user['name']} (ID: {user_id})")
    except Exception as e:
        print(f"User may already exist: {e}")

    # Step 2: Log meals for past 10 days
    print(f"\n✓ Logging 10 days of meals...")

    for days_ago in range(9, -1, -1):  # 10 days ago to today
        meal_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()

        # Breakfast
        await log_meal(
            user_id=user_id,
            meal_type="breakfast",
            foods=[
                {
                    "food_name": "Bread and Egg",
                    "food_id": "nigerian-bread-egg",
                    "portion_grams": 150,
                    "calories": 350,
                    "protein": 15,
                    "carbohydrates": 40,
                    "fat": 10,
                    "iron": 2.5,
                    "calcium": 80,
                    "vitamin_a": 200,
                    "zinc": 1.5,
                    "confidence": 0.9
                }
            ],
            image_url=None
        )

        # Lunch
        await log_meal(
            user_id=user_id,
            meal_type="lunch",
            foods=[
                {
                    "food_name": "Jollof Rice",
                    "food_id": "nigerian-jollof",
                    "portion_grams": 300,
                    "calories": 450,
                    "protein": 12,
                    "carbohydrates": 75,
                    "fat": 12,
                    "iron": 3,
                    "calcium": 60,
                    "vitamin_a": 150,
                    "zinc": 2,
                    "confidence": 0.95
                }
            ],
            image_url=None
        )

        # Dinner
        await log_meal(
            user_id=user_id,
            meal_type="dinner",
            foods=[
                {
                    "food_name": "Egusi Soup and Eba",
                    "food_id": "nigerian-egusi",
                    "portion_grams": 400,
                    "calories": 600,
                    "protein": 20,
                    "carbohydrates": 50,
                    "fat": 25,
                    "iron": 5,
                    "calcium": 120,
                    "vitamin_a": 300,
                    "zinc": 3,
                    "confidence": 0.92
                }
            ],
            image_url=None
        )

        print(f"  Day {10-days_ago}: {meal_date} - 3 meals logged")

    # Step 3: Calculate stats
    print(f"\n✓ Calculating user stats...")
    stats = await calculate_and_update_user_stats(user_id)

    print(f"\n{'='*60}")
    print(f"Test User Created Successfully!")
    print(f"{'='*60}")
    print(f"\nUser ID: {user_id}")
    print(f"Total Meals: {stats['total_meals_logged']}")
    print(f"Learning Phase Complete: {stats['learning_phase_complete']}")
    print(f"Current Streak: {stats['current_logging_streak']} days")
    print(f"\nWeek 1 Averages:")
    print(f"  - Calories: {stats['week1_avg_calories']:.1f} kcal")
    print(f"  - Protein: {stats['week1_avg_protein']:.1f}g")
    print(f"  - Iron: {stats['week1_avg_iron']:.1f}mg")
    print(f"  - Calcium: {stats['week1_avg_calcium']:.1f}mg")
    print(f"\nNow test the food logging endpoint with this user_id!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(create_test_user())
