import re
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from backend.observability import event
from backend.api.schemas import FoodAnalysis, ERRORS
from backend.services.container import Services, get_services
from backend.services.inference_runtime import InferenceBusy, InvalidImage, MAX_UPLOAD_BYTES


def create_router(settings, limiter):
    router = APIRouter()

    @router.post("/api/analyze-food", response_model=FoodAnalysis, response_model_exclude_unset=True, responses=ERRORS)
    async def analyze_food(request: Request, file: UploadFile = File(...), services: Services = Depends(get_services)):
        """
        Analyze uploaded food image and return nutrition information.
        Accepts FormData with key 'file' (from frontend).
        """

        if not services.nutrition:
            raise HTTPException(status_code=503, detail="Services not initialized. Check /api/health")

        try:
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            content = await file.read(MAX_UPLOAD_BYTES + 1)
        finally:
            await file.close()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file received")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File size must be less than 4 MiB")

        try:
            # Runtime owns the unchanged model settings and bounded executor.
            detection_result = await services.inference.analyze(content)

            # FIX: return HTTP 200 with empty result instead of 404
            if not detection_result:
                return {
                    "detections": [],
                    "img_width": None,
                    "img_height": None,
                    "food_not_found": True,
                    "message": "No food detected in image",
                }

            # Process ALL detections and lookup nutrition for each
            all_detections = []
            nutrition_by_label = {
                label: await services.nutrition.get_nutrition_for_food(label)
                for label in dict.fromkeys(det["food_label"] for det in detection_result["detections"])
            }
            for det in detection_result["detections"]:
                nutrition_info = nutrition_by_label[det["food_label"]]

                if nutrition_info is None:
                    # Format display name from YOLO label
                    food_label = det["food_label"]
                    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", food_label)
                    display_name = spaced.title()

                    all_detections.append(
                        {
                            "food_label": food_label,
                            "display_name": display_name,
                            "confidence": det["confidence"],
                            "bounding_box": det["bounding_box"],
                            "macros": None,
                            "macros_unit": "per_100g",
                            "nutrition_source": None,
                            "nutrition_not_found": True,
                        }
                    )
                else:
                    all_detections.append(
                        {
                            "food_label": det["food_label"],
                            "display_name": nutrition_info["display_name"],
                            "confidence": det["confidence"],
                            "bounding_box": det["bounding_box"],
                            "macros": nutrition_info["macros"],
                            "macros_unit": "per_100g",
                            "nutrition_source": nutrition_info["nutrition_source"],
                            "nutrition_source_url": nutrition_info.get("nutrition_source_url"),
                            "nutrition_mapping_note": nutrition_info.get("nutrition_mapping_note"),
                        }
                    )

            result = {
                "detections": all_detections,
                "img_width": detection_result["img_width"],
                "img_height": detection_result["img_height"],
                "food_not_found": False,
            }

            return result

        except InvalidImage as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except InferenceBusy as e:
            raise HTTPException(status_code=503, detail=str(e), headers={"Retry-After": "10"}) from e
        except HTTPException:
            raise
        except Exception as exc:
            event("analysis_error", error_type=type(exc).__name__)
            raise HTTPException(status_code=500, detail="Internal server error during food analysis")

    return router
