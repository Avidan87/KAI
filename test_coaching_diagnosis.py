"""
Diagnostic Script: Check Coaching Agent Behavior
"""
import asyncio
import logging
from kai.database import get_user_stats, get_user

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def diagnose_coaching(user_id: str):
    """Diagnose coaching behavior for a user."""
    print(f"\n{'='*60}")
    print(f"Coaching Diagnosis for user: {user_id}")
    print(f"{'='*60}\n")

    # Check if user exists
    try:
        user = await get_user(user_id)
        print(f"✓ User exists:")
        print(f"  - Gender: {user.get('gender')}")
        print(f"  - Age: {user.get('age')}")
        print(f"  - Created: {user.get('created_at')}")
    except Exception as e:
        print(f"✗ User not found: {e}")
        return

    # Check user stats
    try:
        stats = await get_user_stats(user_id)
        print(f"\n✓ User stats:")
        print(f"  - Total meals: {stats.get('total_meals_logged', 0)}")
        print(f"  - Learning phase complete: {stats.get('learning_phase_complete', False)}")
        print(f"  - Current streak: {stats.get('current_logging_streak', 0)} days")
        print(f"  - Account age: {stats.get('account_age_days', 0)} days")

        print(f"\n  Week 1 Averages:")
        print(f"    - Calories: {stats.get('week1_avg_calories', 0):.1f} kcal")
        print(f"    - Protein: {stats.get('week1_avg_protein', 0):.1f}g")
        print(f"    - Iron: {stats.get('week1_avg_iron', 0):.1f}mg")
        print(f"    - Calcium: {stats.get('week1_avg_calcium', 0):.1f}mg")

        print(f"\n  Trends:")
        print(f"    - Calories: {stats.get('calories_trend', 'N/A')}")
        print(f"    - Protein: {stats.get('protein_trend', 'N/A')}")
        print(f"    - Iron: {stats.get('iron_trend', 'N/A')}")

    except Exception as e:
        print(f"✗ Stats error: {e}")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    import sys

    # Get user_id from command line or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else "test_user_001"

    asyncio.run(diagnose_coaching(user_id))
