"""Application-owned resources with deterministic startup and cleanup."""

from backend.settings import Settings
from fastapi import Request
from .inference_runtime import InferenceRuntime
from .nutrition_service import NutritionService
from .recommendation_service import RecommendationService


class Services:
    def __init__(self, settings: Settings):
        self.inference = InferenceRuntime(settings)
        self.nutrition = NutritionService(settings.database_path)
        self.recommendations = RecommendationService(settings)

    async def start(self):
        await self.nutrition.initialize()
        await self.recommendations.initialize()

    async def close(self):
        try:
            await self.recommendations.close()
        finally:
            self.inference.close()


def get_services(request: Request):
    return request.app.state.services
