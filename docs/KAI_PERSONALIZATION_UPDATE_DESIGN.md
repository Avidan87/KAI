# KAI Personalization System Update - Design Document

**Date:** 2025-12-24
**Version:** 2.0
**Status:** Implementation Ready

---

## Executive Summary

This document outlines the comprehensive redesign of KAI's personalization system to transform it from a female-focused nutrition coach to a universal, science-based nutrition platform for all users (male and female) pursuing various health goals.

### Key Changes:
1. **Remove maternal-specific features** (pregnancy/lactation)
2. **Implement BMR/TDEE-based calculations** using actual body metrics
3. **Add goal-based personalization** (weight loss, muscle gain, maintenance)
4. **Progressive profiling** (optional health profile completion)
5. **Scientific accuracy** with personalized calorie targets

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Design Goals](#design-goals)
3. [Architecture Overview](#architecture-overview)
4. [Database Schema Changes](#database-schema-changes)
5. [API Endpoints](#api-endpoints)
6. [Calculation Logic](#calculation-logic)
7. [User Experience Flow](#user-experience-flow)
8. [Implementation Plan](#implementation-plan)
9. [Testing Strategy](#testing-strategy)
10. [Rollback Plan](#rollback-plan)

---

## 1. Current State Analysis

### Current Personalization Factors
- ✅ Gender (male/female)
- ✅ Age (with 51+ adjustments)
- ⚠️ Activity Level (basic multipliers only)
- ⚠️ Pregnancy Status (maternal focus)
- ⚠️ Lactation Status (maternal focus)

### Current Limitations
1. **Female-focused**: Pregnancy/lactation makes KAI seem primarily for women
2. **No body composition**: Doesn't use weight/height in calculations
3. **Generic targets**: Same calorie target for all 70kg users regardless of height/activity
4. **No goal awareness**: Can't differentiate between weight loss vs muscle gain
5. **No progress tracking**: Can't project time to goal weight

### Current RDV Calculation
```python
# Location: kai/utils/nutrition_rdv.py & kai/database/user_operations.py
# Method: Base values + Age adjustments + Activity multipliers + Pregnancy/Lactation

Base RDV (Gender-based)
  → Age Adjustment (51+)
  → Activity Multiplier (applied to macros)
  → Pregnancy/Lactation Adjustment
  → Final RDV
```

**Problem**: Not personalized enough for serious nutrition coaching!

---

## 2. Design Goals

### Primary Objectives
1. ✅ **Universal Appeal**: Make KAI equally relevant for males and females
2. ✅ **Scientific Accuracy**: Use BMR/TDEE formulas based on actual body metrics
3. ✅ **Goal-Oriented**: Adjust targets based on user's health goals
4. ✅ **Progressive Profiling**: Low friction signup, full personalization when ready
5. ✅ **Accurate Progress Tracking**: Project time to goal, track weekly changes

### Success Metrics
- More accurate calorie targets (within 10% of actual needs)
- Higher profile completion rate (target: 70%+ complete health profile)
- Better user retention (users see personalized results = stay engaged)
- Equal male/female signup distribution (currently skewed female)

---

## 3. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         USER SIGNUP                         │
│  Required: Email, Name, Gender, Age                         │
│  Optional: Weight, Height, Activity, Goals                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROFILE STATE CHECK                      │
│  Is profile complete? (weight, height, activity, goals)     │
└──────┬─────────────────────────────────────────┬────────────┘
       │ NO                                       │ YES
       │                                          │
       ▼                                          ▼
┌─────────────────────┐                ┌──────────────────────┐
│  BASIC MODE         │                │  FULL MODE           │
│  - Generic RDV      │                │  - BMR/TDEE calc     │
│  - Basic coaching   │                │  - Goal-based targets│
│  - Prompt to        │                │  - Progress tracking │
│    complete profile │                │  - Weight projections│
└─────────────────────┘                └──────────────────────┘
       │                                          │
       └──────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    MEAL LOGGING & COACHING                  │
│  - Vision Agent: Detect foods                               │
│  - Knowledge Agent: Get nutrition data                      │
│  - Coaching Agent: Use personalized RDV                     │
│  - Stats Update: Track progress                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Completes Health Profile
    ↓
Calculate BMR (Mifflin-St Jeor)
    ↓
Calculate TDEE (BMR × Activity Multiplier)
    ↓
Adjust for Goal (deficit/surplus/maintenance)
    ↓
Calculate Nutrient Targets (protein, carbs, fat, micros)
    ↓
Store in Database (calculated_calorie_goal, active_calorie_goal)
    ↓
Return to User + Weight Projection
    ↓
Use in Coaching Agent for All Future Meals
```

---

## 4. Database Schema Changes

### 4.1 `user_health` Table Updates

**NEW FIELDS TO ADD:**

```sql
-- Goal tracking
target_weight_kg REAL NULL                -- User's goal weight (if weight loss/gain)

-- Calorie goals
calculated_calorie_goal REAL NULL         -- KAI's BMR/TDEE-based recommendation
custom_calorie_goal REAL NULL             -- User's manual override (if set)
active_calorie_goal REAL NULL             -- The one actually used (custom OR calculated)
```

**EXISTING FIELDS (Keep, Update Usage):**

```sql
-- These become REQUIRED for full personalization (but optional at signup)
weight_kg REAL                            -- Current weight
height_cm REAL                            -- Height
activity_level TEXT                       -- sedentary, light, moderate, active, very_active
health_goals TEXT                         -- lose_weight, gain_muscle, maintain_weight, general_wellness

-- These are IGNORED in calculations (keep for backwards compatibility)
is_pregnant BOOLEAN DEFAULT 0             -- ❌ NOT USED
is_lactating BOOLEAN DEFAULT 0            -- ❌ NOT USED
has_anemia BOOLEAN DEFAULT 0              -- ❌ NOT USED YET

-- Keep as-is
dietary_restrictions TEXT
updated_at TIMESTAMP
```

### 4.2 Migration Strategy

**Approach**: Add new fields, don't remove old ones (non-breaking change)

```sql
-- Migration SQL
ALTER TABLE user_health ADD COLUMN target_weight_kg REAL NULL;
ALTER TABLE user_health ADD COLUMN calculated_calorie_goal REAL NULL;
ALTER TABLE user_health ADD COLUMN custom_calorie_goal REAL NULL;
ALTER TABLE user_health ADD COLUMN active_calorie_goal REAL NULL;
```

**Backwards Compatibility**: Existing users with `is_pregnant=1` or `is_lactating=1` will continue to work, but these fields won't affect their RDV calculations anymore.

---

## 5. API Endpoints

### 5.1 Updated Signup Endpoint

**Endpoint**: `POST /api/v1/auth/signup`

**BEFORE:**
```json
{
  "email": "user@example.com",      // Required
  "name": "John",                   // Optional (defaults to "")
  "gender": "male",                 // Optional (defaults to "female")
  "age": 25                         // Optional (defaults to 25)
}
```

**AFTER:**
```json
{
  "email": "user@example.com",      // Required
  "name": "John Doe",               // Required (NO default)
  "gender": "male",                 // Required (NO default)
  "age": 28                         // Required (13-120, NO default)
}
```

**Changes:**
- Remove defaults for `name`, `gender`, `age`
- Make all four fields required
- Validate age range (13-120)
- Validate gender enum ("male" | "female")

**Response** (unchanged):
```json
{
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "gender": "male",
    "age": 28
  },
  "token": "jwt_token_here"
}
```

---

### 5.2 NEW Health Profile Endpoint

**Endpoint**: `PUT /api/v1/users/health-profile`

**Purpose**: Complete health profile for full personalization

**Request Body:**
```json
{
  "weight_kg": 75.0,                          // Required
  "height_cm": 178.0,                         // Required
  "activity_level": "moderate",               // Required (enum)
  "health_goals": "lose_weight",              // Required (enum)
  "target_weight_kg": 70.0,                   // Optional (for weight loss/gain)
  "custom_calorie_goal": null                 // Optional (override KAI's calc)
}
```

**Enums:**
```
activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active"
health_goals: "lose_weight" | "gain_muscle" | "maintain_weight" | "general_wellness"
```

**Response:**
```json
{
  "success": true,
  "profile_complete": true,
  "calculated_rdv": {
    "bmr": 1708.0,                            // Basal Metabolic Rate
    "tdee": 2646.0,                           // Total Daily Energy Expenditure
    "recommended_calories": 2146.0,           // TDEE adjusted for goal
    "active_calories": 2146.0                 // What KAI uses (same if no custom)
  },
  "weight_loss_projection": {                 // Only if weight loss/gain goal
    "current_weight": 75.0,
    "target_weight": 70.0,
    "deficit_per_day": 500.0,
    "estimated_loss_per_week": 0.5,           // kg
    "estimated_weeks_to_goal": 10
  }
}
```

**Validation Rules:**
1. `weight_kg`: 30-300 kg (realistic human range)
2. `height_cm`: 100-250 cm (realistic human range)
3. `activity_level`: Must be valid enum
4. `health_goals`: Must be valid enum
5. `target_weight_kg`: If provided, must be different from current weight
6. `custom_calorie_goal`: If provided, validate (min 1200 female, 1500 male)

**Error Responses:**
```json
// Invalid activity level
{
  "error": "Invalid activity_level. Must be one of: sedentary, light, moderate, active, very_active"
}

// Dangerous custom calorie goal
{
  "error": "Custom calorie goal (800) is dangerously low. Minimum: 1200 (female) or 1500 (male).",
  "level": "danger"
}
```

---

### 5.3 Updated User Profile Endpoint

**Endpoint**: `GET /api/v1/users/profile`

**BEFORE:**
```json
{
  "user": { ... },
  "health": { ... },
  "rdv": { ... }
}
```

**AFTER** (add `profile_complete` flag):
```json
{
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "gender": "male",
    "age": 28
  },
  "health": {
    "weight_kg": 75.0,
    "height_cm": 178.0,
    "activity_level": "moderate",
    "health_goals": "lose_weight",
    "target_weight_kg": 70.0,
    "calculated_calorie_goal": 2146.0,
    "custom_calorie_goal": null,
    "active_calorie_goal": 2146.0,
    "dietary_restrictions": "",
    "is_pregnant": false,                     // Still returned but not used
    "is_lactating": false,                    // Still returned but not used
    "has_anemia": false                       // Still returned but not used
  },
  "profile_complete": true,                   // NEW FLAG
  "missing_fields": [],                       // NEW - empty if complete
  "rdv": {
    "calories": 2146,
    "protein": 150,
    "carbs": 241,
    "fat": 71,
    "iron": 8,
    "calcium": 1000,
    "vitamin_a": 900,
    "zinc": 11
  }
}
```

**Profile Completeness Logic:**
```python
profile_complete = all([
    health.get("weight_kg"),
    health.get("height_cm"),
    health.get("activity_level"),
    health.get("health_goals")
])

missing_fields = []
if not health.get("weight_kg"): missing_fields.append("weight_kg")
if not health.get("height_cm"): missing_fields.append("height_cm")
if not health.get("activity_level"): missing_fields.append("activity_level")
if not health.get("health_goals"): missing_fields.append("health_goals")
```

---

## 6. Calculation Logic

### 6.1 BMR Calculation (Mifflin-St Jeor Equation)

**Why Mifflin-St Jeor?**
- Most accurate equation for modern populations
- Validated in multiple studies
- Better than Harris-Benedict for obese individuals

**Formula:**

```python
def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation

    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: "male" or "female"

    Returns:
        BMR in kcal/day
    """
    if gender == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:  # female
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    return round(bmr, 2)
```

**Examples:**
```
Example 1: 28-year-old female, 70kg, 165cm
BMR = (10 × 70) + (6.25 × 165) - (5 × 28) - 161
    = 700 + 1031.25 - 140 - 161
    = 1430.25 kcal

Example 2: 32-year-old male, 75kg, 178cm
BMR = (10 × 75) + (6.25 × 178) - (5 × 32) + 5
    = 750 + 1112.5 - 160 + 5
    = 1707.5 kcal
```

---

### 6.2 TDEE Calculation (Total Daily Energy Expenditure)

**Activity Level Multipliers** (based on research):

| Activity Level | Multiplier | Description |
|---------------|-----------|-------------|
| Sedentary | 1.2 | Little or no exercise, desk job |
| Light | 1.375 | Light exercise 1-3 days/week |
| Moderate | 1.55 | Moderate exercise 3-5 days/week |
| Active | 1.725 | Hard exercise 6-7 days/week |
| Very Active | 1.9 | Very hard exercise, physical job |

**Formula:**

```python
def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure

    Args:
        bmr: Basal Metabolic Rate (from calculate_bmr)
        activity_level: One of: sedentary, light, moderate, active, very_active

    Returns:
        TDEE in kcal/day
    """
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }

    multiplier = activity_multipliers.get(activity_level, 1.55)  # Default moderate
    tdee = bmr * multiplier

    return round(tdee, 2)
```

**Examples:**
```
Example 1: Female, BMR = 1430 kcal, Moderate activity
TDEE = 1430 × 1.55 = 2216.5 kcal

Example 2: Male, BMR = 1708 kcal, Active
TDEE = 1708 × 1.725 = 2946.3 kcal
```

---

### 6.3 Goal-Based Calorie Adjustment

**Science-Based Adjustments:**

| Goal | Adjustment | Reasoning |
|------|-----------|-----------|
| Lose Weight | TDEE - 500 | 500 kcal deficit = ~0.5kg loss/week (safe, sustainable) |
| Gain Muscle | TDEE + 300 | Small surplus prevents excess fat gain |
| Maintain Weight | TDEE + 0 | Maintenance calories |
| General Wellness | TDEE + 0 | Maintenance calories |

**Formula:**

```python
def calculate_goal_adjusted_calories(tdee: float, health_goal: str) -> float:
    """
    Adjust TDEE based on health goal

    Args:
        tdee: Total Daily Energy Expenditure
        health_goal: One of: lose_weight, gain_muscle, maintain_weight, general_wellness

    Returns:
        Target calories in kcal/day
    """
    adjustments = {
        "lose_weight": -500,
        "gain_muscle": 300,
        "maintain_weight": 0,
        "general_wellness": 0
    }

    adjustment = adjustments.get(health_goal, 0)
    target_calories = tdee + adjustment

    return round(target_calories, 2)
```

---

### 6.4 Macronutrient Calculation

**Protein Requirements** (goal-dependent):

| Goal | Protein Ratio | Example (75kg person) |
|------|--------------|----------------------|
| Lose Weight | 1.6-2.0 g/kg | 120-150g |
| Gain Muscle | 1.8-2.2 g/kg | 135-165g |
| Maintain | 1.2-1.6 g/kg | 90-120g |
| General Wellness | 1.0-1.2 g/kg | 75-90g |

**Carbs & Fat Distribution:**

```python
def calculate_macronutrients(target_calories: float, weight_kg: float, health_goal: str, gender: str) -> dict:
    """
    Calculate macronutrient targets

    Returns:
        {
            "protein_g": float,
            "carbs_g": float,
            "fat_g": float
        }
    """
    # Protein calculation (goal-dependent)
    protein_ratios = {
        "lose_weight": 1.8,      # Higher protein to preserve muscle during deficit
        "gain_muscle": 2.0,      # High protein for muscle synthesis
        "maintain_weight": 1.4,
        "general_wellness": 1.2
    }

    protein_ratio = protein_ratios.get(health_goal, 1.4)
    protein_g = round(weight_kg * protein_ratio, 1)
    protein_calories = protein_g * 4  # 4 kcal per gram

    # Fat: 25-30% of total calories (essential for hormones)
    fat_percentage = 0.28
    fat_calories = target_calories * fat_percentage
    fat_g = round(fat_calories / 9, 1)  # 9 kcal per gram

    # Carbs: Remaining calories
    carbs_calories = target_calories - protein_calories - fat_calories
    carbs_g = round(carbs_calories / 4, 1)  # 4 kcal per gram

    return {
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g
    }
```

---

### 6.5 Micronutrient Calculation

**Based on Gender & Age (No Pregnancy/Lactation!):**

```python
def calculate_micronutrients(gender: str, age: int) -> dict:
    """
    Calculate micronutrient RDV based on gender and age

    Returns:
        {
            "iron_mg": float,
            "calcium_mg": float,
            "vitamin_a_mcg": float,
            "zinc_mg": float
        }
    """
    if gender == "male":
        micros = {
            "iron_mg": 8,
            "calcium_mg": 1200 if age >= 51 else 1000,  # Bone health for 51+
            "vitamin_a_mcg": 900,
            "zinc_mg": 11
        }
    else:  # female
        micros = {
            "iron_mg": 8 if age >= 51 else 18,  # Lower post-menopause
            "calcium_mg": 1200 if age >= 51 else 1000,
            "vitamin_a_mcg": 700,
            "zinc_mg": 8
        }

    return micros
```

**Key Changes:**
- ❌ NO pregnancy adjustments (+300 kcal, +iron to 27mg)
- ❌ NO lactation adjustments (+500 kcal, +vitamin A to 1300mcg)
- ✅ Age-based calcium boost (51+)
- ✅ Age-based iron reduction for females (51+)

---

### 6.6 Weight Loss/Gain Projection

**Formula:**

```python
def calculate_weight_projection(
    current_weight: float,
    target_weight: float,
    daily_deficit: float
) -> dict:
    """
    Calculate time to reach goal weight

    Args:
        current_weight: Current weight in kg
        target_weight: Goal weight in kg
        daily_deficit: Calorie deficit/surplus per day (positive for loss, negative for gain)

    Returns:
        {
            "current_weight": float,
            "target_weight": float,
            "deficit_per_day": float,
            "estimated_loss_per_week": float (or gain if negative),
            "estimated_weeks_to_goal": int
        }
    """
    # Science: 1kg of body fat = ~7700 calories
    calories_per_kg = 7700

    # Weekly deficit
    weekly_deficit = daily_deficit * 7

    # Weight change per week (kg)
    weight_change_per_week = weekly_deficit / calories_per_kg

    # Total weight to change
    weight_to_change = abs(target_weight - current_weight)

    # Weeks to goal
    if weight_change_per_week > 0:
        weeks_to_goal = int(weight_to_change / weight_change_per_week)
    else:
        weeks_to_goal = None  # Maintenance - no weight change expected

    return {
        "current_weight": current_weight,
        "target_weight": target_weight,
        "deficit_per_day": daily_deficit,
        "estimated_loss_per_week": round(weight_change_per_week, 2),
        "estimated_weeks_to_goal": weeks_to_goal
    }
```

**Examples:**
```
Example 1: Weight Loss
Current: 75kg, Target: 70kg, Deficit: 500 kcal/day
Weekly deficit: 500 × 7 = 3,500 kcal
Loss per week: 3,500 / 7,700 = 0.45 kg/week
Weeks to goal: 5kg / 0.45 = 11 weeks

Example 2: Muscle Gain
Current: 65kg, Target: 72kg, Surplus: 300 kcal/day
Weekly surplus: 300 × 7 = 2,100 kcal
Gain per week: 2,100 / 7,700 = 0.27 kg/week
Weeks to goal: 7kg / 0.27 = 26 weeks
```

---

## 7. User Experience Flow

### 7.1 New User Journey

```
Step 1: Discovery
User discovers KAI → Clicks "Sign Up"

Step 2: Quick Signup (Required Fields Only)
Form:
  Email: [___________]
  Name: [___________]
  Gender: ( ) Male  ( ) Female
  Age: [___]

[Sign Up] button

Step 3: Welcome Screen
"Welcome, John! 🎉
Let's log your first meal and see KAI in action!"

[Log First Meal] [Complete Profile for Better Results]

Step 4a: User Chooses "Log First Meal"
→ Meal logging flow
→ Vision agent detects food
→ Basic coaching (generic RDV)
→ Banner: "⚠️ Complete your profile for personalized guidance!"

Step 4b: User Chooses "Complete Profile"
Form:
  Weight: [___] kg
  Height: [___] cm
  Activity Level: [Dropdown]
  Health Goal: [Dropdown]
  Target Weight (optional): [___] kg

[Calculate My Plan] button

Step 5: Personalization Results
"Based on your profile:
- Your daily calorie target: 2,146 kcal
- Expected weight loss: 0.5 kg/week
- Time to reach 70kg: ~10 weeks

Ready to start logging meals with your personalized targets?"

[Let's Go!]

Step 6: Enhanced Meal Logging
→ All future meals use personalized RDV
→ Progress tracked against goal
→ Weekly updates on progress
```

---

### 7.2 Existing User Migration

**Scenario**: User signed up with old system (only has email, name, gender, age)

```
Day 1: User logs in
→ Dashboard shows banner: "⚠️ Complete your profile for personalized nutrition guidance!"
→ Click "Complete Now"

Day 1: Profile Completion
→ Fills weight, height, activity, goals
→ Sees personalized targets
→ "Your targets have been updated! All future meal coaching will use these."

Day 2+: Enhanced Experience
→ Meals analyzed against new RDV
→ Progress tracked
→ Weekly trends more accurate
```

**Backwards Compatibility:**
- Users with `is_pregnant=1` or `is_lactating=1` in database: Values remain but don't affect calculations
- They can update their profile anytime to use new system

---

## 8. Implementation Plan

### Phase 1: Database & Core Logic (Day 1)
```
1.1 Update database schema
    - Add new fields to user_health table
    - Run migration SQL
    - Test field creation

1.2 Implement calculation functions
    - calculate_bmr()
    - calculate_tdee()
    - calculate_goal_adjusted_calories()
    - calculate_macronutrients()
    - calculate_micronutrients()
    - calculate_weight_projection()

1.3 Create comprehensive RDV calculator
    - calculate_user_rdv_v2() in nutrition_rdv.py
    - Unit tests for all edge cases
```

### Phase 2: API Endpoints (Day 2)
```
2.1 Update signup endpoint
    - Remove defaults for name, gender, age
    - Add validation
    - Test error cases

2.2 Create health profile endpoint
    - PUT /api/v1/users/health-profile
    - Request validation
    - Response formatting
    - Error handling

2.3 Update profile endpoint
    - Add profile_complete flag
    - Add missing_fields list
    - Test completeness logic
```

### Phase 3: Integration (Day 3)
```
3.1 Update coaching agent
    - Use calculate_user_rdv_v2()
    - Remove pregnancy/lactation references
    - Add goal-based messaging
    - Test with complete vs incomplete profiles

3.2 Update user operations
    - Update get_user_health_profile()
    - Add helper functions for completeness check

3.3 Update stats calculations
    - Ensure weekly averages use new RDV
```

### Phase 4: Testing & Debugging (Day 4)
```
4.1 Unit tests
    - Test all calculation functions
    - Test edge cases (very low/high values)

4.2 Integration tests
    - Full signup → profile → meal → coaching flow
    - Test incomplete profile flow

4.3 Edge case testing
    - Invalid inputs
    - Missing fields
    - Extreme values
```

### Phase 5: Documentation & Deployment (Day 5)
```
5.1 Update API documentation
5.2 Create migration guide for existing users
5.3 Deploy to production
5.4 Monitor for errors
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**File**: `tests/test_nutrition_rdv.py`

```python
def test_calculate_bmr_male():
    # 32-year-old male, 75kg, 178cm
    bmr = calculate_bmr(75, 178, 32, "male")
    assert abs(bmr - 1707.5) < 1  # Allow 1 kcal variance

def test_calculate_bmr_female():
    # 28-year-old female, 70kg, 165cm
    bmr = calculate_bmr(70, 165, 28, "female")
    assert abs(bmr - 1430.25) < 1

def test_calculate_tdee_moderate():
    bmr = 1430.25
    tdee = calculate_tdee(bmr, "moderate")
    assert abs(tdee - 2216.89) < 1

def test_goal_adjustment_weight_loss():
    tdee = 2217
    target = calculate_goal_adjusted_calories(tdee, "lose_weight")
    assert target == 1717

def test_weight_projection():
    projection = calculate_weight_projection(75, 70, 500)
    assert projection["estimated_weeks_to_goal"] == 10
```

### 9.2 Integration Tests

**Test Cases:**

1. **Complete Flow - Weight Loss**
   - Signup → Complete profile (lose_weight) → Log meal → Check coaching
   - Verify: RDV uses BMR/TDEE, coaching mentions goal

2. **Incomplete Profile Flow**
   - Signup → Skip profile → Log meal
   - Verify: Generic RDV used, banner shown

3. **Profile Completion Mid-Journey**
   - Signup → Log 3 meals → Complete profile → Log meal
   - Verify: RDV switches from generic to personalized

4. **Custom Calorie Goal**
   - Complete profile with custom_calorie_goal
   - Verify: active_calorie_goal uses custom, not calculated

### 9.3 Edge Cases

```
- Very low weight (30kg) - should work
- Very high weight (200kg) - should work
- Age 13 (minimum) - should work
- Age 120 (maximum) - should work
- Very tall (250cm) - should work
- Very short (100cm) - should work
- Negative deficit (surplus for muscle gain) - should work
- Zero deficit (maintenance) - should work
- Missing target_weight for weight_loss goal - should work (optional)
- Dangerous custom calorie (800 kcal) - should warn but allow
```

---

## 10. Rollback Plan

### If Critical Issues Arise

**Scenario**: New RDV calculations cause errors or incorrect results

**Rollback Steps:**

1. **Immediate**: Revert coaching agent to use old `calculate_user_rdv()` function
2. **Database**: New fields remain but aren't used (no data loss)
3. **API**: Disable health profile endpoint temporarily
4. **Users**: Existing functionality unaffected (old RDV still works)

**Rollback Command:**
```bash
# Git revert to previous commit
git revert HEAD
git push origin main

# Or restore specific files
git checkout HEAD~1 -- kai/utils/nutrition_rdv.py
git checkout HEAD~1 -- kai/agents/coaching_agent.py
```

**Recovery Time**: < 5 minutes (simple file revert)

---

## Appendices

### A. Formula References

1. **Mifflin-St Jeor Equation**
   Source: Mifflin et al. (1990), American Journal of Clinical Nutrition

2. **Activity Multipliers**
   Source: Ainsworth et al. (2011), Compendium of Physical Activities

3. **Weight Loss Science**
   Source: 1kg fat = 7,700 kcal (widely accepted in nutrition science)

### B. Validation Rules Summary

| Field | Min | Max | Type | Required |
|-------|-----|-----|------|----------|
| weight_kg | 30 | 300 | float | Yes (for full) |
| height_cm | 100 | 250 | float | Yes (for full) |
| age | 13 | 120 | int | Yes |
| custom_calorie_goal | 1200/1500* | 5000 | float | No |
| target_weight_kg | 30 | 300 | float | No |

*Minimum 1200 for female, 1500 for male

### C. Error Codes

| Code | Message | Action |
|------|---------|--------|
| PROFILE_INCOMPLETE | Profile missing required fields | Show which fields needed |
| INVALID_ACTIVITY | Invalid activity level | Show valid options |
| INVALID_GOAL | Invalid health goal | Show valid options |
| DANGEROUS_CALORIES | Custom calorie goal too low | Warn but allow |
| INVALID_RANGE | Value out of acceptable range | Show min/max |

---

## Sign-Off

**Document prepared by**: Claude (KAI AI Engineer)
**Review required by**: Human Developer
**Status**: Ready for Implementation
**Estimated implementation time**: 4-5 days
**Risk level**: Low (backwards compatible, non-breaking changes)

---

**END OF DESIGN DOCUMENT**
