from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.schemas import ERRORS, RecommendationRequest, RecommendationResponse
from backend.services.container import Services, get_services
from backend.services.recommendation_service import RecommendationBusy


def create_router(settings, limiter):
    router = APIRouter()

    @router.post("/api/recommendations", response_model=RecommendationResponse, responses=ERRORS)
    async def recommendations(
        request: Request, payload: RecommendationRequest, services: Services = Depends(get_services)
    ):
        foods = [food.model_dump(exclude_none=True) for food in payload.detected_foods]
        try:
            return await services.recommendations.get_recommendations(
                foods, payload.user_goal, payload.health_condition
            )
        except RecommendationBusy as exc:
            raise HTTPException(503, detail=str(exc), headers={"Retry-After": "5"}) from exc

    return router
