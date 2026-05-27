"""
FastAPI Backend for AI Food Recognition
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import os
import asyncio
import concurrent.futures
import re
from functools import partial
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

from services.vision_service import VisionService
from services.nutrition_service import NutritionService
from services.recommendation_service import RecommendationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Food Recognition API",
    description="Indian Food Recognition with Nutrition Analysis",
    version="1.0.0"
)

# CORS — must be added FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit is {os.getenv('RATE_LIMIT_PER_MINUTE', '30')} per minute.",
            "retry_after": 60
        }
    )

vision_service       = None
nutrition_service    = None
recommendation_service = None
executor             = concurrent.futures.ThreadPoolExecutor(max_workers=2)


@app.on_event("startup")
async def startup_event():
    global vision_service, nutrition_service, recommendation_service
    logger.info("Starting AI Food Recognition API...")
    try:
        nutrition_service = NutritionService()
        await nutrition_service.initialize()
        logger.info("Nutrition service initialized")

        vision_service = VisionService()
        await vision_service.initialize()
        logger.info("Vision service initialized")

        await vision_service.warmup()
        logger.info("Model warm-up completed")

        recommendation_service = RecommendationService()
        logger.info("Recommendation service initialized")

        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Backend initialization failed: {e}")
        raise


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": vision_service is not None,
        "description": "AI Food Recognition API"
    }


@app.get("/api/test-nutrition/{food_name}")
async def test_nutrition(food_name: str):
    try:
        nutrition = await nutrition_service.get_nutrition_for_food(food_name)
        return {"food_label": food_name, "found": bool(nutrition), "nutrition": nutrition}
    except Exception as e:
        return {"food_label": food_name, "found": False, "error": str(e), "nutrition": None}


@app.get("/api/validate-nutrition")
async def validate_nutrition():
    yolo_classes = [
        "AlooGobi", "AlooMasala", "Bhatura", "BhindiMasala", "Biryani",
        "Chai", "Chole", "CoconutChutney", "Dal", "Dosa", "DumAloo",
        "FishCurry", "Ghevar", "GreenChutney", "GulabJamun", "Idli",
        "Jalebi", "Kebab", "Kheer", "Kulfi", "Lassi", "MuttonCurry",
        "OnionPakoda", "PalakPaneer", "Poha", "RajmaCurry", "RasMalai",
        "Samosa", "ShahiPaneer", "WhiteRice"
    ]
    results = []
    for yolo_class in yolo_classes:
        try:
            nutrition = await nutrition_service.get_nutrition_for_food(yolo_class)
            results.append({
                "yolo_class"  : yolo_class,
                "display_name": nutrition["display_name"] if nutrition else None,
                "found"       : bool(nutrition),
                "calories"    : nutrition["macros"]["calories"] if nutrition else None,
            })
        except Exception as e:
            results.append({"yolo_class": yolo_class, "found": False, "error": str(e)})

    success_count = sum(1 for r in results if r["found"])
    return {
        "total_classes"      : len(yolo_classes),
        "successful_matches" : success_count,
        "success_rate"       : round((success_count / len(yolo_classes)) * 100, 1),
        "results"            : results
    }


@app.post("/api/analyze-food")
@limiter.limit(f"{os.getenv('RATE_LIMIT_PER_MINUTE', '30')}/minute")
async def analyze_food(request: Request, file: UploadFile = File(...)):
    """
    Analyze uploaded food image and return nutrition information.
    Accepts FormData with key 'file' (from frontend).
    """
    logger.info(f"Received file upload request: {file.filename if file else 'No file'}")
    logger.info(f"File content type: {file.content_type if file else 'No file'}")

    if not vision_service or not nutrition_service:
        raise HTTPException(status_code=503, detail="Services not initialized. Check /api/health")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file received")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    try:
        # FIX: pass iou=0.45 to match notebook exactly, using partial
        detection_result = await asyncio.get_event_loop().run_in_executor(
            executor,
            partial(vision_service.analyze_image, content, conf=0.25, iou=0.45)
        )

        # FIX: return HTTP 200 with empty result instead of 404
        if not detection_result:
            return JSONResponse(
                status_code=200,
                content={
                    "detections"      : [],
                    "img_width"       : None,
                    "img_height"      : None,
                    "food_not_found"  : True,
                    "message"         : "No food detected in image"
                }
            )

        # Process ALL detections and lookup nutrition for each
        all_detections = []
        for det in detection_result["detections"]:
            logger.info(f"Looking up nutrition for: '{det['food_label']}'")
            nutrition_info = await nutrition_service.get_nutrition_for_food(det["food_label"])
            
            if nutrition_info is None:
                # Format display name from YOLO label
                food_label   = det["food_label"]
                spaced       = re.sub(r'([a-z])([A-Z])', r'\1 \2', food_label)
                display_name = spaced.title()
                
                all_detections.append({
                    "food_label"         : food_label,
                    "display_name"       : display_name,
                    "confidence"       : det["confidence"],
                    "bounding_box"       : det["bounding_box"],
                    "macros"             : None,
                    "macros_unit"        : "per_100g",
                    "nutrition_source"   : None,
                    "nutrition_not_found": True
                })
            else:
                all_detections.append({
                    "food_label"      : det["food_label"],
                    "display_name"    : nutrition_info["display_name"],
                    "confidence"      : det["confidence"],
                    "bounding_box"    : det["bounding_box"],
                    "macros"          : nutrition_info["macros"],
                    "macros_unit"     : "per_100g",
                    "nutrition_source": "INDB"
                })

        result = {
            "detections"     : all_detections,
            "img_width"      : detection_result["img_width"],
            "img_height"     : detection_result["img_height"],
            "food_not_found" : False
        }

        logger.info(f"FINAL API RESPONSE: {len(all_detections)} foods detected")
        for d in all_detections:
            logger.info(f"  - {d['display_name']}: {d['confidence']:.3f}")
        
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing food: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during food analysis")


# ============== Phase 2: User Goals & Macro Calculation ==============

class MacroCalculationRequest(BaseModel):
    goal: str
    target_calories: int

@app.post("/api/user/calculate-macros")
async def calculate_macros(request: MacroCalculationRequest):
    """
    Calculate macro targets based on user goal and calorie target.
    
    Request body:
        {
            "goal": "Weight Loss",
            "target_calories": 2000
        }
    
    Returns:
        Macro breakdown with grams for carbs, protein, and fat
    """
    if not recommendation_service:
        raise HTTPException(status_code=503, detail="Recommendation service not initialized")
    
    if request.target_calories <= 0:
        raise HTTPException(status_code=400, detail="Target calories must be positive")
    
    if request.target_calories > 5000:
        raise HTTPException(status_code=400, detail="Target calories seem unrealistically high")
    
    result = recommendation_service.calculate_macros(request.goal, request.target_calories)
    return result


@app.get("/api/user/goals")
async def get_available_goals():
    """
    Get list of available dietary goals and their macro splits.
    """
    if not recommendation_service:
        raise HTTPException(status_code=503, detail="Recommendation service not initialized")
    
    return {
        "goals": list(recommendation_service.GOAL_MACRO_SPLITS.values())
    }


# ============== Phase 3: AI Recommendations ==============

@app.post("/api/recommendations")
async def get_recommendations(request: Request):
    """
    Get AI-powered dietary recommendations based on scanned food and user goal.
    
    Request body:
        {
            "detected_foods": [...],  # Array of detected food items from analysis
            "user_goal": "Weight Loss"  # User's dietary goal
        }
    
    Returns:
        3 bullet points of dietary advice
    """
    if not recommendation_service:
        raise HTTPException(status_code=503, detail="Recommendation service not initialized")
    
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    detected_foods = body.get("detected_foods", [])
    user_goal = body.get("user_goal", "Maintenance")
    
    if not detected_foods:
        raise HTTPException(status_code=400, detail="No detected foods provided")
    
    if not user_goal:
        raise HTTPException(status_code=400, detail="No user goal provided")
    
    try:
        result = await recommendation_service.get_recommendations(detected_foods, user_goal)
        return result
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@app.get("/")
async def root():
    return {
        "message": "AI Food Recognition API",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "analyze_food": "/api/analyze-food",
            "calculate_macros": "/api/user/calculate-macros",
            "recommendations": "/api/recommendations"
        }
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
