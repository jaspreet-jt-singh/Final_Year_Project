"""
FastAPI Backend for AI Food Recognition
Phase 1: Working Food Recognition MVP
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import json
import sqlite3
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Food Recognition API",
    description="Indian Food Recognition with Nutrition Analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and data
model_loaded = False
food_label_map = None
nutrition_db_path = None

def load_food_label_map():
    """Load food label mapping from Phase 0 data"""
    global food_label_map
    try:
        food_map_path = Path(__file__).parent.parent / "data" / "food_label_map.json"
        with open(food_map_path, 'r') as f:
            food_label_map = json.load(f)
        logger.info(f"Loaded food label map with {len(food_label_map)} classes")
        return True
    except Exception as e:
        logger.error(f"Error loading food label map: {e}")
        return False

def initialize_nutrition_db():
    """Initialize nutrition database connection"""
    global nutrition_db_path
    try:
        nutrition_db_path = Path(__file__).parent.parent / "data" / "nutrition.db"
        if nutrition_db_path.exists():
            logger.info("Nutrition database initialized")
            return True
        else:
            logger.error("Nutrition database not found")
            return False
    except Exception as e:
        logger.error(f"Error initializing nutrition database: {e}")
        return False

def get_nutrition_for_food(food_label: str, serving_size_g: float = None):
    """Get nutrition information for a food label"""
    global food_label_map
    
    if not food_label_map or food_label not in food_label_map:
        return None
    
    food_data = food_label_map[food_label]
    nutrition_100g = food_data['nutrition_per_100g']
    
    # Use default serving size if not provided
    if serving_size_g is None:
        serving_size_g = food_data['default_serving_size_g']
    
    # Scale nutrition to serving size
    factor = serving_size_g / 100.0
    
    return {
        "food_label": food_label,
        "display_name": food_data['display_name'],
        "estimated_mass_g": serving_size_g,
        "mass_source": "default_serving_size",
        "macros": {
            "calories": round(nutrition_100g['calories'] * factor, 1),
            "protein_g": round(nutrition_100g['protein_g'] * factor, 1),
            "carbs_g": round(nutrition_100g['carbs_g'] * factor, 1),
            "fat_g": round(nutrition_100g['fat_g'] * factor, 1)
        },
        "nutrition_source": food_data['fallback_source']
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    global model_loaded
    
    logger.info("Starting AI Food Recognition API...")
    
    # Load Phase 0 data
    food_map_loaded = load_food_label_map()
    db_initialized = initialize_nutrition_db()
    
    # For Phase 1, we'll simulate model loading
    # In production, this would load the actual YOLOv8-seg model
    model_loaded = food_map_loaded and db_initialized
    
    if model_loaded:
        logger.info("✅ Backend initialized successfully")
        logger.info("🎯 Phase 1 MVP ready")
    else:
        logger.error("❌ Backend initialization failed")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "phase": "1",
        "description": "AI Food Recognition - Phase 1 MVP"
    }

@app.post("/api/analyze-food")
async def analyze_food(file: UploadFile = File(...)):
    """
    Analyze uploaded food image and return nutrition information
    Phase 1: Returns simulated results with real nutrition data
    """
    
    if not model_loaded:
        raise HTTPException(
            status_code=503, 
            detail="Model not loaded. Please check /api/health"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    try:
        # Read image content (for Phase 1, we don't actually process it)
        image_content = await file.read()
        
        # Phase 1: Simulate food detection
        # In production, this would use YOLOv8-seg model
        simulated_results = [
            {"food_label": "biryani", "confidence": 0.91},
            {"food_label": "dal_makhani", "confidence": 0.85},
            {"food_label": "dosa", "confidence": 0.78},
            {"food_label": "samosa", "confidence": 0.72}
        ]
        
        # Get the highest confidence result
        best_result = max(simulated_results, key=lambda x: x['confidence'])
        food_label = best_result['food_label']
        confidence = best_result['confidence']
        
        # Get nutrition information
        nutrition_info = get_nutrition_for_food(food_label)
        
        if nutrition_info is None:
            raise HTTPException(
                status_code=404,
                detail=f"Nutrition information not found for {food_label}"
            )
        
        # Add confidence to response
        nutrition_info['confidence'] = confidence
        nutrition_info['food_not_found'] = False
        
        logger.info(f"Analyzed food: {food_label} with confidence {confidence}")
        
        return JSONResponse(content=nutrition_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing food: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during food analysis"
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Food Recognition API",
        "phase": "1",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "analyze_food": "/api/analyze-food"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
