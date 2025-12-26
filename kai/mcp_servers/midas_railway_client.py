"""
MiDaS Railway MCP Client

This module provides a client to call the hosted MiDaS MCP server on Railway
for depth estimation and portion size calculation from food images.

Instead of running MiDaS locally, this client makes HTTP requests to the
Railway-hosted MCP server endpoint using MIDAS_MCP_URL from .env
"""

import httpx
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class MiDaSRailwayClient:
    """Client for calling MiDaS MCP server hosted on Railway"""

    def __init__(self, railway_url: Optional[str] = None):
        """
        Initialize MiDaS Railway client.

        Args:
            railway_url: URL of hosted MiDaS MCP server on Railway
                        If None, reads from MIDAS_MCP_URL env variable
        """
        self.railway_url = railway_url or os.getenv("MIDAS_MCP_URL")

        if not self.railway_url:
            raise ValueError(
                "MiDaS Railway URL not provided. Set MIDAS_MCP_URL environment variable "
                "or pass railway_url parameter."
            )

        # Remove trailing slash
        self.railway_url = self.railway_url.rstrip('/')

        # Initialize async HTTP client with extended timeout for depth estimation
        # MiDaS depth estimation can take 60-90 seconds for complex images
        self.client = httpx.AsyncClient(timeout=120.0)

    async def estimate_depth(
        self,
        image_url: str,
        model_type: str = "DPT_Large"
    ) -> Dict[str, Any]:
        """
        Estimate depth map from food image.

        Args:
            image_url: URL of the food image
            model_type: MiDaS model type (DPT_Large, DPT_Hybrid, MiDaS_small)

        Returns:
            Dict with depth map data and metadata
        """
        endpoint = f"{self.railway_url}/api/v1/depth/estimate"

        payload = {
            "image_url": image_url,
            "model_type": model_type
        }

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"MiDaS API error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to MiDaS Railway server: {e}")

    async def estimate_portion_size(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        reference_object: Optional[str] = None,
        reference_size_cm: Optional[float] = None,
        food_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate portion size using depth estimation.

        Args:
            image_url: URL of the food image (optional if image_base64 provided)
            image_base64: Base64 encoded image (optional if image_url provided)
            reference_object: Type of reference object (e.g., "plate", "spoon", "hand")
            reference_size_cm: Known size of reference object in cm
            food_type: Type of food for density calculation (e.g., "Jollof Rice")

        Returns:
            Dict with portion estimate in grams/ml and confidence score
        """
        if not image_url and not image_base64:
            raise ValueError("Either image_url or image_base64 must be provided")

        endpoint = f"{self.railway_url}/api/v1/portion/estimate"

        payload = {
            "reference_object": reference_object,
            "reference_size_cm": reference_size_cm,
            "food_type": food_type
        }

        # Add either URL or base64 to payload
        if image_url:
            payload["image_url"] = image_url
        if image_base64:
            payload["image_base64"] = image_base64

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"MiDaS API error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to MiDaS Railway server: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if MiDaS Railway server is healthy.

        Returns:
            Dict with health status
        """
        endpoint = f"{self.railway_url}/health"

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"MiDaS health check failed: {e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"Cannot reach MiDaS Railway server: {e}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for use in agents

async def get_portion_estimate(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    reference_object: Optional[str] = None,
    food_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get portion estimate from MiDaS Railway.

    This function can be used directly in OpenAI Agents SDK tools.

    Args:
        image_url: URL of food image (optional if image_base64 provided)
        image_base64: Base64 encoded image (optional if image_url provided)
        reference_object: Detected reference object (plate, spoon, hand, etc.)
        food_type: Type of food for density calculation (e.g., "Jollof Rice")

    Returns:
        {
            "portion_grams": 250.0,
            "confidence": 0.78,
            "reference_used": "plate",
            "volume_ml": 200.0
        }
    """
    if not image_url and not image_base64:
        return {
            "portion_grams": 200.0,  # Default 200g
            "confidence": 0.5,
            "error": "No image provided (neither URL nor base64)",
            "fallback_used": True,
            "note": "Using default portion estimate - no image provided"
        }

    # Common Nigerian reference sizes
    REFERENCE_SIZES = {
        "plate": 24.0,  # Standard Nigerian plate diameter in cm
        "spoon": 15.0,  # Table spoon length
        "hand": 18.0,   # Average hand width
        "fork": 18.0,
        "cup": 8.0      # Cup diameter
    }

    reference_size = REFERENCE_SIZES.get(reference_object.lower()) if reference_object else None

    async with MiDaSRailwayClient() as client:
        # Skip health check - if server is down, the API call will fail anyway
        # Health check adds unnecessary latency and potential DNS timeout issues

        # Estimate portion
        try:
            result = await client.estimate_portion_size(
                image_url=image_url,
                image_base64=image_base64,
                reference_object=reference_object,
                reference_size_cm=reference_size,
                food_type=food_type
            )
            return result

        except Exception as e:
            # Fallback: return default portion estimate
            return {
                "portion_grams": 200.0,  # Default 200g
                "confidence": 0.5,
                "error": str(e),
                "fallback_used": True,
                "note": "Using default portion estimate due to MiDaS error"
            }


# Example usage in agents
if __name__ == "__main__":
    import asyncio

    async def test_midas_client():
        """Test the MiDaS Railway client"""

        print("🧪 Testing MiDaS Railway Client\n")

        # Example image URL (replace with actual)
        test_image_url = "https://example.com/jollof-rice.jpg"

        async with MiDaSRailwayClient() as client:
            # Test 1: Health check
            print("1️⃣  Testing health check...")
            try:
                health = await client.health_check()
                print(f"   ✓ Server healthy: {health}")
            except Exception as e:
                print(f"   ✗ Health check failed: {e}")

            # Test 2: Depth estimation
            print("\n2️⃣  Testing depth estimation...")
            try:
                depth_result = await client.estimate_depth(test_image_url)
                print(f"   ✓ Depth map generated: {depth_result.get('depth_map_shape')}")
            except Exception as e:
                print(f"   ✗ Depth estimation failed: {e}")

            # Test 3: Portion estimation
            print("\n3️⃣  Testing portion estimation...")
            try:
                portion_result = await client.estimate_portion_size(
                    image_url=test_image_url,
                    reference_object="plate"
                )
                print(f"   ✓ Portion estimate: {portion_result.get('portion_grams')}g")
                print(f"   ✓ Confidence: {portion_result.get('confidence')}")
            except Exception as e:
                print(f"   ✗ Portion estimation failed: {e}")

        # Test 4: Convenience function
        print("\n4️⃣  Testing convenience function...")
        try:
            result = await get_portion_estimate(test_image_url, "plate")
            print(f"   ✓ Result: {result}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

    # Run tests
    asyncio.run(test_midas_client())
