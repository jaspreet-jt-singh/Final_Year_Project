"""
Vision Service for YOLO Food Detection
"""

import os
import numpy as np
from PIL import Image
import io
from pathlib import Path
import logging
from ultralytics import YOLO
import hashlib
logger = logging.getLogger(__name__)

# Per-class minimum confidence — raises bar for weak classes
WEAK_CLASS_MIN_CONF = {
    'GreenChutney': 0.50,
    'Dosa'        : 0.45,
    'FishCurry'   : 0.50,
    'Samosa'      : 0.45,
}


class VisionService:
    def __init__(self):
        self.model      = None
        self.model_path = None

    async def initialize(self):
        try:
            model_path_env = os.getenv("YOLO_MODEL_PATH", "results_after_discontinuation/yolo11s_indian_food_best.pt")
            if not model_path_env.strip():
                raise ValueError("YOLO_MODEL_PATH is empty in .env")

            project_root    = Path(__file__).parent.parent.parent
            model_full_path = project_root / model_path_env

            if not model_full_path.exists():
                raise FileNotFoundError(f"Model not found at {model_full_path}")

            self.model      = YOLO(str(model_full_path))
            self.model_path = model_path_env
            # NOTE: do NOT call self.model.eval() — Ultralytics handles this internally
            # Calling it externally suppresses confidence scores

            logger.info(f"✅ Loaded YOLO model from {self.model_path}")
            logger.info(f"✅ Classes: {list(self.model.names.values())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize vision service: {e}")
            raise

    async def warmup(self):
        try:
            dummy = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy, verbose=False, conf=0.25, iou=0.45, imgsz=640)
            logger.info("✅ Model warm-up completed")
        except Exception as e:
            logger.error(f"❌ Warm-up failed: {e}")
            raise

    def analyze_image(self, image_content: bytes, conf: float = 0.25, iou: float = 0.45) -> dict | None:
        """
        Analyze image bytes and return best detection.
        - PIL always gives RGB (no BGR, no RGBA issues)
        - NO manual resize — YOLO letterboxes internally with imgsz=640
        - iou=0.45 matches notebook exactly
        """
        try:
            img_hash = hashlib.md5(image_content).hexdigest()[:8]
            logger.info(f"Image hash: {img_hash} | Size: {len(image_content)} bytes")
            # PIL always RGB — strips alpha, no BGR swap needed
            img       = Image.open(io.BytesIO(image_content)).convert('RGB')

            # iou=0.45 matches notebook
            results    = self.model.predict(img, verbose=False, conf=conf, iou=iou, imgsz=640, device="cpu")
            detections = results[0].boxes
            logger.info(f"Found {len(detections)} detections above {conf} confidence")

            if len(detections) == 0:
                logger.warning("No food detected in image")
                return None

            # Filter by per-class minimum confidence, then pick highest
            valid_boxes = []
            for box in detections:
                class_id   = int(box.cls[0])
                class_name = self.model.names[class_id]
                confidence = float(box.conf[0])
                min_conf   = WEAK_CLASS_MIN_CONF.get(class_name, conf)
                if confidence >= min_conf:
                    valid_boxes.append((box, class_name, confidence))
                else:
                    logger.info(f"Skipping {class_name} at {confidence:.3f} (min={min_conf})")

            if not valid_boxes:
                logger.warning("All detections below per-class minimum confidence")
                return None

            # Return ALL valid detections (sorted by confidence)
            valid_boxes.sort(key=lambda x: x[2], reverse=True)
            
            detections = []
            for box, class_name, confidence in valid_boxes:
                bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
                detections.append({
                    "food_label"   : class_name,
                    "confidence"   : round(confidence, 4),
                    "bounding_box" : bbox
                })
            
            logger.info(f"Detected {len(detections)} foods: {[d['food_label'] for d in detections]}")
            
            return {
                "detections" : detections,
                "img_width"  : img.width,
                "img_height" : img.height
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing image: {e}")
            raise

    def get_class_names(self) -> list:
        return list(self.model.names.values()) if self.model else []
