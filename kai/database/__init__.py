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
from .stats_operations import (
    get_user_stats,
    initialize_user_stats,
    update_user_stats,
    get_user_food_frequency,
    update_food_frequency,
    reset_weekly_food_frequency,
    log_recommendation,
    mark_recommendation_followed,
    get_recommendation_stats,
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

    # Stats operations
    "get_user_stats",
    "initialize_user_stats",
    "update_user_stats",
    "get_user_food_frequency",
    "update_food_frequency",
    "reset_weekly_food_frequency",
    "log_recommendation",
    "mark_recommendation_followed",
    "get_recommendation_stats",
]
