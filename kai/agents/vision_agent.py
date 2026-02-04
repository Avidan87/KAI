"""
Vision Agent - Nigerian Food Detection and Analysis

Uses GPT-4o vision capabilities to detect and analyze Nigerian foods from images.
Specialized for recognizing 50+ Nigerian dishes with cultural context.

Uses OpenAI Agents SDK for orchestrator consistency.
"""

import base64
import io
import json
import logging
from typing import Dict, Any, Optional, List, Annotated
from datetime import datetime
from openai import AsyncOpenAI
from agents import Agent, function_tool
from dotenv import load_dotenv
import os

from kai.models import VisionResult, DetectedFood
from kai.mcp_servers.depth_estimation_client import get_portion_estimate, get_portions_batch
from kai.agents.sam_segmentation import SAMFoodSegmenter
import numpy as np
from PIL import Image

load_dotenv()
logger = logging.getLogger(__name__)


# Meal-type aware portion limits (grams)
# Based on Nigerian portion research and nutritional guidelines
MEAL_PORTION_LIMITS = {
    "breakfast": {"max_total": 400.0, "max_per_food": 200.0},
    "lunch": {"max_total": 600.0, "max_per_food": 300.0},
    "dinner": {"max_total": 600.0, "max_per_food": 300.0},
    "snack": {"max_total": 200.0, "max_per_food": 150.0},
    "default": {"max_total": 500.0, "max_per_food": 250.0},  # Conservative default
}


def get_portion_limits(meal_type: Optional[str]) -> dict:
    """Get portion limits based on meal type."""
    if meal_type and meal_type.lower() in MEAL_PORTION_LIMITS:
        return MEAL_PORTION_LIMITS[meal_type.lower()]
    return MEAL_PORTION_LIMITS["default"]


class VisionAgent:
    """
    Vision Agent for detecting Nigerian foods from meal images.

    Uses OpenAI Agents SDK with vision tools for orchestrator integration.

    Capabilities:
    - Detect multiple Nigerian foods in a single image
    - Estimate portion sizes (grams)
    - Identify cooking methods and visible ingredients
    - Provide confidence scores for each detection
    - Handle various image qualities and lighting conditions
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize Vision Agent with GPT-4o and OpenAI Agents SDK."""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-5"  # Vision-capable model
        self.max_image_size = 2048  # Max dimension for processing

        # Nigerian food knowledge (from our enriched database)
        self.known_foods = [
            "Jollof Rice", "Pounded Yam", "Fufu", "Suya", "Moi Moi",
            "Pepper Soup", "Akara", "Efo Riro", "Ewa Agoyin", "Okra Soup",
            "Ogbono Soup", "Rice and Stew", "Beans and Stew", "Eba",
            "Fried Plantain", "Egusi Soup", "Amala", "Fried Rice"
        ]

        # Setup agent with vision tools
        self._setup_agent()

    def _setup_agent(self):
        """
        Setup OpenAI Agent with Nigerian food detection tools using @function_tool decorator.
        """
        # Create agent instructions
        agent_instructions = f"""You are KAI's Vision Agent, an expert in Nigerian food recognition.

Your mission is to accurately detect and identify Nigerian foods from meal images to help Nigerians track their nutrition intake.

**Your Expertise:**
- 50+ Nigerian dishes including: {', '.join(self.known_foods[:10])}... and more
- Portion size estimation using typical Nigerian serving sizes
- Ingredient identification from visual appearance
- Cooking method recognition
- Cultural context and regional variations

**Your Approach:**
1. Carefully analyze meal images for all visible Nigerian foods
2. Estimate portions based on typical Nigerian serving sizes
3. Assign confidence scores based on visual clarity
4. Request clarification when uncertain
5. Provide culturally relevant context

**Detection Priorities:**
- Accuracy over speed - Nigerians' health depends on correct tracking
- Cultural awareness - recognize regional variations and local names
- Practical portions - use real-world Nigerian serving sizes
- Clear communication - explain what you see and why

Use the analyze_nigerian_food_image tool to process images and return structured detection results."""

        # Create tool using @function_tool decorator
        analyze_food_tool = self._create_analyze_food_tool()

        self.agent = Agent(
            name="KAI Vision Agent",
            instructions=agent_instructions,
            model=self.model,
            tools=[analyze_food_tool]
        )

        logger.info("✓ Vision Agent initialized with @function_tool decorator")

    def _create_analyze_food_tool(self):
        """Create the analyze_nigerian_food_image tool with @function_tool decorator."""
        client = self.client
        model = self.model
        known_foods = self.known_foods

        @function_tool
        async def analyze_nigerian_food_image(
            image_base64: Annotated[str, "Base64 encoded meal image"],
            user_description: Annotated[Optional[str], "Optional user description of the meal"] = None,
            meal_type: Annotated[Optional[str], "Type of meal (breakfast, lunch, dinner, snack)"] = None
        ) -> str:
            """
            Analyze a meal image to detect and identify Nigerian foods.
            Returns detailed information about detected dishes including names, portions,
            ingredients, cooking methods, and confidence scores.
            """
            logger.info(f"🔧 Tool: analyze_nigerian_food_image (meal_type={meal_type})")

            # Build analysis prompt
            meal_context = f"This is a {meal_type} meal. " if meal_type else ""

            prompt = f"""You are an expert Nigerian food recognition AI specialized in identifying Nigerian dishes.

{meal_context}Analyze this meal image and identify ALL Nigerian foods present.

**Known Nigerian Foods to Look For:**
{', '.join(known_foods[:20])}... and 30+ more dishes

**Your Task:**
1. Identify each distinct Nigerian food in the image
2. Estimate portion size in grams (typical Nigerian portions)
3. Identify visible ingredients and cooking method
4. Assign confidence score (0.0-1.0) for each food
5. Note the overall meal context
6. Flag if you need clarification from the user

**Typical Portion Reference:**
- 1 plate of rice/stew = ~250g
- 1 wrap of fufu/eba = ~200g
- 1 piece of meat = ~80-100g
- 1 bowl of soup = ~200-300g
- Small side dishes = ~50-100g

**Return ONLY valid JSON (no markdown):**
{{
  "detected_foods": [
    {{
      "name": "Food name in English",
      "nigerian_name": "Nigerian/local name if different",
      "confidence": 0.0-1.0,
      "estimated_portion": "descriptive size",
      "estimated_grams": number,
      "visible_ingredients": ["ingredient1", "ingredient2"],
      "cooking_method": "how it appears to be cooked"
    }}
  ],
  "meal_context": "Overall description of the meal",
  "cooking_method": "Primary cooking method observed",
  "overall_confidence": 0.0-1.0,
  "needs_clarification": true/false,
  "clarification_questions": ["question1", "question2"]
}}

**Important Detection Rules:**
- If you see rice with red/orange sauce → likely "Jollof Rice" or "Fried Rice"
- White pounded starchy food → "Pounded Yam", "Fufu", or "Eba"
- Dark green leafy soup → "Efo Riro", "Edikang Ikong", or vegetable soup
- Thick draw soup → "Ogbono Soup" or "Okra Soup"
- Fried bean cakes → "Akara"
- Grilled spicy meat on stick → "Suya"
- Yellow/brown fried plantain slices → "Fried Plantain" (Dodo)

**Confidence Guidelines:**
- 0.9-1.0: Very certain (clear view, familiar dish)
- 0.7-0.9: Confident (good visibility, recognizable)
- 0.5-0.7: Moderate (some uncertainty, partial view)
- 0.3-0.5: Low (unclear, could be multiple dishes)
- <0.3: Very uncertain (needs clarification)

Be specific about Nigerian dishes, not generic descriptions!"""

            # Call GPT-4o Vision API
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Analyze this Nigerian meal image. {user_description or ''}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=1500
            )

            # Log token usage
            usage = response.usage
            logger.info(
                f"Vision Agent: {usage.total_tokens} tokens "
                f"(~${usage.total_tokens * 2.5 / 1000:.4f})"
            )

            return response.choices[0].message.content

        return analyze_nigerian_food_image

    async def analyze_image(
        self,
        image_base64: str,
        image_url: Optional[str] = None,
        user_description: Optional[str] = None,
        meal_type: Optional[str] = None
    ) -> VisionResult:
        """
        Analyze meal image and detect Nigerian foods.
        """
        try:
            logger.info("🔍 Starting Nigerian food vision analysis (SDK mode)")

            # Call the tool function directly (SDK pattern)
            result_json = await self._tool_analyze_nigerian_food_image(
                image_base64=image_base64,
                user_description=user_description,
                meal_type=meal_type
            )

            # Parse tool result
            result_dict = json.loads(result_json)

            depth_estimation_used = False
            portion_grams = None

            # (We need detected_foods info for portion logic)
            detected_foods = result_dict.get("detected_foods", [])
            if (image_url or image_base64) and detected_foods:
                logger.info("📏 Starting per-food portion estimation with SAM segmentation")

                # Decode image for SAM segmentation
                img_array = None
                if image_base64:
                    img_bytes = base64.b64decode(image_base64)
                    img_array = np.array(Image.open(io.BytesIO(img_bytes)))
                elif image_url:
                    # Fetch image from URL
                    import httpx
                    response = httpx.get(image_url, timeout=30.0)
                    img_array = np.array(Image.open(io.BytesIO(response.content)))

                # Use SAM 2 for pixel-perfect food segmentation
                # OPTIMIZATION: Use SAM 2 for 2+ foods (skip for single dishes)
                # Single dishes don't need segmentation (portion = whole plate)
                # 2+ foods benefit from accurate segmentation (different portion sizes)
                use_sam = len(detected_foods) >= 2 and img_array is not None

                if use_sam:
                    try:
                        logger.info("🔍 Using SAM 2 for pixel-perfect food segmentation")

                        # Extract food names for segmentation
                        food_names = [food.get("name") for food in detected_foods]

                        # Initialize SAM segmenter
                        sam_segmenter = SAMFoodSegmenter(device="cpu", model_size="small")

                        # Get pixel-perfect masks for each food
                        food_masks = sam_segmenter.segment_foods(
                            image=img_array,
                            food_names=food_names,
                            use_automatic_segmentation=True
                        )
                        sam_segmenter.unload_model()

                        logger.info(f"✓ SAM 2 generated {len(food_masks)} pixel masks for {len(detected_foods)} foods")

                        # Convert masks to bboxes for batch depth estimation
                        # (MCP server currently expects bboxes, we'll update it later to accept masks)
                        # Use meal-type aware portion limits
                        portion_limits = get_portion_limits(meal_type)
                        MAX_REASONABLE_PORTION_PER_FOOD = portion_limits["max_per_food"]
                        img_height, img_width = img_array.shape[:2]

                        bboxes_for_batch = []
                        food_types_for_batch = []
                        food_to_batch_index = {}

                        for idx, (food_name, mask) in enumerate(food_masks.items()):
                            # Convert pixel mask to bounding box (tight fit around masked region)
                            ys, xs = np.where(mask)

                            if len(xs) > 0 and len(ys) > 0:
                                x1, x2 = int(np.min(xs)), int(np.max(xs))
                                y1, y2 = int(np.min(ys)), int(np.max(ys))

                                bbox_area = (x2 - x1) * (y2 - y1)
                                mask_area = np.sum(mask)
                                coverage = mask_area / bbox_area if bbox_area > 0 else 0

                                logger.info(
                                    f"✓ {food_name}: mask covers {mask_area} pixels "
                                    f"({mask_area / (img_width * img_height):.1%} of image, "
                                    f"{coverage:.1%} fill ratio in bbox)"
                                )

                                food_to_batch_index[idx] = len(bboxes_for_batch)
                                bboxes_for_batch.append((x1, y1, x2, y2))
                                food_types_for_batch.append(food_name)
                            else:
                                # Empty mask - use default portion
                                logger.warning(f"⚠️ {food_name}: empty mask, will use default portion (150g)")
                                food_to_batch_index[idx] = None

                        # 🚀 BATCH PROCESSING: Single API call for all foods!
                        logger.info(f"🚀 Using BATCH API for {len(bboxes_for_batch)} foods (single depth estimation run)")

                        try:
                            batch_results = await get_portions_batch(
                                image_base64=image_base64,
                                bboxes=bboxes_for_batch,
                                food_types=food_types_for_batch,
                                reference_object="plate"
                            )

                            # Assign results to foods
                            for idx, food in enumerate(detected_foods):
                                batch_idx = food_to_batch_index.get(idx)

                                if batch_idx is not None:
                                    # Food has a mask - get result from batch
                                    result = batch_results[batch_idx]
                                    portion_grams = result.get("portion_grams", 200.0)

                                    # Cap at reasonable max
                                    if portion_grams > MAX_REASONABLE_PORTION_PER_FOOD:
                                        logger.warning(f"⚠️ {food.get('name')}: {portion_grams}g → capped at {MAX_REASONABLE_PORTION_PER_FOOD}g")
                                        portion_grams = MAX_REASONABLE_PORTION_PER_FOOD

                                    food["estimated_grams"] = portion_grams
                                    logger.info(
                                        f"✓ {food.get('name')}: {portion_grams:.1f}g "
                                        f"(confidence: {result.get('confidence', 0):.2f})"
                                    )
                                else:
                                    # Food has no mask - use default portion
                                    food["estimated_grams"] = 150.0
                                    logger.info(f"✓ {food.get('name')}: 150.0g (default, no mask)")

                        except Exception as e:
                            logger.error(f"❌ Batch estimation failed: {e}, using defaults")
                            # Fallback to defaults
                            for food in detected_foods:
                                food["estimated_grams"] = 200.0

                        # Check total meal portion and scale down if unrealistic
                        # Use meal-type aware limits (breakfast ~400g, lunch/dinner ~600g)
                        total_estimated = sum(food["estimated_grams"] for food in detected_foods)
                        MAX_REASONABLE_MEAL = portion_limits["max_total"]

                        if total_estimated > MAX_REASONABLE_MEAL:
                            scale_factor = MAX_REASONABLE_MEAL / total_estimated
                            logger.warning(
                                f"⚠️ Total meal {total_estimated:.0f}g exceeds realistic max ({MAX_REASONABLE_MEAL}g). "
                                f"Scaling all portions down by {scale_factor:.2f}x to prevent over-estimation."
                            )
                            for food in detected_foods:
                                original = food["estimated_grams"]
                                food["estimated_grams"] = original * scale_factor
                                logger.info(f"   📉 {food.get('name')}: {original:.0f}g → {food['estimated_grams']:.0f}g")
                        else:
                            logger.info(f"✅ Total meal portion {total_estimated:.0f}g is reasonable")

                        depth_estimation_used = True

                    except Exception as e:
                        logger.error(f"❌ SAM 2 segmentation failed: {e}, falling back to division method")
                        use_sam = False

                # Fallback: divide total portion evenly
                if not use_sam:
                    try:
                        portion = await get_portion_estimate(
                            image_url=image_url,
                            image_base64=image_base64,
                            reference_object="plate"
                        )
                        portion_grams = portion.get("portion_grams")

                        # Use meal-type aware limits (consistent with SAM path)
                        portion_limits = get_portion_limits(meal_type)
                        MAX_REASONABLE_MEAL = portion_limits["max_total"]
                        if portion_grams and portion_grams > 0:
                            if portion_grams > MAX_REASONABLE_MEAL:
                                logger.warning(f"⚠️ Total portion {portion_grams}g exceeds max ({MAX_REASONABLE_MEAL}g) for {meal_type or 'unknown'} meal, capping")
                                portion_grams = MAX_REASONABLE_MEAL

                            # Split evenly among foods
                            num_foods = len(detected_foods)
                            portion_per_food = portion_grams / num_foods if num_foods > 0 else portion_grams

                            logger.info(f"✅ Fallback: {portion_grams}g total → {portion_per_food:.1f}g per food")
                            depth_estimation_used = True

                            for food in detected_foods:
                                food["estimated_grams"] = portion_per_food
                        else:
                            logger.warning("⚠️ Depth estimation MCP returned invalid portion")
                    except Exception as e:
                        logger.error(f"❌ Depth estimation fallback failed: {e}")
                        depth_estimation_used = False
            # Now, build the VisionResult from result_dict and correct depth_estimation_used
            vision_result = self._parse_detection_result(result_dict, depth_estimation_used=depth_estimation_used)
            return vision_result
        except Exception as ex:
            logger.exception(f"VisionAgent.analyze_image failed: {str(ex)}")
            raise

    async def _tool_analyze_nigerian_food_image(
        self,
        image_base64: str,
        user_description: Optional[str] = None,
        meal_type: Optional[str] = None
    ) -> str:
        """
        Tool function for Nigerian food image analysis.

        This is the actual implementation of the analyze_nigerian_food_image tool.
        It wraps the GPT-4o Vision API call and returns structured JSON.

        Args:
            image_base64: Base64 encoded meal image
            user_description: Optional user description
            meal_type: Type of meal

        Returns:
            JSON string with detection results
        """
        logger.info(f"🔧 Tool: analyze_nigerian_food_image (meal_type={meal_type})")

        # Build analysis prompt
        prompt = self._build_detection_prompt(user_description, meal_type)

        # Call GPT-4o Vision API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this Nigerian meal image. {user_description or ''}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"  # High detail for food recognition
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2,  # Low temperature for consistent detection
            max_completion_tokens=1500
        )

        # Log token usage
        usage = response.usage
        logger.info(
            f"Vision Agent: {usage.total_tokens} tokens "
            f"(~${usage.total_tokens * 2.5 / 1000:.4f})"
        )

        # Return raw JSON for tool
        return response.choices[0].message.content

    def _build_detection_prompt(
        self,
        user_description: Optional[str],
        meal_type: Optional[str]
    ) -> str:
        """
        Build detection prompt for GPT-4o Vision.

        Args:
            user_description: User's description
            meal_type: Type of meal

        Returns:
            Formatted prompt for Nigerian food detection
        """
        meal_context = f"This is a {meal_type} meal. " if meal_type else ""

        return f"""You are an expert Nigerian food recognition AI specialized in identifying Nigerian dishes.

{meal_context}Analyze this meal image and identify ALL Nigerian foods present.

**Known Nigerian Foods to Look For:**
{', '.join(self.known_foods[:20])}... and 30+ more dishes

**Your Task:**
1. Identify each distinct Nigerian food in the image
2. Estimate portion size in grams (typical Nigerian portions)
3. Identify visible ingredients and cooking method
4. Assign confidence score (0.0-1.0) for each food
5. Note the overall meal context
6. Flag if you need clarification from the user

**Typical Portion Reference:**
- 1 plate of rice/stew = ~250g
- 1 wrap of fufu/eba = ~200g
- 1 piece of meat = ~80-100g
- 1 bowl of soup = ~200-300g
- Small side dishes = ~50-100g

**Return ONLY valid JSON (no markdown):**
{{
  "detected_foods": [
    {{
      "name": "Food name in English",
      "nigerian_name": "Nigerian/local name if different",
      "confidence": 0.0-1.0,
      "estimated_portion": "descriptive size",
      "estimated_grams": number,
      "visible_ingredients": ["ingredient1", "ingredient2"],
      "cooking_method": "how it appears to be cooked"
    }}
  ],
  "meal_context": "Overall description of the meal",
  "cooking_method": "Primary cooking method observed",
  "overall_confidence": 0.0-1.0,
  "needs_clarification": true/false,
  "clarification_questions": ["question1", "question2"]
}}

**Important Detection Rules:**
- If you see rice with red/orange sauce → likely "Jollof Rice" or "Fried Rice"
- White pounded starchy food → "Pounded Yam", "Fufu", or "Eba"
- Dark green leafy soup → "Efo Riro", "Edikang Ikong", or vegetable soup
- Thick draw soup → "Ogbono Soup" or "Okra Soup"
- Fried bean cakes → "Akara"
- Grilled spicy meat on stick → "Suya"
- Yellow/brown fried plantain slices → "Fried Plantain" (Dodo)

**Confidence Guidelines:**
- 0.9-1.0: Very certain (clear view, familiar dish)
- 0.7-0.9: Confident (good visibility, recognizable)
- 0.5-0.7: Moderate (some uncertainty, partial view)
- 0.3-0.5: Low (unclear, could be multiple dishes)
- <0.3: Very uncertain (needs clarification)

Be specific about Nigerian dishes, not generic descriptions!"""

    def _parse_detection_result(self, result_dict: Dict[str, Any], depth_estimation_used: bool = False) -> VisionResult:
        """
        Parse JSON result into VisionResult model.

        Args:
            result_dict: Parsed JSON from GPT-4o
            depth_estimation_used: Boolean indicating if depth estimation was used for portion estimation

        Returns:
            Structured VisionResult
        """
        detected_foods = []

        for food_data in result_dict.get("detected_foods", []):
            detected_food = DetectedFood(
                name=food_data.get("name", "Unknown Food"),
                nigerian_name=food_data.get("nigerian_name"),
                confidence=food_data.get("confidence", 0.5),
                estimated_portion=food_data.get("estimated_portion", "Unknown"),
                estimated_grams=food_data.get("estimated_grams", 0.0),
                visible_ingredients=food_data.get("visible_ingredients", []),
                cooking_method=food_data.get("cooking_method")
            )
            detected_foods.append(detected_food)

        return VisionResult(
            detected_foods=detected_foods,
            meal_context=result_dict.get("meal_context", "Nigerian meal"),
            cooking_method=result_dict.get("cooking_method"),
            overall_confidence=result_dict.get("overall_confidence", 0.7),
            needs_clarification=result_dict.get("needs_clarification", False),
            clarification_questions=result_dict.get("clarification_questions", []),
            depth_estimation_used=depth_estimation_used
        )

    def validate_image_quality(self, image_base64: str) -> Dict[str, Any]:
        """
        Quick validation of image quality for food detection.

        Args:
            image_base64: Base64 encoded image

        Returns:
            Validation results
        """
        try:
            # Decode to check basic properties
            image_data = base64.b64decode(image_base64)

            return {
                "is_valid": True,
                "size_bytes": len(image_data),
                "message": "Image is suitable for analysis"
            }
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return {
                "is_valid": False,
                "message": f"Invalid image format: {str(e)}"
            }


# ============================================================================
# Convenience Functions
# ============================================================================

def detect_nigerian_foods(
    image_base64: str,
    user_description: Optional[str] = None,
    meal_type: Optional[str] = None,
    openai_api_key: Optional[str] = None
) -> VisionResult:
    """
    Convenience function for single-image food detection.

    Args:
        image_base64: Base64 encoded meal image
        user_description: Optional description from user
        meal_type: Type of meal
        openai_api_key: Optional API key override

    Returns:
        VisionResult with detected foods
    """
    import asyncio
    agent = VisionAgent(openai_api_key=openai_api_key)
    return asyncio.run(agent.analyze_image(image_base64, user_description, meal_type))


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_vision_agent():
        """Test Vision Agent with sample scenarios."""

        print("\n" + "="*60)
        print("Testing Vision Agent - Nigerian Food Detection")
        print("="*60 + "\n")

        agent = VisionAgent()

        # Note: Actual testing requires real images
        print("Vision Agent initialized successfully!")
        print(f"Model: {agent.model}")
        print(f"Known foods: {len(agent.known_foods)} Nigerian dishes")

        print("\n" + "="*60)
        print("Vision Agent Ready for Food Detection!")
        print("="*60 + "\n")

    asyncio.run(test_vision_agent())