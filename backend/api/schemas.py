"""Public wire contracts. Existing response keys remain stable."""

import re
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.policy import CONDITIONS, resolve_condition, resolve_goal

HealthCondition = Enum("HealthCondition", {key: key for key in CONDITIONS}, type=str)
NutritionNumber = Annotated[float, Field(ge=0, le=10000, allow_inf_nan=False, strict=True)]


class Macros(BaseModel):
    calories: NutritionNumber
    protein_g: NutritionNumber
    carbs_g: NutritionNumber
    fat_g: NutritionNumber


class FoodDetection(BaseModel):
    food_label: str
    display_name: str
    confidence: float
    bounding_box: tuple[float, float, float, float]
    macros: Macros | None
    macros_unit: Literal["per_100g"] = "per_100g"
    nutrition_source: str | None
    nutrition_not_found: bool | None = None


class FoodAnalysis(BaseModel):
    detections: list[FoodDetection]
    img_width: int | None
    img_height: int | None
    food_not_found: bool
    message: str | None = None


class RecommendationFood(BaseModel):
    model_config = ConfigDict(extra="ignore")
    food_label: str = Field(max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    macros: Macros | None = None

    @field_validator("food_label", "display_name")
    @classmethod
    def safe_label(cls, value):
        if value is None:
            return value
        cleaned = re.sub(r"[^a-zA-Z0-9 _-]", "", value)
        if not cleaned.strip():
            raise ValueError("Food label must not be empty")
        return cleaned


class RecommendationRequest(BaseModel):
    detected_foods: list[RecommendationFood] = Field(min_length=1, max_length=10)
    user_goal: str = Field(default="Maintenance", max_length=100)
    health_condition: str = Field(default="none", max_length=100)

    @field_validator("user_goal")
    @classmethod
    def goal(cls, value):
        return resolve_goal(value)

    @field_validator("health_condition")
    @classmethod
    def condition(cls, value):
        return resolve_condition(value)


class RecommendationResponse(BaseModel):
    recommendations: list[str] = Field(min_length=3, max_length=3)
    source: Literal["groq", "fallback", "openai", "ollama"]
    health_condition: HealthCondition


class MacroCalculationRequest(BaseModel):
    goal: str = Field(max_length=100)
    target_calories: int
    health_condition: str = Field(default="none", max_length=100)

    @field_validator("goal")
    @classmethod
    def goal_key(cls, value):
        return resolve_goal(value)

    @field_validator("health_condition")
    @classmethod
    def condition_key(cls, value):
        return resolve_condition(value)


class MacroGoal(BaseModel):
    goal: str
    goal_key: str
    target_calories: int
    carbs_g: int
    protein_g: int
    fat_g: int
    carbs_percent: int
    protein_percent: int
    fat_percent: int
    description: str
    health_condition: str
    health_condition_key: HealthCondition


class GoalOption(BaseModel):
    name: str
    carbs_percent: int
    protein_percent: int
    fat_percent: int
    description: str


class GoalsResponse(BaseModel):
    goals: list[GoalOption]


class ConditionOption(BaseModel):
    key: HealthCondition
    name: str
    description: str
    adjustment_label: str


class ConditionsResponse(BaseModel):
    health_conditions: list[ConditionOption]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_status: str
    model_available: bool
    description: str


class ErrorResponse(BaseModel):
    detail: str


ERRORS = {code: {"model": ErrorResponse} for code in (400, 413, 422, 429, 500, 503)}
