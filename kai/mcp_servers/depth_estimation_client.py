"""
Depth Estimation Railway MCP Client

This module provides a client to call the hosted Depth Estimation MCP server on Railway.
Server uses Depth Anything V2 Small (state-of-the-art, 24.8M params).

Makes HTTP requests to Railway-hosted MCP server endpoint using DEPTH_ESTIMATION_URL from .env
Legacy support: Also reads MIDAS_MCP_URL for backwards compatibility
"""

import httpx
import os
import time
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DepthEstimationClient:
    """Client for calling Depth Estimation MCP server (Depth Anything V2) hosted on Railway"""

    def __init__(self, railway_url: Optional[str] = None):
        """
        Initialize Depth Estimation Railway client.

        Args:
            railway_url: URL of hosted Depth Estimation MCP server on Railway
                        If None, reads from DEPTH_ESTIMATION_URL or MIDAS_MCP_URL (legacy) env variable
        """
        self.railway_url = railway_url or os.getenv("DEPTH_ESTIMATION_URL") or os.getenv("MIDAS_MCP_URL")

        if not self.railway_url:
            raise ValueError(
                "Depth Estimation Railway URL not provided. Set DEPTH_ESTIMATION_URL (or legacy MIDAS_MCP_URL) "
                "environment variable or pass railway_url parameter."
            )

        # Remove trailing slash
        self.railway_url = self.railway_url.rstrip('/')

        # Initialize async HTTP client with extended timeout for depth estimation
        # Depth Anything V2 can take 30-60 seconds on CPU (Railway serverless)
        # Timeout set to 120s to handle cold starts + processing
        self.client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def estimate_depth(
        self,
        image_url: str
    ) -> Dict[str, Any]:
        """
        Estimate depth map from food image using Depth Anything V2.

        Args:
            image_url: URL of the food image

        Returns:
            Dict with depth map data and metadata

        Note:
            Server uses Depth Anything V2 Small (24.8M params).
            model_type parameter removed - server now uses fixed model.
        """
        endpoint = f"{self.railway_url}/api/v1/depth/estimate"

        # Performance tracking
        start_time = time.perf_counter()

        payload = {
            "image_url": image_url
        }

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()

            elapsed = time.perf_counter() - start_time
            logger.info(f"⏱️ Depth estimation completed in {elapsed:.2f}s")

            return response.json()

        except httpx.HTTPStatusError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Depth API error after {elapsed:.2f}s: {e.response.status_code}")
            raise Exception(f"Depth API error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Connection failed after {elapsed:.2f}s: {str(e)}")
            raise Exception(f"Failed to connect to Depth Railway server: {e}")

    async def estimate_portion_size(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        reference_object: Optional[str] = None,
        reference_size_cm: Optional[float] = None,
        food_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate portion size using Depth Anything V2 depth estimation.

        Args:
            image_url: URL of the food image (optional if image_base64 provided)
            image_base64: Base64 encoded image (optional if image_url provided)
            reference_object: Type of reference object (e.g., "plate", "spoon", "hand")
            reference_size_cm: Known size of reference object in cm
            food_type: Type of food for density calculation (e.g., "Jollof Rice")

        Returns:
            Dict with portion estimate in grams/ml and confidence score
            {
                "portion_grams": 250.0,
                "volume_ml": 200.0,
                "confidence": 0.78,
                "reference_object_detected": true,
                "success": true,
                "message": "..."
            }
        """
        if not image_url and not image_base64:
            raise ValueError("Either image_url or image_base64 must be provided")

        endpoint = f"{self.railway_url}/api/v1/portion/estimate"

        # Performance tracking
        start_time = time.perf_counter()

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

            elapsed = time.perf_counter() - start_time
            result = response.json()

            # Log performance with food type for analysis
            logger.info(
                f"⏱️ Portion estimation completed in {elapsed:.2f}s "
                f"(food={food_type}, grams={result.get('portion_grams', 0):.1f}g)"
            )

            return result

        except httpx.HTTPStatusError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Portion API error after {elapsed:.2f}s: {e.response.status_code}")
            raise Exception(f"Portion API error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Connection failed after {elapsed:.2f}s: {str(e)}")
            raise Exception(f"Failed to connect to Depth Railway server: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Depth Estimation Railway server is healthy.

        Returns:
            Dict with health status
        """
        endpoint = f"{self.railway_url}/health"

        start_time = time.perf_counter()

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()

            elapsed = time.perf_counter() - start_time
            logger.info(f"⏱️ Health check completed in {elapsed:.2f}s")

            return response.json()

        except httpx.HTTPStatusError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Health check failed after {elapsed:.2f}s: {e.response.status_code}")
            raise Exception(f"Health check failed: {e.response.status_code}")
        except httpx.RequestError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Cannot reach server after {elapsed:.2f}s: {str(e)}")
            raise Exception(f"Cannot reach Depth Railway server: {e}")

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
    Convenience function to get portion estimate from Depth Estimation Railway.

    This function can be used directly in OpenAI Agents SDK tools.
    Uses Depth Anything V2 Small for state-of-the-art depth estimation.

    Args:
        image_url: URL of food image (optional if image_base64 provided)
        image_base64: Base64 encoded image (optional if image_url provided)
        reference_object: Detected reference object (plate, spoon, hand, etc.)
        food_type: Type of food for density calculation (e.g., "Jollof Rice")

    Returns:
        {
            "portion_grams": 250.0,
            "volume_ml": 200.0,
            "confidence": 0.78,
            "reference_object_detected": true,
            "success": true
        }
    """
    # Performance tracking
    overall_start = time.perf_counter()

    if not image_url and not image_base64:
        logger.warning("⚠️ No image provided for portion estimation")
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

    async with DepthEstimationClient() as client:
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

            overall_elapsed = time.perf_counter() - overall_start
            logger.info(f"✅ Total get_portion_estimate() time: {overall_elapsed:.2f}s")

            return result

        except Exception as e:
            overall_elapsed = time.perf_counter() - overall_start
            logger.error(
                f"❌ Portion estimation failed after {overall_elapsed:.2f}s: {str(e)[:100]}"
            )

            # Fallback: return default portion estimate
            return {
                "portion_grams": 200.0,  # Default 200g
                "confidence": 0.5,
                "error": str(e),
                "fallback_used": True,
                "note": "Using default portion estimate due to depth estimation error"
            }


# Example usage in agents
if __name__ == "__main__":
    import asyncio

    async def test_depth_estimation_client():
        """Test the Depth Estimation Railway client"""

        print("🧪 Testing Depth Estimation Railway Client\n")

        # Example image URL (replace with actual)
        test_image_url = "https://example.com/jollof-rice.jpg"

        async with DepthEstimationClient() as client:
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
    asyncio.run(test_depth_estimation_client())
