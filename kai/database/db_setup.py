"""
Database Setup and Initialization

Creates SQLite database with tables for users, meals, and nutrient tracking.
Uses aiosqlite for async operations.
"""

import aiosqlite
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Database file location
DB_PATH = Path("kai_database.db")


async def initialize_database(db_path: Optional[Path] = None) -> None:
    """
    Initialize SQLite database with all required tables.

    Creates tables for:
    - users: User profiles and demographics
    - user_health: Health information and RDA adjustments
    - meals: Meal logging records
    - meal_foods: Foods within each meal
    - daily_nutrients: Daily nutrient totals

    Args:
        db_path: Optional custom database path
    """
    path = db_path or DB_PATH
    logger.info(f"Initializing database at: {path}")

    async with aiosqlite.connect(path) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                gender TEXT CHECK(gender IN ('male', 'female')),
                age INTEGER CHECK(age >= 13 AND age <= 120),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User health information
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_health (
                user_id TEXT PRIMARY KEY,
                is_pregnant BOOLEAN DEFAULT 0,
                is_lactating BOOLEAN DEFAULT 0,
                has_anemia BOOLEAN DEFAULT 0,
                weight_kg REAL,
                height_cm REAL,
                activity_level TEXT CHECK(activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
                health_goals TEXT,
                dietary_restrictions TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Meals table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                meal_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
                meal_date TEXT NOT NULL,
                meal_time TEXT NOT NULL,
                image_url TEXT,
                user_description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Foods within meals
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meal_foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id TEXT NOT NULL,
                food_name TEXT NOT NULL,
                food_id TEXT,
                portion_grams REAL NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                carbohydrates REAL NOT NULL,
                fat REAL NOT NULL,
                iron REAL NOT NULL,
                calcium REAL NOT NULL,
                vitamin_a REAL NOT NULL,
                zinc REAL NOT NULL,
                confidence REAL DEFAULT 1.0,
                FOREIGN KEY (meal_id) REFERENCES meals(meal_id) ON DELETE CASCADE
            )
        """)

        # Daily nutrient totals (aggregated)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_nutrients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_calories REAL DEFAULT 0,
                total_protein REAL DEFAULT 0,
                total_carbohydrates REAL DEFAULT 0,
                total_fat REAL DEFAULT 0,
                total_iron REAL DEFAULT 0,
                total_calcium REAL DEFAULT 0,
                total_vitamin_a REAL DEFAULT 0,
                total_zinc REAL DEFAULT 0,
                meal_count INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, date)
            )
        """)

        # Create indexes for faster queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_meals_user_date
            ON meals(user_id, meal_date)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_nutrients_user_date
            ON daily_nutrients(user_id, date)
        """)

        await db.commit()
        logger.info("✓ Database tables created successfully")


@asynccontextmanager
async def get_db(db_path: Optional[Path] = None):
    """
    Async context manager for database connections.

    Usage:
        async with get_db() as db:
            await db.execute(...)

    Args:
        db_path: Optional custom database path

    Yields:
        aiosqlite.Connection: Database connection
    """
    path = db_path or DB_PATH
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row  # Enable dict-like row access
    await db.execute("PRAGMA foreign_keys = ON")

    try:
        yield db
    finally:
        await db.close()


async def reset_database(db_path: Optional[Path] = None) -> None:
    """
    Drop all tables and reinitialize database.

    WARNING: This deletes all data!

    Args:
        db_path: Optional custom database path
    """
    path = db_path or DB_PATH
    logger.warning(f"⚠️ Resetting database at: {path}")

    async with aiosqlite.connect(path) as db:
        # Drop all tables
        await db.execute("DROP TABLE IF EXISTS daily_nutrients")
        await db.execute("DROP TABLE IF EXISTS meal_foods")
        await db.execute("DROP TABLE IF EXISTS meals")
        await db.execute("DROP TABLE IF EXISTS user_health")
        await db.execute("DROP TABLE IF EXISTS users")
        await db.commit()

    # Reinitialize
    await initialize_database(db_path)
    logger.info("✓ Database reset complete")


async def get_database_stats() -> dict:
    """
    Get statistics about the database.

    Returns:
        dict: Database statistics (user count, meal count, etc.)
    """
    async with get_db() as db:
        # Count users
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        user_count = (await cursor.fetchone())["count"]

        # Count meals
        cursor = await db.execute("SELECT COUNT(*) as count FROM meals")
        meal_count = (await cursor.fetchone())["count"]

        # Count total foods logged
        cursor = await db.execute("SELECT COUNT(*) as count FROM meal_foods")
        food_count = (await cursor.fetchone())["count"]

        return {
            "users": user_count,
            "meals": meal_count,
            "foods_logged": food_count,
            "database_path": str(DB_PATH),
        }


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_database():
        """Test database setup"""
        print("\n" + "="*60)
        print("Testing Database Setup")
        print("="*60 + "\n")

        # Initialize database
        await initialize_database()

        # Get stats
        stats = await get_database_stats()
        print("\nDatabase Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✓ Database setup test complete!\n")

    asyncio.run(test_database())
