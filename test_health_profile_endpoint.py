"""
Test Health Profile Endpoint Fix

Tests the fixed health profile endpoint to ensure it properly handles
the NoneType error that was occurring.
"""

import json
import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_health_profile_update():
    """Test updating health profile with the exact data the user sent"""
    print("\n" + "="*60)
    print("Testing Health Profile Endpoint Fix")
    print("="*60 + "\n")

    # Step 1: Login with the test user
    print("Step 1: Logging in with test user...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": "sarah@test.com",
            "password": "password123"
        },
        timeout=10
    )

    if login_response.status_code != 200:
        print(f"[FAIL] Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return

    login_data = login_response.json()
    token = login_data["access_token"]
    print(f"[OK] Login successful! Token: {token[:20]}...")

    # Step 2: Update health profile with exact data user sent
    print("\nStep 2: Updating health profile...")
    health_data = {
        "weight_kg": 90,
        "height_cm": 182,
        "activity_level": "moderate",
        "health_goals": "lose_weight",
        "target_weight_kg": 75,
        "custom_calorie_goal": 0
    }

    print(f"   Data: {json.dumps(health_data, indent=2)}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    update_response = requests.put(
        f"{BASE_URL}/users/health-profile",
        data=health_data,
        headers=headers,
        timeout=10
    )

    print(f"\n   Status Code: {update_response.status_code}")

    if update_response.status_code == 200:
        result = update_response.json()
        print("[OK] Health profile updated successfully!")
        print("\n   Response:")
        print(f"   - Success: {result['success']}")
        print(f"   - Message: {result['message']}")
        print(f"   - Profile Complete: {result['profile_complete']}")

        if 'calculated_rdv' in result:
            rdv = result['calculated_rdv']
            print("\n   Calculated RDV:")
            print(f"   - BMR: {rdv['bmr']} kcal")
            print(f"   - TDEE: {rdv['tdee']} kcal")
            print(f"   - Recommended Calories: {rdv['recommended_calories']} kcal")
            print(f"   - Active Calories: {rdv['active_calories']} kcal")

        if 'weight_projection' in result:
            proj = result['weight_projection']
            print("\n   Weight Projection:")
            print(f"   - Current Weight: {proj['current_weight_kg']} kg")
            print(f"   - Target Weight: {proj['target_weight_kg']} kg")
            print(f"   - Daily Deficit: {proj['daily_deficit_kcal']} kcal")
            print(f"   - Days to Target: {proj['days_to_target']}")
            print(f"   - Target Date: {proj['target_date']}")

        print(f"\n   Processing Time: {result['processing_time_ms']} ms")

    else:
        print("[FAIL] Health profile update failed!")
        print(f"   Response: {update_response.text}")

        # Try to parse error detail
        try:
            error_data = update_response.json()
            print(f"   Error Detail: {error_data.get('detail', 'No detail provided')}")
        except Exception:
            pass

    # Step 3: Verify by fetching profile
    print("\n" + "-"*60)
    print("Step 3: Verifying by fetching user profile...")

    profile_response = requests.get(
        f"{BASE_URL}/users/profile",
        headers=headers,
        timeout=10
    )

    if profile_response.status_code == 200:
        profile = profile_response.json()
        print("[OK] Profile fetched successfully!")
        print(f"\n   User: {profile['name']} ({profile['email']})")
        print(f"   Weight: {profile['weight_kg']} kg")
        print(f"   Height: {profile['height_cm']} cm")
        print(f"   Activity Level: {profile['activity_level']}")
        print(f"   Health Goals: {profile['health_goals']}")
        print(f"   Target Weight: {profile['target_weight_kg']} kg")
        print(f"   Active Calorie Goal: {profile['active_calorie_goal']} kcal")
        print(f"   Profile Complete: {profile['profile_complete']}")
    else:
        print(f"[FAIL] Profile fetch failed: {profile_response.status_code}")

    print("\n" + "="*60)
    print("[OK] Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_health_profile_update()
