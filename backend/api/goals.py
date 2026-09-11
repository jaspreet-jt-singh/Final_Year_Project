from fastapi import APIRouter, HTTPException

from backend.api.schemas import ConditionsResponse, ERRORS, GoalsResponse, MacroCalculationRequest, MacroGoal
from backend.domain.policy import GOALS, condition_options
from backend.domain.rules import NutritionRules

router = APIRouter()


@router.get("/api/user/goals", response_model=GoalsResponse)
async def goals():
    return {"goals": list(GOALS.values())}


@router.get("/api/user/health-conditions", response_model=ConditionsResponse)
async def conditions():
    return {"health_conditions": condition_options()}


@router.post("/api/user/calculate-macros", response_model=MacroGoal, responses=ERRORS)
async def calculate_macros(payload: MacroCalculationRequest):
    if not 0 < payload.target_calories <= 5000:
        raise HTTPException(400, "Target calories must be positive and at most 5000")
    return NutritionRules().calculate_macros(payload.goal, payload.target_calories, payload.health_condition)
