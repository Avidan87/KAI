"""
User Database Operations

CRUD operations for user profiles and health information.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from .db_setup import get_db

logger = logging.getLogger(__name__)


async def create_user(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    gender: str = "female",
    age: int = 25
) -> Dict[str, Any]:
    """
    Create a new user profile.

    Args:
        user_id: Unique user identifier
        email: User email (optional)
        name: User name (optional)
        gender: User gender (male/female)
        age: User age (13-120)

    Returns:
        dict: Created user data

    Raises:
        ValueError: If user already exists or invalid data
    """
    async with get_db() as db:
        # Check if user exists
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            raise ValueError(f"User {user_id} already exists")

        # Create user
        await db.execute(
            """
            INSERT INTO users (user_id, email, name, gender, age, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, name, gender, age, datetime.now().isoformat(), datetime.now().isoformat())
        )

        # Create default health profile
        await db.execute(
            """
            INSERT INTO user_health (user_id, updated_at)
            VALUES (?, ?)
            """,
            (user_id, datetime.now().isoformat())
        )

        await db.commit()

        logger.info(f"✓ Created user: {user_id}")

        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "gender": gender,
            "age": age,
        }


async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile by ID.

    Args:
        user_id: User identifier

    Returns:
        dict: User data or None if not found
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT u.*, h.weight_kg, h.height_cm, h.activity_level,
                   h.health_goals, h.dietary_restrictions, h.target_weight_kg,
                   h.calculated_calorie_goal, h.custom_calorie_goal, h.active_calorie_goal
            FROM users u
            LEFT JOIN user_health h ON u.user_id = h.user_id
            WHERE u.user_id = ?
            """,
            (user_id,)
        )

        row = await cursor.fetchone()

        if not row:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "name": row[2],
            "gender": row[3],
            "age": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "weight_kg": row[7] if len(row) > 7 else None,
            "height_cm": row[8] if len(row) > 8 else None,
            "activity_level": row[9] if len(row) > 9 else None,
            "health_goals": row[10] if len(row) > 10 else None,
            "dietary_restrictions": row[11] if len(row) > 11 else None,
            "target_weight_kg": row[12] if len(row) > 12 else None,
            "calculated_calorie_goal": row[13] if len(row) > 13 else None,
            "custom_calorie_goal": row[14] if len(row) > 14 else None,
            "active_calorie_goal": row[15] if len(row) > 15 else None,
        }


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile by email.

    Args:
        email: User email

    Returns:
        dict: User data or None if not found
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT u.*, h.weight_kg, h.height_cm, h.activity_level,
                   h.health_goals, h.dietary_restrictions, h.target_weight_kg,
                   h.calculated_calorie_goal, h.custom_calorie_goal, h.active_calorie_goal
            FROM users u
            LEFT JOIN user_health h ON u.user_id = h.user_id
            WHERE u.email = ?
            """,
            (email,)
        )

        row = await cursor.fetchone()

        if not row:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "name": row[2],
            "gender": row[3],
            "age": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "weight_kg": row[7] if len(row) > 7 else None,
            "height_cm": row[8] if len(row) > 8 else None,
            "activity_level": row[9] if len(row) > 9 else None,
            "health_goals": row[10] if len(row) > 10 else None,
            "dietary_restrictions": row[11] if len(row) > 11 else None,
            "target_weight_kg": row[12] if len(row) > 12 else None,
            "calculated_calorie_goal": row[13] if len(row) > 13 else None,
            "custom_calorie_goal": row[14] if len(row) > 14 else None,
            "active_calorie_goal": row[15] if len(row) > 15 else None,
        }


async def update_user(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    gender: Optional[str] = None,
    age: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update user profile.

    Args:
        user_id: User identifier
        email: Updated email
        name: Updated name
        gender: Updated gender
        age: Updated age

    Returns:
        dict: Updated user data

    Raises:
        ValueError: If user not found
    """
    async with get_db() as db:
        # Check user exists
        existing = await get_user(user_id)
        if not existing:
            raise ValueError(f"User {user_id} not found")

        # Build update query dynamically
        updates = []
        params = []

        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if gender is not None:
            updates.append("gender = ?")
            params.append(gender)
        if age is not None:
            updates.append("age = ?")
            params.append(age)

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(user_id)

            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            await db.execute(query, params)
            await db.commit()

        logger.info(f"✓ Updated user: {user_id}")

        return await get_user(user_id)


async def update_user_health(
    user_id: str,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    activity_level: Optional[str] = None,
    health_goals: Optional[str] = None,
    dietary_restrictions: Optional[str] = None,
    target_weight_kg: Optional[float] = None,
    calculated_calorie_goal: Optional[float] = None,
    custom_calorie_goal: Optional[float] = None,
    active_calorie_goal: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Update user health information.

    NEW: Removed pregnancy/lactation/anemia fields completely!
    Added: target_weight_kg, calculated_calorie_goal, custom_calorie_goal, active_calorie_goal

    Args:
        user_id: User identifier
        weight_kg: Current weight in kilograms
        height_cm: Height in centimeters
        activity_level: Activity level (sedentary, light, moderate, active, very_active)
        health_goals: Health goals (lose_weight, gain_muscle, maintain_weight, general_wellness)
        dietary_restrictions: Dietary restrictions text
        target_weight_kg: Goal weight (for weight loss/gain tracking)
        calculated_calorie_goal: KAI's calculated calorie recommendation (BMR/TDEE-based)
        custom_calorie_goal: User's manual calorie override
        active_calorie_goal: The active calorie goal being used

    Returns:
        dict: Updated user health data

    Raises:
        ValueError: If user not found
    """
    async with get_db() as db:
        # Check user exists
        existing = await get_user(user_id)
        if not existing:
            raise ValueError(f"User {user_id} not found")

        # Build update query
        updates = []
        params = []

        if weight_kg is not None:
            updates.append("weight_kg = ?")
            params.append(weight_kg)
        if height_cm is not None:
            updates.append("height_cm = ?")
            params.append(height_cm)
        if activity_level is not None:
            updates.append("activity_level = ?")
            params.append(activity_level)
        if health_goals is not None:
            updates.append("health_goals = ?")
            params.append(health_goals)
        if dietary_restrictions is not None:
            updates.append("dietary_restrictions = ?")
            params.append(dietary_restrictions)
        if target_weight_kg is not None:
            updates.append("target_weight_kg = ?")
            params.append(target_weight_kg)
        if calculated_calorie_goal is not None:
            updates.append("calculated_calorie_goal = ?")
            params.append(calculated_calorie_goal)
        if custom_calorie_goal is not None:
            updates.append("custom_calorie_goal = ?")
            params.append(custom_calorie_goal)
        if active_calorie_goal is not None:
            updates.append("active_calorie_goal = ?")
            params.append(active_calorie_goal)

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(user_id)

            query = f"UPDATE user_health SET {', '.join(updates)} WHERE user_id = ?"
            await db.execute(query, params)
            await db.commit()

        logger.info(f"✓ Updated health info for user: {user_id}")

        return await get_user(user_id)


async def get_user_health_profile(user_id: str) -> Dict[str, Any]:
    """
    Get user health profile with RDV calculations.

    NEW: Uses BMR/TDEE-based calculations if profile is complete, otherwise uses basic RDV.
    NO pregnancy/lactation adjustments - removed completely!

    Returns user health info plus calculated RDV values based on:
    - Gender
    - Age
    - Weight (if available)
    - Height (if available)
    - Activity level (if available)
    - Health goals (if available)

    Args:
        user_id: User identifier

    Returns:
        dict: User health profile with RDV values

    Raises:
        ValueError: If user not found
    """
    user = await get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Check if profile is complete (has weight, height, activity, goals)
    profile_complete = all([
        user.get("weight_kg"),
        user.get("height_cm"),
        user.get("activity_level"),
        user.get("health_goals")
    ])

    # Calculate RDV using appropriate method
    if profile_complete:
        # Use NEW BMR/TDEE-based calculation
        from kai.utils.nutrition_rdv import calculate_user_rdv_v2

        try:
            rdv_result = calculate_user_rdv_v2(user)
            rdv = rdv_result["rdv"]
        except (ValueError, KeyError) as e:
            logger.warning(f"Error calculating BMR/TDEE RDV for user {user_id}: {e}. Falling back to basic RDV.")
            # Fall back to basic calculation
            from kai.utils.nutrition_rdv import calculate_user_rdv
            rdv = calculate_user_rdv({
                "gender": user["gender"],
                "age": user["age"],
                "activity_level": user.get("activity_level", "moderate")
            })
    else:
        # Use OLD basic calculation (no weight/height)
        from kai.utils.nutrition_rdv import calculate_user_rdv
        rdv = calculate_user_rdv({
            "gender": user["gender"],
            "age": user["age"],
            "activity_level": user.get("activity_level", "moderate")
        })

    return {
        "user_id": user_id,
        "email": user.get("email"),
        "name": user["name"],
        "gender": user["gender"],
        "age": user["age"],
        "weight_kg": user.get("weight_kg"),
        "height_cm": user.get("height_cm"),
        "activity_level": user.get("activity_level"),
        "health_goals": user.get("health_goals"),
        "dietary_restrictions": user.get("dietary_restrictions"),
        "target_weight_kg": user.get("target_weight_kg"),
        "calculated_calorie_goal": user.get("calculated_calorie_goal"),
        "custom_calorie_goal": user.get("custom_calorie_goal"),
        "active_calorie_goal": user.get("active_calorie_goal"),
        "profile_complete": profile_complete,
        "rdv": rdv,
    }


async def delete_user(user_id: str) -> bool:
    """
    Delete user and all associated data.

    Args:
        user_id: User identifier

    Returns:
        bool: True if deleted, False if not found
    """
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

        deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"✓ Deleted user: {user_id}")
        else:
            logger.warning(f"User not found: {user_id}")

        return deleted


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from .db_setup import initialize_database

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_user_operations():
        """Test user CRUD operations"""
        print("\n" + "="*60)
        print("Testing User Operations")
        print("="*60 + "\n")

        # Initialize database
        await initialize_database()

        # Create user
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user = await create_user(
            user_id=test_user_id,
            email="ada@example.com",
            name="Ada Nwankwo",
            gender="female",
            age=28
        )
        print(f"Created user: {user}")

        # Get user
        user = await get_user(test_user_id)
        print(f"\nRetrieved user: {user}")

        # Update health info
        user = await update_user_health(
            user_id=test_user_id,
            is_pregnant=True,
            weight_kg=65.0,
            height_cm=165.0,
            activity_level="moderate",
            health_goals="Healthy pregnancy, prevent anemia"
        )
        print(f"\nUpdated health info: {user}")

        # Get health profile with RDA
        profile = await get_user_health_profile(test_user_id)
        print(f"\nHealth profile with RDA:")
        print(f"  RDA Calories: {profile['rdv']['calories']}")
        print(f"  RDA Iron: {profile['rdv']['iron']}mg (pregnant)")
        print(f"  RDA Protein: {profile['rdv']['protein']}g")

        # Delete user
        deleted = await delete_user(test_user_id)
        print(f"\nDeleted user: {deleted}")

        print("\n✓ User operations test complete!\n")

    asyncio.run(test_user_operations())
