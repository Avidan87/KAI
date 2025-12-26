"""
Test Health Profile Endpoint with Valid Data
"""

import json
import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_valid_health_profile():
    """Test with valid data (no custom_calorie_goal)"""
    print("\n" + "="*60)
    print("Testing Health Profile with Valid Data")
    print("="*60 + "\n")

    # Login
    print("Step 1: Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"email": "sarah@test.com", "password": "password123"},
        timeout=10
    )
    token = login_response.json()["access_token"]
    print("[OK] Logged in")

    # Update health profile WITHOUT custom_calorie_goal
    print("\nStep 2: Updating health profile (auto-calculate calories)...")
    health_data = {
        "weight_kg": 90,
        "height_cm": 182,
        "activity_level": "moderate",
        "health_goals": "lose_weight",
        "target_weight_kg": 75
    }

    headers = {"Authorization": f"Bearer {token}"}
    update_response = requests.put(
        f"{BASE_URL}/users/health-profile",
        data=health_data,
        headers=headers,
        timeout=10
    )

    print(f"   Status Code: {update_response.status_code}")

    if update_response.status_code == 200:
        result = update_response.json()
        print("[OK] Health profile updated successfully!\n")

        rdv = result['calculated_rdv']
        print("   Calculated RDV:")
        print(f"   - BMR: {rdv['bmr']} kcal")
        print(f"   - TDEE: {rdv['tdee']} kcal")
        print(f"   - Recommended Calories: {rdv['recommended_calories']} kcal")
        print(f"   - Active Calories: {rdv['active_calories']} kcal")

        if 'weight_projection' in result:
            proj = result['weight_projection']
            print("\n   Weight Projection:")
            print(f"   - Current: {proj['current_weight_kg']} kg")
            print(f"   - Target: {proj['target_weight_kg']} kg")
            print(f"   - Daily Deficit: {proj['daily_deficit_kcal']} kcal")
            print(f"   - Days to Target: {proj['days_to_target']}")
            print(f"   - Target Date: {proj['target_date']}")
    else:
        print(f"[FAIL] Error: {update_response.text}")

    print("\n" + "="*60)
    print("[OK] Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_valid_health_profile()
