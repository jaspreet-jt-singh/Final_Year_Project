"""
FastAPI Backend for AI Food Recognition
Phase 1: Working Food Recognition MVP
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import os
import asyncio
import concurrent.futures
from pathlib import Path
import logging
import torch
from ultralytics import YOLO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import services
from services.vision_service import VisionService
from services.nutrition_service import NutritionService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="AI Food Recognition API",
    description="Indian Food Recognition with Nutrition Analysis",
    version="1.0.0"
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
vision_service = None
nutrition_service = None
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    global vision_service, nutrition_service
    
    logger.info("Starting AI Food Recognition API...")
    
    try:
        # Initialize nutrition service
        nutrition_service = NutritionService()
        await nutrition_service.initialize()
        logger.info("Nutrition service initialized")
        
        # Initialize vision service
        vision_service = VisionService()
        await vision_service.initialize()
        logger.info("Vision service initialized")
        
        # Warm-up pass on dummy black image
        await vision_service.warmup()
        logger.info("Model warm-up completed")
        
        logger.info("Phase 1 MVP ready")
        
    except Exception as e:
        logger.error(f"Backend initialization failed: {e}")
        raise

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model_loaded": vision_service is not None and vision_service.model is not None,
        "phase": "1",
        "description": "AI Food Recognition - Phase 1 MVP"
    }

@app.post("/api/analyze-food")
@limiter.limit("5/minute")
async def analyze_food(request: Request, file: UploadFile = File(...)):
    """
    Analyze uploaded food image and return nutrition information
    Phase 1: Real YOLO detection + SQLite nutrition lookup
    """
    
    # Debug logging
    logger.info(f"Received file upload request: {file.filename if file else 'No file'}")
    logger.info(f"File content type: {file.content_type if file else 'No file'}")
    
    if not vision_service or not nutrition_service:
        raise HTTPException(
            status_code=503, 
            detail="Services not initialized. Please check /api/health"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    # Validate file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10MB"
        )
    
    try:
        # Run vision inference in thread pool to avoid blocking
        detection_result = await asyncio.get_event_loop().run_in_executor(
            executor, 
            vision_service.analyze_image, 
            content
        )
        
        if not detection_result:
            raise HTTPException(
                status_code=404,
                detail="No food detected in image"
            )
        
        # Get nutrition information
        nutrition_info = await nutrition_service.get_nutrition_for_food(
            detection_result["food_label"]
        )
        
        if nutrition_info is None:
            # Handle known missing foods
            missing_foods = ["kathi_roll", "vada_pav", "momos"]
            if detection_result["food_label"] in missing_foods:
                return {
                    "food_label": detection_result["food_label"],
                    "display_name": detection_result["food_label"].replace("_", " ").title(),
                    "confidence": detection_result["confidence"],
                    "bounding_box": detection_result["bounding_box"],
                    "img_width": detection_result["img_width"],
                    "img_height": detection_result["img_height"],
                    "macros": None,
                    "macros_unit": "per_100g",
                    "nutrition_source": None,
                    "food_not_found": True
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Nutrition information not found for {detection_result['food_label']}"
                )
        
        # Combine detection and nutrition results
        result = {
            "food_label": detection_result["food_label"],
            "display_name": nutrition_info["display_name"],
            "confidence": detection_result["confidence"],
            "bounding_box": detection_result["bounding_box"],
            "img_width": detection_result["img_width"],
            "img_height": detection_result["img_height"],
            "macros": nutrition_info["macros"],
            "macros_unit": "per_100g",
            "nutrition_source": "INDB",
            "food_not_found": False
        }
        
        logger.info(f"Analyzed food: {detection_result['food_label']} with confidence {detection_result['confidence']}")
        
        return JSONResponse(content=result)
        
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
