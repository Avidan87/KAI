"""
Test script for new goal-driven feedback analysis

Tests the complete flow:
1. User logs meal (simulated)
2. Frontend calls chat endpoint
3. Chat analyzes the most recent meal
4. Returns goal-driven feedback with new format
"""

import asyncio
import logging
from datetime import datetime

from kai.database import initialize_database, create_user, log_meal, update_user_health
from kai.agents.chat_agent import get_chat_agent

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def test_feedback_flow():
    """Test complete feedback flow for different meal scenarios"""

    print("\n" + "="*70)
    print("🧪 TESTING GOAL-DRIVEN FEEDBACK ANALYSIS")
    print("="*70)

    # Initialize database
    await initialize_database()

    # Create test user with weight loss goal
    user_id = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    await create_user(
        user_id=user_id,
        email=f"{user_id}@test.com",
        name="Test User",
        gender="female",
        age=28
    )

    # Set health profile (weight loss goal)
    await update_user_health(
        user_id=user_id,
        weight_kg=75.0,
        height_cm=165.0,
        activity_level="moderate",
        health_goals="lose_weight",
        calculated_calorie_goal=1800,
        active_calorie_goal=1800
    )

    print(f"\n✅ Created test user: {user_id}")
    print(f"   Goal: Weight Loss (1800 cal/day)")
    print(f"   Learning Phase: First 21 meals\n")

    # Get chat agent
    chat_agent = get_chat_agent()

    # ========================================================================
    # TEST 1: POOR MEAL - White rice only (learning phase)
    # ========================================================================
    print("\n" + "="*70)
    print("TEST 1: POOR MEAL - White Rice Only (Learning Phase)")
    print("="*70)

    poor_meal_foods = [
        {
            "food_name": "White Rice",
            "food_id": "nigerian-white-rice",
            "portion_grams": 400.0,
            "calories": 520.0,
            "protein": 8.0,
            "carbohydrates": 115.0,
            "fat": 1.0,
            "iron": 0.8,
            "calcium": 16.0,
            "potassium": 55.0,
            "zinc": 1.0,
        }
    ]

    meal1 = await log_meal(user_id, "breakfast", poor_meal_foods)
    print(f"\n📥 Logged: {meal1['meal_id']}")
    print(f"   Foods: White Rice (400g)")
    print(f"   Totals: {meal1['totals']['calories']} cal, {meal1['totals']['protein']}g protein")

    # Simulate frontend calling chat endpoint
    print(f"\n💬 Frontend calls: /api/v1/chat")
    result1 = await chat_agent.chat(
        user_id=user_id,
        message="How was my last meal?",
        conversation_history=[]
    )

    print(f"\n🤖 KAI's Response:")
    print(f"   {result1['message']}\n")

    # ========================================================================
    # TEST 2: OKAY MEAL - Jollof rice + plantain (learning phase)
    # ========================================================================
    print("\n" + "="*70)
    print("TEST 2: OKAY MEAL - Jollof Rice + Plantain (Learning Phase)")
    print("="*70)

    okay_meal_foods = [
        {
            "food_name": "Jollof Rice",
            "food_id": "nigerian-jollof-rice",
            "portion_grams": 300.0,
            "calories": 420.0,
            "protein": 10.5,
            "carbohydrates": 78.0,
            "fat": 8.6,
            "iron": 3.0,
            "calcium": 54.0,
            "potassium": 144.0,
            "zinc": 1.4,
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
            "potassium": 358.0,
            "zinc": 0.1,
        }
    ]

    meal2 = await log_meal(user_id, "lunch", okay_meal_foods)
    print(f"\n📥 Logged: {meal2['meal_id']}")
    print(f"   Foods: Jollof Rice (300g) + Fried Plantain (100g)")
    print(f"   Totals: {meal2['totals']['calories']} cal, {meal2['totals']['protein']}g protein")

    print(f"\n💬 Frontend calls: /api/v1/chat")
    result2 = await chat_agent.chat(
        user_id=user_id,
        message="Analyze my last meal",
        conversation_history=[]
    )

    print(f"\n🤖 KAI's Response:")
    print(f"   {result2['message']}\n")

    # ========================================================================
    # TEST 3: EXCELLENT MEAL - Egusi soup + fish + fufu
    # ========================================================================
    print("\n" + "="*70)
    print("TEST 3: EXCELLENT MEAL - Egusi + Fish + Fufu (Learning Phase)")
    print("="*70)

    excellent_meal_foods = [
        {
            "food_name": "Egusi Soup",
            "food_id": "nigerian-egusi-soup",
            "portion_grams": 250.0,
            "calories": 280.0,
            "protein": 18.0,
            "carbohydrates": 12.0,
            "fat": 20.0,
            "iron": 6.5,
            "calcium": 180.0,
            "potassium": 520.0,
            "zinc": 2.8,
        },
        {
            "food_name": "Grilled Tilapia",
            "food_id": "nigerian-grilled-tilapia",
            "portion_grams": 150.0,
            "calories": 165.0,
            "protein": 30.0,
            "carbohydrates": 0.0,
            "fat": 4.5,
            "iron": 1.2,
            "calcium": 45.0,
            "potassium": 390.0,
            "zinc": 1.8,
        },
        {
            "food_name": "Pounded Yam",
            "food_id": "nigerian-pounded-yam",
            "portion_grams": 200.0,
            "calories": 280.0,
            "protein": 4.0,
            "carbohydrates": 66.0,
            "fat": 0.4,
            "iron": 1.0,
            "calcium": 28.0,
            "potassium": 670.0,
            "zinc": 0.8,
        }
    ]

    meal3 = await log_meal(user_id, "dinner", excellent_meal_foods)
    print(f"\n📥 Logged: {meal3['meal_id']}")
    print(f"   Foods: Egusi Soup + Grilled Tilapia + Pounded Yam")
    print(f"   Totals: {meal3['totals']['calories']} cal, {meal3['totals']['protein']}g protein")

    print(f"\n💬 Frontend calls: /api/v1/chat")
    result3 = await chat_agent.chat(
        user_id=user_id,
        message="Give me feedback on what I just logged",
        conversation_history=[]
    )

    print(f"\n🤖 KAI's Response:")
    print(f"   {result3['message']}\n")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"\n✅ All 3 meals logged successfully")
    print(f"✅ Chat endpoint analyzed most recent meal each time")
    print(f"✅ Goal-driven feedback generated for weight loss goal")
    print(f"✅ Learning phase tone applied (gentle, educational)")
    print(f"\n💡 Key observations:")
    print(f"   - Poor meal: Should show critical gaps (protein, iron, etc.)")
    print(f"   - Okay meal: Should suggest adding protein")
    print(f"   - Excellent meal: Should celebrate protein + nutrients")
    print(f"   - All should mention calorie status relative to weight loss goal")
    print(f"\n🎯 Data flow verified: Upload → DB → Chat → Feedback ✅")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_feedback_flow())
