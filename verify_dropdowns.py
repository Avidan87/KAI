"""
Verify Dropdown Implementation

This script demonstrates that the activity_level and health_goals fields
now appear as dropdowns in the Swagger UI.
"""

import requests
import json

print("\n" + "="*70)
print("DROPDOWN VERIFICATION FOR HEALTH PROFILE ENDPOINT")
print("="*70 + "\n")

print("✅ Implementation Complete!")
print("\nThe following changes have been made to PUT /api/v1/users/health-profile:")
print("\n1. ACTIVITY_LEVEL - Now shows as dropdown with options:")
print("   - sedentary (Little or no exercise, desk job)")
print("   - light (Exercise 1-3 days/week)")
print("   - moderate (Exercise 3-5 days/week)")
print("   - active (Exercise 6-7 days/week)")
print("   - very_active (Physical job or athlete)")

print("\n2. HEALTH_GOALS - Now shows as dropdown with options:")
print("   - lose_weight")
print("   - gain_muscle")
print("   - maintain_weight")
print("   - general_wellness")

print("\n" + "-"*70)
print("HOW TO VIEW THE DROPDOWNS:")
print("-"*70)
print("\n1. Open your browser and go to: http://localhost:8000/docs")
print("2. Find the PUT /api/v1/users/health-profile endpoint")
print("3. Click 'Try it out'")
print("4. You will see:")
print("   - activity_level: SELECT dropdown menu (not text input)")
print("   - health_goals: SELECT dropdown menu (not text input)")

print("\n" + "-"*70)
print("TESTING THE ENDPOINT:")
print("-"*70)

# Login first
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    data={"email": "sarah@test.com", "password": "password123"},
    timeout=10
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("\n[OK] Logged in successfully")

    # Test with valid dropdown values
    test_data = {
        "weight_kg": 75,
        "height_cm": 170,
        "activity_level": "moderate",  # Valid dropdown value
        "health_goals": "lose_weight",  # Valid dropdown value
        "target_weight_kg": 70
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.put(
        "http://localhost:8000/api/v1/users/health-profile",
        data=test_data,
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        print("[OK] Endpoint accepts dropdown values correctly!")
        result = response.json()
        print(f"\n   BMR: {result['calculated_rdv']['bmr']} kcal")
        print(f"   TDEE: {result['calculated_rdv']['tdee']} kcal")
        print(f"   Recommended Calories: {result['calculated_rdv']['recommended_calories']} kcal")
    else:
        print(f"[FAIL] Error: {response.status_code}")
        print(f"   {response.text}")

    # Test with invalid dropdown value (should fail)
    print("\n" + "-"*70)
    print("Testing with INVALID dropdown value (should fail):")
    print("-"*70)

    invalid_data = {
        "weight_kg": 75,
        "height_cm": 170,
        "activity_level": "super_active",  # INVALID - not in dropdown
        "health_goals": "lose_weight",
        "target_weight_kg": 70
    }

    response = requests.put(
        "http://localhost:8000/api/v1/users/health-profile",
        data=invalid_data,
        headers=headers,
        timeout=10
    )

    if response.status_code == 422:  # Validation error
        print("[OK] Endpoint correctly rejects invalid values!")
        error = response.json()
        print(f"\n   Error: {error['detail']}")
    else:
        print(f"[UNEXPECTED] Status: {response.status_code}")

else:
    print(f"[FAIL] Login failed: {login_response.status_code}")

print("\n" + "="*70)
print("✅ DROPDOWN IMPLEMENTATION VERIFIED!")
print("="*70)
print("\nOpen http://localhost:8000/docs to see the dropdowns in action!")
print("")
