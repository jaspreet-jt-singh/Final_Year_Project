"""
Vision Service for YOLO Food Detection
Phase 1: Real YOLOv8n detection model
"""

import os
import numpy as np
import cv2
from PIL import Image
import io
from pathlib import Path
import logging
import torch
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.model = None
        self.model_path = None
        
    async def initialize(self):
        """Initialize YOLO model"""
        try:
            # Get model path from environment or default
            self.model_path = os.getenv("YOLO_MODEL_PATH", "models/yolov8n_indian.pt")
            
            # Ensure we're in project root
            project_root = Path(__file__).parent.parent.parent
            model_full_path = project_root / self.model_path
            
            if not model_full_path.exists():
                raise FileNotFoundError(f"Model not found at {model_full_path}")
            
            # Load YOLOv8n detection model
            self.model = YOLO(str(model_full_path))
            
            # Set model to evaluation mode
            self.model.eval()
            
            logger.info(f"✅ Loaded YOLO model from {self.model_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize vision service: {e}")
            raise
    
    async def warmup(self):
        """Warm-up pass on dummy black image"""
        try:
            # Create dummy black image (640x640)
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
            
            # Run inference
            results = self.model(dummy_image, verbose=False)
            
            logger.info("✅ Model warm-up completed")
            
        except Exception as e:
            logger.error(f"❌ Model warm-up failed: {e}")
            raise
    
    def analyze_image(self, image_content: bytes) -> dict:
        """
        Analyze image and return detection results
        Returns dict with food_label, confidence, bounding_box, img_width, img_height
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_content))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to max 1024px while maintaining aspect ratio
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Store original dimensions
            img_height, img_width = img_array.shape[:2]
            
            # Run YOLO inference
            results = self.model(img_array, verbose=False)
            
            # Get detections
            detections = results[0].boxes
            
            if len(detections) == 0:
                logger.warning("No food detected in image")
                return None
            
            # Get highest confidence detection
            best_detection = None
            best_confidence = 0
            
            for box in detections:
                confidence = float(box.conf[0])
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_detection = box
            
            if best_detection is None:
                logger.warning("No valid detection found")
                return None
            
            # Get class label and bounding box
            class_id = int(best_detection.cls[0])
            food_label = self.model.names[class_id]
            
            # Convert bounding box to [x1, y1, x2, y2] format
            bbox = best_detection.xyxy[0].cpu().numpy().astype(int).tolist()
            
            result = {
                "food_label": food_label,
                "confidence": float(best_confidence),
                "bounding_box": bbox,
                "img_width": img_width,
                "img_height": img_height
            }
            
            logger.info(f"Detected {food_label} with confidence {best_confidence:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing image: {e}")
            raise
    
    def get_class_names(self) -> list:
        """Get list of class names from model"""
        if self.model is None:
            return []
        return list(self.model.names.values())
