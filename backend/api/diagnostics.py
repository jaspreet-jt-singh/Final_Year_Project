from fastapi import APIRouter, Depends
from backend.api.schemas import HealthResponse
from backend.services.container import Services, get_services

router = APIRouter()


@router.get("/api")
async def api_info():
    return {
        "message": "AI Food Recognition API",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "analyze_food": "/api/analyze-food",
            "calculate_macros": "/api/user/calculate-macros",
            "recommendations": "/api/recommendations",
        },
    }


@router.get("/api/health", response_model=HealthResponse)
async def health_check(services: Services = Depends(get_services)):
    return {
        "status": "ok",
        "model_loaded": services.inference.status == "ready",
        "model_status": services.inference.status,
        "model_available": services.inference.model_available,
        "description": "AI Food Recognition API",
    }


@router.get("/api/test-nutrition/{food_name}")
async def test_nutrition(food_name: str, services: Services = Depends(get_services)):
    try:
        nutrition = await services.nutrition.get_nutrition_for_food(food_name)
        return {"food_label": food_name, "found": bool(nutrition), "nutrition": nutrition}
    except Exception:
        return {"food_label": food_name, "found": False, "error": "Nutrition lookup failed", "nutrition": None}


@router.get("/api/validate-nutrition")
async def validate_nutrition(services: Services = Depends(get_services)):
    yolo_classes = [
        "AlooGobi",
        "AlooMasala",
        "Bhatura",
        "BhindiMasala",
        "Biryani",
        "Chai",
        "Chole",
        "CoconutChutney",
        "Dal",
        "Dosa",
        "DumAloo",
        "FishCurry",
        "Ghevar",
        "GreenChutney",
        "GulabJamun",
        "Idli",
        "Jalebi",
        "Kebab",
        "Kheer",
        "Kulfi",
        "Lassi",
        "MuttonCurry",
        "OnionPakoda",
        "PalakPaneer",
        "Poha",
        "RajmaCurry",
        "RasMalai",
        "Samosa",
        "ShahiPaneer",
        "WhiteRice",
    ]
    results = []
    for yolo_class in yolo_classes:
        try:
            nutrition = await services.nutrition.get_nutrition_for_food(yolo_class)
            results.append(
                {
                    "yolo_class": yolo_class,
                    "display_name": nutrition["display_name"] if nutrition else None,
                    "found": bool(nutrition),
                    "calories": nutrition["macros"]["calories"] if nutrition else None,
                }
            )
        except Exception:
            results.append({"yolo_class": yolo_class, "found": False, "error": "Nutrition lookup failed"})

    success_count = sum(1 for r in results if r["found"])
    return {
        "total_classes": len(yolo_classes),
        "successful_matches": success_count,
        "success_rate": round((success_count / len(yolo_classes)) * 100, 1),
        "results": results,
    }
