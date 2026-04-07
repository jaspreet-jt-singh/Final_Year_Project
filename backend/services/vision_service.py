import os
import numpy as np
from PIL import Image
import io
from pathlib import Path
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.model      = None
        self.model_path = None

    async def initialize(self):
        try:
            model_path_env = os.getenv("YOLO_MODEL_PATH", "models/yolo11s_indian.pt")
            if not model_path_env.strip():
                raise ValueError("YOLO_MODEL_PATH is empty in .env")

            project_root    = Path(__file__).parent.parent.parent
            model_full_path = project_root / model_path_env

            if not model_full_path.exists():
                raise FileNotFoundError(f"Model not found at {model_full_path}")

            self.model      = YOLO(str(model_full_path))
            self.model_path = model_path_env
            # FIX: removed self.model.eval() — Ultralytics handles this internally

            logger.info(f"✅ Loaded YOLO model from {self.model_path}")
            logger.info(f"✅ Classes: {list(self.model.names.values())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize vision service: {e}")
            raise

    async def warmup(self):
        try:
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)  # smaller dummy is fine
            self.model.predict(dummy, verbose=False, conf=0.25, imgsz=640)
            logger.info("✅ Model warm-up completed")
        except Exception as e:
            logger.error(f"❌ Warm-up failed: {e}")
            raise

    def analyze_image(self, image_content: bytes, conf: float = 0.25) -> dict | None:
        try:
            # DEBUG: save received bytes to disk — check if it looks correct
            debug_path = Path('debug_received_image.jpg')
            with open(debug_path, 'wb') as f:
                f.write(image_content)
            logger.info(f"DEBUG: Saved received image to {debug_path} ({len(image_content)} bytes)")
            # ✅ PIL always RGB — no BGR, no RGBA
            img       = Image.open(io.BytesIO(image_content)).convert('RGB')
            img_array = np.array(img)

            logger.info(f"Image shape: {img_array.shape}")
            logger.info(f"Image dtype: {img_array.dtype}")
            logger.info(f"Value range: {img_array.min()} – {img_array.max()}")

            if img_array.dtype != np.uint8:
                img_array = img_array.astype(np.uint8)

            img_height, img_width = img_array.shape[:2]

            # ✅ No manual resize — YOLO letterboxes internally
            results    = self.model.predict(img_array, verbose=False, conf=conf, imgsz=640)
            detections = results[0].boxes
            logger.info(f"Found {len(detections)} detections above {conf} confidence")

            if len(detections) == 0:
                logger.warning("No food detected in image")
                return None

            # Pick highest confidence detection
            best_box  = max(detections, key=lambda b: float(b.conf[0]))
            class_id  = int(best_box.cls[0])
            food_label = self.model.names[class_id]
            confidence = float(best_box.conf[0])
            bbox       = best_box.xyxy[0].cpu().numpy().astype(int).tolist()

            logger.info(f"Detected {food_label} with confidence {confidence:.3f}")

            return {
                "food_label"   : food_label,
                "confidence"   : round(confidence, 4),
                "bounding_box" : bbox,
                "img_width"    : img_width,
                "img_height"   : img_height
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing image: {e}")
            raise

    def get_class_names(self) -> list:
        return list(self.model.names.values()) if self.model else []