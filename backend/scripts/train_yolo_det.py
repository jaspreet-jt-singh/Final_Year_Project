#!/usr/bin/env python3
"""
Phase 0: YOLO Detection Training Script
Same logic as notebook but as .py for terminal execution
Usage: python backend\scripts\train_yolo_det.py
"""

import torch
import yaml
import os
import shutil
import json
from pathlib import Path
from ultralytics import YOLO

def main():
    print("=== Phase 0: YOLO Detection Training ===")
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    print(f"Working directory: {project_root}")
    
    # GPU Check
    print("\n=== GPU Check ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("WARNING: CUDA not available - training will be very slow!")
        device = "cpu"
    else:
        device = 0
    
    # Load YOLOv8n model for detection
    print("\n=== Loading Model ===")
    model = YOLO('yolov8n.pt')  # detection model
    
    # Training configuration for 4GB VRAM
    training_args = {
        'data': 'data/indianfoodnet_yolo/data.yaml',
        'epochs': 60,
        'imgsz': 640,
        'batch': 8,  # Critical for 4GB VRAM
        'patience': 15,
        'device': device,
        'workers': 2,  # Reduce memory usage
        'amp': True,  # Mixed precision
        'save_period': 10,  # Save every 10 epochs
        'project': 'models/runs',
        'name': 'indian_food_detection'
    }
    
    print(f"Training args: {training_args}")
    
    # Train the model
    print("\n=== Starting Training ===")
    results = model.train(**training_args)
    print("✅ Training completed!")
    
    # Copy best model to models/yolov8n_indian.pt
    print("\n=== Saving Model ===")
    runs_dir = Path('models/runs/indian_food_detection')
    if runs_dir.exists():
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if run_dirs:
            latest_run = max(run_dirs, key=lambda x: x.stat().st_mtime)
            best_model_path = latest_run / 'weights' / 'best.pt'
            
            if best_model_path.exists():
                Path('models').mkdir(exist_ok=True)
                shutil.copy2(best_model_path, 'models/yolov8n_indian.pt')
                print(f"✅ Copied best model to: models/yolov8n_indian.pt")
                print(f"Original path: {best_model_path}")
            else:
                print(f"❌ best.pt not found in {latest_run / 'weights'}")
        else:
            print("❌ No run directories found")
    else:
        print("❌ Training runs directory not found")
    
    # Save class names to models/class_names.json
    print("\n=== Extracting Class Names ===")
    data_yaml_path = 'data/indianfoodnet_yolo/data.yaml'
    if Path(data_yaml_path).exists():
        with open(data_yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)
        
        class_names = data_config.get('names', [])
        print(f"Found {len(class_names)} classes: {class_names}")
        
        with open('models/class_names.json', 'w') as f:
            json.dump(class_names, f, indent=2)
        
        print(f"✅ Saved class names to: models/class_names.json")
    else:
        print(f"❌ data.yaml not found at {data_yaml_path}")
    
    print("\n✅ Phase 0 YOLO training script completed!")

if __name__ == "__main__":
    main()
