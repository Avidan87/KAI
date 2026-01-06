"""
Download Florence-2 Model from HuggingFace

This script pre-downloads the Florence-2 model so it's ready when needed.
Run this once to cache the model locally.
"""

import os
from transformers import AutoProcessor, AutoModelForCausalLM
import torch

def download_florence2(model_variant="base"):
    """
    Download Florence-2 model from HuggingFace.

    Args:
        model_variant: "base" (230M params, default) or "large" (770M params)
    """
    model_name = f"microsoft/Florence-2-{model_variant}"

    print(f"\n{'='*60}")
    print(f"Downloading Florence-2 Model: {model_name}")
    print(f"{'='*60}\n")

    print("📥 Step 1/2: Downloading processor...")
    try:
        processor = AutoProcessor.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        print("✅ Processor downloaded successfully!\n")
    except Exception as e:
        print(f"❌ Processor download failed: {e}")
        return False

    print("📥 Step 2/2: Downloading model (this may take a few minutes)...")
    try:
        # Use float32 for CPU compatibility
        dtype = torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=dtype,
            trust_remote_code=True,
            attn_implementation="eager"  # Python 3.12+ compatibility
        )
        print("✅ Model downloaded successfully!\n")
    except Exception as e:
        print(f"❌ Model download failed: {e}")
        return False

    # Get cache location
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")

    print(f"\n{'='*60}")
    print("✅ Florence-2 Model Download Complete!")
    print(f"{'='*60}")
    print(f"\n📦 Model cached at: {cache_dir}")
    print(f"🎯 Model: {model_name}")
    print(f"💾 Size: ~500MB")
    print("\nThe model is now ready to use in your KAI app! 🚀\n")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download Florence-2 model from HuggingFace")
    parser.add_argument(
        "--variant",
        choices=["base", "large"],
        default="base",
        help="Model variant: 'base' (230M params) or 'large' (770M params)"
    )

    args = parser.parse_args()

    print("\n🤖 Florence-2 Model Downloader")
    print("This will download the model from HuggingFace and cache it locally.\n")

    success = download_florence2(model_variant=args.variant)

    if success:
        print("\n✅ All done! You can now use Florence-2 in your KAI app without delays.\n")
    else:
        print("\n❌ Download failed. Please check your internet connection and try again.\n")
