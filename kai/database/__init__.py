"""
KAI Database Package

User database management with aiosqlite for:
- User profiles and health data
- Meal logging history
- Daily nutrient tracking
- Session management
"""

from .db_setup import initialize_database, get_db
from .user_operations import (
    create_user,
    get_user,
    get_user_by_email,
    update_user,
    update_user_health,
    get_user_health_profile,
)
from .meal_operations import (
    log_meal,
    get_user_meals,
    get_meals_by_date,
    get_daily_nutrition_totals,
)

__all__ = [
    # Database setup
    "initialize_database",
    "get_db",

    # User operations
    "create_user",
    "get_user",
    "get_user_by_email",
    "update_user",
    "update_user_health",
    "get_user_health_profile",

    # Meal operations
    "log_meal",
    "get_user_meals",
    "get_meals_by_date",
    "get_daily_nutrition_totals",
]
