#!/usr/bin/env python3
"""
YOLOv8 Segmentation Training Script for Indian Food Detection
Auto-detects VRAM and configures optimal batch size for RTX 3050 4GB
"""

import torch
import os
import sys
import shutil
import yaml
import json
import argparse
from pathlib import Path
from ultralytics import YOLO

def detect_vram_and_batch_size():
    """Auto-detect VRAM and set appropriate batch size"""
    if torch.cuda.is_available():
        gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {gpu_memory_gb:.1f} GB")
        
        # Batch size recommendations for YOLOv8n-seg
        if gpu_memory_gb >= 8:
            return 16
        elif gpu_memory_gb >= 6:
            return 12
        elif gpu_memory_gb >= 4:
            return 8  # RTX 3050 4GB - optimal batch size
        else:
            return 4
    else:
        print("WARNING: No GPU detected, using CPU")
        return 1

def train_yolo_segmentation(data_path=None, epochs=60, imgsz=640, batch_size=None):
    """Train YOLOv8n-seg model on Indian food dataset"""
    
    # Project paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    models_dir = project_root / "models"
    
    print("=== YOLOv8 Indian Food Segmentation Training ===")
    print(f"Project root: {project_root}")
    
    # Auto-detect batch size if not provided
    if batch_size is None:
        batch_size = detect_vram_and_batch_size()
    
    print(f"Using batch size: {batch_size}")
    
    # Data path
    if data_path is None:
        data_path = data_dir / "indianfoodnet_yolo" / "data.yaml"
    
    data_path = Path(data_path)
    print(f"Training data: {data_path}")
    
    if not data_path.exists():
        print(f"ERROR: Training data not found at {data_path}")
        print("Please ensure IndianFoodNet dataset is properly set up in data/indianfoodnet_yolo/")
        return False
    
    # Ensure models directory exists
    models_dir.mkdir(exist_ok=True)
    
    # Load YOLOv8n-seg model
    print("Loading YOLOv8n-seg model...")
    model = YOLO('yolov8n-seg.pt')
    
    # Training configuration
    device = 0 if torch.cuda.is_available() else 'cpu'
    print(f"Training device: {'GPU' if device == 0 else 'CPU'}")
    
    # Train the model
    print("Starting training...")
    try:
        results = model.train(
            data=str(data_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            patience=15,
            device=device,
            workers=2,
            amp=True,  # Always use mixed precision
            save_period=10,
            project=str(models_dir / "runs"),
            name="yolo_indian_seg",
            exist_ok=True,
            verbose=True
        )
        
        print("✅ Training completed successfully!")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False
    
    # Copy best model to models directory
    runs_dir = models_dir / "runs" / "yolo_indian_seg"
    if runs_dir.exists():
        # Find the latest run directory
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith('train')]
        if run_dirs:
            latest_run = max(run_dirs, key=lambda x: x.stat().st_mtime)
            best_pt_path = latest_run / "weights" / "best.pt"
            
            if best_pt_path.exists():
                target_path = models_dir / "yolov8_indian_seg.pt"
                shutil.copy2(best_pt_path, target_path)
                print(f"✅ Best model saved to: {target_path}")
            else:
                print("❌ best.pt not found in training output")
                return False
        else:
            print("❌ No training runs found")
            return False
    
    # Save class names
    try:
        with open(data_path, 'r') as f:
            data_config = yaml.safe_load(f)
        
        class_names = data_config.get('names', {})
        class_names_path = models_dir / "class_names.json"
        
        with open(class_names_path, 'w') as f:
            json.dump(class_names, f, indent=2)
        
        print(f"✅ Class names saved to: {class_names_path}")
        print(f"Classes: {len(class_names)}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not save class names: {e}")
    
    # Print training summary
    print("\n=== Training Summary ===")
    print(f"Model: YOLOv8n-seg")
    print(f"Dataset: {data_path}")
    print(f"Epochs: {epochs}")
    print(f"Image size: {imgsz}")
    print(f"Batch size: {batch_size}")
    print(f"Device: {'GPU' if device == 0 else 'CPU'}")
    print(f"Output model: {models_dir / 'yolov8_indian_seg.pt'}")
    
    return True

def main():
    """Main training script entry point"""
    parser = argparse.ArgumentParser(description="Train YOLOv8n-seg on Indian food dataset")
    parser.add_argument("--data", type=str, help="Path to data.yaml file")
    parser.add_argument("--epochs", type=int, default=60, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--batch", type=int, help="Batch size (auto-detected if not provided)")
    
    args = parser.parse_args()
    
    success = train_yolo_segmentation(
        data_path=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch_size=args.batch
    )
    
    if success:
        print("\n🎉 Training completed successfully!")
        print("You can now use the trained model for food detection.")
        print("Update your .env file: YOLO_MODEL_PATH=models/yolov8_indian_seg.pt")
        sys.exit(0)
    else:
        print("\n💥 Training failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
