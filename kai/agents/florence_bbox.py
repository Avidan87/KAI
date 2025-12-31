"""
Florence-2 Bounding Box Detection for Food Items

Microsoft's Florence-2 for accurate object detection with bounding boxes.
Integrates with Vision Agent for per-food portion estimation.

ENHANCED: Includes intelligent bbox splitting for oversized detections
using K-Means color clustering to separate merged foods.

Official Docs: https://huggingface.co/microsoft/Florence-2-base
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from PIL import Image
import cv2
from scipy import ndimage

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

            # Load model with Python 3.13 compatibility
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                dtype=dtype,  # Use dtype (torch_dtype is deprecated)
                trust_remote_code=True,
                attn_implementation="eager"  # Fix for Python 3.13: disable SDPA
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

        # Validate image
        if image is None:
            raise ValueError("Image cannot be None")

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

            # Move to device (properly handle BatchEncoding)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate predictions
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,  # Beam search for better accuracy
                    use_cache=False  # Disable KV caching to avoid past_key_values issue
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


# ============================================================================
# INTELLIGENT BBOX SPLITTING FOR OVERSIZED DETECTIONS
# ============================================================================

def split_oversized_bbox(
    image: np.ndarray,
    bbox: List[float],
    num_expected_foods: int = 2,
    area_threshold: float = 0.7
) -> List[Dict[str, any]]:
    """
    Split an oversized bounding box into separate food regions using K-Means clustering.

    This handles cases where Florence-2 detects the entire plate as one food
    (e.g., bbox covers 87% of image for "fried plantain" when there's also egg sauce).

    Algorithm:
    1. Check if bbox is oversized (>70% of image)
    2. Extract region and convert to HSV color space
    3. Apply K-Means clustering on colors
    4. Find connected components for each cluster
    5. Generate sub-bboxes for each component
    6. Filter noise and return valid regions

    Args:
        image: Original image as numpy array (H, W, 3) RGB
        bbox: Bounding box [x1, y1, x2, y2]
        num_expected_foods: Number of foods expected (from Florence detection count)
        area_threshold: Bbox area ratio threshold to trigger splitting (default 0.7 = 70%)

    Returns:
        List of sub-bboxes:
        [
            {"bbox": [x1, y1, x2, y2], "cluster_id": 0, "area": 1234},
            {"bbox": [x1, y1, x2, y2], "cluster_id": 1, "area": 5678},
            ...
        ]

        Returns empty list if bbox is not oversized (will use original bbox)
    """
    img_height, img_width = image.shape[:2]
    x1, y1, x2, y2 = [int(c) for c in bbox]

    # Calculate bbox area ratio
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    bbox_area = bbox_width * bbox_height
    image_area = img_width * img_height
    area_ratio = bbox_area / image_area

    # Check if bbox is oversized
    if area_ratio <= area_threshold:
        logger.info(f"Bbox covers {area_ratio:.1%} of image - not oversized, skipping split")
        return []

    logger.warning(f"🔍 Bbox covers {area_ratio:.1%} of image - attempting intelligent split into {num_expected_foods} regions")

    try:
        # Extract the region
        cropped = image[y1:y2, x1:x2].copy()

        # Convert to HSV (better for color-based segmentation)
        hsv = cv2.cvtColor(cropped, cv2.COLOR_RGB2HSV)

        # Reshape for K-Means: (H*W, 3)
        pixels = hsv.reshape(-1, 3).astype(np.float32)

        # Apply K-Means clustering
        from sklearn.cluster import KMeans

        k = min(num_expected_foods, 4)  # Cap at 4 clusters max
        logger.info(f"Running K-Means with K={k} clusters on {len(pixels)} pixels")

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(pixels)

        # Reshape back to image shape
        cluster_mask = labels.reshape(bbox_height, bbox_width)

        # Find connected components for each cluster
        sub_bboxes = []

        for cluster_id in range(k):
            # Binary mask for this cluster
            binary_mask = (cluster_mask == cluster_id).astype(np.uint8)

            # Find connected components
            labeled, num_features = ndimage.label(binary_mask)

            logger.info(f"  Cluster {cluster_id}: Found {num_features} connected components")

            # Get bounding boxes for each component
            component_slices = ndimage.find_objects(labeled)

            for component_idx, component_slice in enumerate(component_slices):
                if component_slice is None:
                    continue

                y_slice, x_slice = component_slice

                # Calculate component bbox (relative to cropped region)
                comp_x1 = x_slice.start
                comp_y1 = y_slice.start
                comp_x2 = x_slice.stop
                comp_y2 = y_slice.stop

                # Calculate area
                comp_area = (comp_x2 - comp_x1) * (comp_y2 - comp_y1)

                # Filter out tiny regions (noise)
                MIN_AREA = 500  # pixels
                if comp_area < MIN_AREA:
                    logger.debug(f"    Component {component_idx}: {comp_area}px - too small, skipping")
                    continue

                # Convert to absolute coordinates (relative to original image)
                abs_x1 = x1 + comp_x1
                abs_y1 = y1 + comp_y1
                abs_x2 = x1 + comp_x2
                abs_y2 = y1 + comp_y2

                sub_bboxes.append({
                    "bbox": [abs_x1, abs_y1, abs_x2, abs_y2],
                    "cluster_id": cluster_id,
                    "area": comp_area,
                    "area_ratio": comp_area / bbox_area
                })

                logger.info(f"    ✓ Component {component_idx}: {comp_area}px ({comp_area/bbox_area:.1%} of bbox)")

        # Sort by area (largest first)
        sub_bboxes.sort(key=lambda x: x["area"], reverse=True)

        logger.info(f"✅ Split oversized bbox into {len(sub_bboxes)} sub-regions")

        return sub_bboxes

    except Exception as e:
        logger.error(f"❌ Bbox splitting failed: {e}, returning empty list")
        return []


def merge_nearby_bboxes(
    bboxes: List[Dict[str, any]],
    distance_threshold: float = 30.0
) -> List[Dict[str, any]]:
    """
    Merge bboxes that are very close to each other (likely same food item).

    Args:
        bboxes: List of bbox dicts with "bbox" key
        distance_threshold: Maximum distance between centers to merge (pixels)

    Returns:
        Merged list of bboxes
    """
    if len(bboxes) <= 1:
        return bboxes

    merged = []
    used = set()

    for i, bbox1 in enumerate(bboxes):
        if i in used:
            continue

        # Calculate center of bbox1
        x1, y1, x2, y2 = bbox1["bbox"]
        cx1, cy1 = (x1 + x2) / 2, (y1 + y2) / 2

        # Find all bboxes to merge with this one
        to_merge = [bbox1]
        used.add(i)

        for j, bbox2 in enumerate(bboxes[i+1:], start=i+1):
            if j in used:
                continue

            # Calculate center of bbox2
            x1, y1, x2, y2 = bbox2["bbox"]
            cx2, cy2 = (x1 + x2) / 2, (y1 + y2) / 2

            # Calculate distance
            distance = np.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2)

            if distance < distance_threshold:
                to_merge.append(bbox2)
                used.add(j)

        # Merge all bboxes
        if len(to_merge) == 1:
            merged.append(to_merge[0])
        else:
            # Calculate merged bbox (union of all)
            all_x1 = min(b["bbox"][0] for b in to_merge)
            all_y1 = min(b["bbox"][1] for b in to_merge)
            all_x2 = max(b["bbox"][2] for b in to_merge)
            all_y2 = max(b["bbox"][3] for b in to_merge)

            merged_bbox = {
                "bbox": [all_x1, all_y1, all_x2, all_y2],
                "cluster_id": to_merge[0]["cluster_id"],
                "area": (all_x2 - all_x1) * (all_y2 - all_y1),
                "merged_from": len(to_merge)
            }
            merged.append(merged_bbox)

            logger.info(f"Merged {len(to_merge)} nearby bboxes into one")

    return merged
