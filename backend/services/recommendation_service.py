"""Bounded recommendation orchestration, with injectable providers for tests."""

from threading import BoundedSemaphore

from backend.domain.policy import resolve_goal
from backend.domain.recommendations import fallback_recommendations
from backend.domain.rules import NutritionRules
from backend.observability import event
from backend.settings import Settings
from .providers import GroqProvider, OpenAIProvider, OllamaProvider


class RecommendationBusy(RuntimeError):
    pass


class RecommendationService(NutritionRules):
    def __init__(self, settings=None, providers=None):
        self.settings = settings or Settings.from_environment()
        self.providers = list(providers) if providers is not None else []
        self.injected_providers = providers is not None
        self.capacity = BoundedSemaphore(self.settings.provider_capacity)

    async def initialize(self):
        if self.injected_providers:
            return
        candidates = [(bool(self.settings.groq_key.get_secret_value()), GroqProvider)]
        if not self.settings.production:
            candidates += [
                (bool(self.settings.openai_key.get_secret_value()), OpenAIProvider),
                (bool(self.settings.ollama_host), OllamaProvider),
            ]
        for enabled, provider in candidates:
            if enabled:
                try:
                    self.providers.append(provider(self.settings))
                except Exception as exc:
                    event("provider_init", provider=provider.name, outcome="unavailable", error_type=type(exc).__name__)

    async def close(self):
        for provider in reversed(self.providers):
            try:
                await provider.close()
            except Exception as exc:
                event("provider_close", provider=provider.name, outcome="failed", error_type=type(exc).__name__)
        self.providers.clear()

    async def get_recommendations(self, detected_foods, user_goal, health_condition="none"):
        condition = self._resolve_condition_key(health_condition)
        goal = resolve_goal(user_goal)
        if not self.capacity.acquire(blocking=False):
            event("provider_capacity", outcome="busy")
            raise RecommendationBusy("Recommendations are busy. Please retry shortly.")
        try:
            prompt = self._build_prompt(detected_foods, self.GOAL_MACRO_SPLITS[goal]["name"], condition)
            for provider in self.providers:
                try:
                    result = await provider.recommend(prompt)
                    if (
                        isinstance(result, list)
                        and len(result) == 3
                        and all(isinstance(item, str) and item.strip() for item in result)
                    ):
                        event("provider_result", provider=provider.name, outcome="success")
                        return {"recommendations": result, "source": provider.name, "health_condition": condition}
                    event("provider_result", provider=provider.name, outcome="invalid_response")
                except Exception as exc:
                    event("provider_result", provider=provider.name, outcome="fallback", error_type=type(exc).__name__)
            event("provider_result", provider="fallback", outcome="success")
            return {
                "recommendations": fallback_recommendations(detected_foods, goal, condition),
                "source": "fallback",
                "health_condition": condition,
            }
        finally:
            self.capacity.release()
