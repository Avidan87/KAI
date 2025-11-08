"""
Test MiDaS MCP Server - Diagnose Base64 Workflow Issue

This script tests the MiDaS server with both file upload and base64 methods
to identify why the food logging workflow is failing.
"""
import asyncio
import base64
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get MiDaS server URL from environment
MIDAS_URL = os.getenv("MIDAS_MCP_URL", "http://localhost:8000")
MIDAS_URL = MIDAS_URL.rstrip('/')

print("=" * 80)
print("MiDaS MCP Server Test - Diagnosing Base64 Workflow Issue")
print("=" * 80)
print(f"\nServer URL: {MIDAS_URL}")


def create_test_image_base64():
    """Create a small test image as base64 for testing"""
    from PIL import Image
    import io

    # Create a simple 100x100 red square
    img = Image.new('RGB', (100, 100), color='red')

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return img_base64


async def test_health_check():
    """Test 1: Check if MiDaS server is running"""
    print("\n[Test 1] Health Check")
    print("-" * 80)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{MIDAS_URL}/health")
            response.raise_for_status()
            data = response.json()

            print(f"✅ Server is running")
            print(f"   Status: {data.get('status')}")
            print(f"   Model Loaded: {data.get('model_loaded')}")
            print(f"   Device: {data.get('device')}")

            return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_base64_portion_estimate():
    """Test 2: Send base64 image to /api/v1/portion/estimate endpoint"""
    print("\n[Test 2] Base64 Portion Estimate (NEW endpoint - what client expects)")
    print("-" * 80)

    try:
        # Create test image
        img_base64 = create_test_image_base64()
        print(f"   Created test image (base64 length: {len(img_base64)} chars)")

        # This is what the client is sending
        payload = {
            "image_base64": img_base64,
            "reference_object": "plate",
            "reference_size_cm": 24.0
        }

        endpoint = f"{MIDAS_URL}/api/v1/portion/estimate"
        print(f"   Sending POST to: {endpoint}")
        print(f"   Payload keys: {list(payload.keys())}")

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(endpoint, json=payload)

            print(f"   Response status: {response.status_code}")

            if response.status_code == 404:
                print(f"❌ Endpoint not found! This endpoint doesn't exist on the server.")
                print(f"   Server needs to implement /api/v1/portion/estimate endpoint")
                return False

            response.raise_for_status()
            data = response.json()

            print(f"✅ Base64 portion estimate successful!")
            print(f"   Portion: {data.get('portion_grams', 'N/A')}g")
            print(f"   Volume: {data.get('volume_ml', 'N/A')}ml")
            print(f"   Confidence: {data.get('confidence', 'N/A')}")

            return True

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_file_upload_portion_estimate():
    """Test 3: Send file upload to /estimate_portion endpoint (OLD method)"""
    print("\n[Test 3] File Upload Portion Estimate (OLD endpoint - currently exists)")
    print("-" * 80)

    try:
        # Create test image file
        from PIL import Image
        import io

        img = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        print(f"   Created test image file")

        endpoint = f"{MIDAS_URL}/estimate_portion"
        print(f"   Sending POST to: {endpoint}")

        files = {
            'file': ('test_image.png', buffer, 'image/png')
        }

        data = {
            'reference_object': 'plate'
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(endpoint, files=files, data=data)

            print(f"   Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            print(f"✅ File upload portion estimate successful!")
            print(f"   Weight: {data.get('estimated_weight_grams', 'N/A')}g")
            print(f"   Volume: {data.get('estimated_volume_ml', 'N/A')}ml")
            print(f"   Confidence: {data.get('confidence', 'N/A')}")

            return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_available_endpoints():
    """Test 4: Check what endpoints are available"""
    print("\n[Test 4] Available Endpoints")
    print("-" * 80)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MIDAS_URL}/")
            response.raise_for_status()
            data = response.json()

            print(f"✅ Root endpoint accessible")
            print(f"   Available endpoints: {data.get('endpoints', [])}")

            return True
    except Exception as e:
        print(f"❌ Failed to check endpoints: {e}")
        return False


async def run_all_tests():
    """Run all diagnostic tests"""
    print("\n🧪 Running MiDaS Server Diagnostic Tests...\n")

    # Test 1: Health check
    health_ok = await test_health_check()

    if not health_ok:
        print("\n❌ Server is not running or unreachable. Cannot continue tests.")
        return

    # Test 4: Check available endpoints
    await test_available_endpoints()

    # Test 2: Try base64 (what client is trying to do)
    base64_ok = await test_base64_portion_estimate()

    # Test 3: Try file upload (what currently works)
    file_ok = await test_file_upload_portion_estimate()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Health Check:              {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Base64 Endpoint (/api/v1): {'✅ PASS' if base64_ok else '❌ FAIL - NEEDS IMPLEMENTATION'}")
    print(f"File Upload Endpoint:      {'✅ PASS' if file_ok else '❌ FAIL'}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    if not base64_ok and file_ok:
        print("🔍 ISSUE IDENTIFIED:")
        print("   - The MiDaS server only has the OLD /estimate_portion endpoint")
        print("   - This endpoint requires file uploads (multipart/form-data)")
        print("   - The NEW /api/v1/portion/estimate endpoint (for base64) doesn't exist")
        print("\n💡 SOLUTION:")
        print("   - Add a new endpoint to MCP SERVER/server.py that accepts base64 images")
        print("   - The endpoint should accept JSON payload with 'image_base64' field")
        print("   - This will allow the KAI workflow to send base64 images directly")
    elif base64_ok:
        print("✅ Both endpoints working! Base64 workflow should be functional.")
    else:
        print("❌ Server issues detected. Check if MiDaS server is deployed correctly.")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
