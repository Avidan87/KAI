"""
Florence-2 Bounding Box Detection for Food Items

Microsoft's Florence-2 for accurate object detection with bounding boxes.
Integrates with Vision Agent for per-food portion estimation.

Official Docs: https://huggingface.co/microsoft/Florence-2-base
"""

import logging
from typing import List, Dict, Tuple
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class FlorenceBBoxDetector:
    """Florence-2 bounding box detector for food regions"""

    def __init__(self, device: str = "cpu", model_variant: str = "base"):
        """
        Initialize Florence-2 detector.

        Args:
            device: "cpu" or "cuda"
            model_variant: "base" (230M params) or "large" (770M params)
        """
        self.device = device
        self.model_variant = model_variant
        self.model = None
        self.processor = None
        self._model_loaded = False

        # Model name
        self.model_name = f"microsoft/Florence-2-{model_variant}"

    def load_model(self):
        """Lazy load Florence-2 on first use"""
        if self._model_loaded:
            return

        try:
            logger.info(f"Loading Florence-2 ({self.model_variant})...")

            from transformers import AutoProcessor, AutoModelForCausalLM
            import torch

            # Load processor
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # Load model
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                trust_remote_code=True
            )

            # Move to device
            self.model = self.model.to(self.device)

            self._model_loaded = True
            logger.info(f"✓ Florence-2 ({self.model_variant}) loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Florence-2: {e}")
            raise

    def detect_objects(self, image: np.ndarray) -> List[Dict[str, any]]:
        """
        Detect objects in image with bounding boxes.

        Args:
            image: RGB image as numpy array (H, W, 3)

        Returns:
            List of detections:
            [
                {
                    "bbox": [x1, y1, x2, y2],  # Top-left, bottom-right
                    "label": "object",
                    "confidence": 0.9
                },
                ...
            ]
        """
        self.load_model()

        # Convert to PIL Image
        if isinstance(image, np.ndarray):
            pil_image = Image.fromarray(image.astype(np.uint8))
        else:
            pil_image = image

        try:
            import torch

            # Task prompt for object detection
            prompt = "<OD>"

            # Prepare inputs (from official docs)
            inputs = self.processor(
                text=prompt,
                images=pil_image,
                return_tensors="pt"
            )

            # Move to device
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            inputs = inputs.to(self.device, torch_dtype)

            # Generate predictions
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    do_sample=False,
                    num_beams=3
                )

            # Decode results
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=False
            )[0]

            # Parse output (from official docs)
            parsed_answer = self.processor.post_process_generation(
                generated_text,
                task="<OD>",
                image_size=(pil_image.width, pil_image.height)
            )

            # Extract detections
            detections = []
            if '<OD>' in parsed_answer:
                od_result = parsed_answer['<OD>']
                bboxes = od_result.get('bboxes', [])
                labels = od_result.get('labels', [])

                for bbox, label in zip(bboxes, labels):
                    detections.append({
                        "bbox": bbox,  # [x1, y1, x2, y2]
                        "label": label,
                        "confidence": 0.9  # Florence-2 doesn't return confidence
                    })

            logger.info(
                f"Florence-2 detected {len(detections)} regions "
                f"in {pil_image.width}×{pil_image.height} image"
            )

            return detections

        except Exception as e:
            logger.error(f"Florence-2 detection failed: {e}")
            raise

    def unload_model(self):
        """Free memory by unloading model"""
        if self._model_loaded:
            import torch

            del self.model
            del self.processor
            self.model = None
            self.processor = None
            self._model_loaded = False

            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.info(f"✓ Florence-2 unloaded from memory")

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded


# Convenience function
def detect_food_regions(image: np.ndarray, device: str = "cpu") -> List[Dict[str, any]]:
    """
    One-shot food region detection.

    Args:
        image: RGB image
        device: "cpu" or "cuda"

    Returns:
        List of detected regions with bounding boxes
    """
    detector = FlorenceBBoxDetector(device=device, model_variant="base")
    detections = detector.detect_objects(image)
    detector.unload_model()
    return detections
