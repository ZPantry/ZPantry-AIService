from fastapi import APIRouter

from app.schemas.common_schema import ApiResponse
from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    MealIngredientCheckAiRequest,
    MealIngredientCheckAiResponse,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
)
from app.services.recommendation_service import (
    check_meal_ingredients,
    recommend_meals,
    suggest_missing_ingredients,
)

router = APIRouter()


@router.post("/recommend-meals", response_model=ApiResponse[RecommendMealAiResponse])
async def recommend_meal(request: RecommendMealAiRequest) -> ApiResponse[RecommendMealAiResponse]:
    data = recommend_meals(request)
    return ApiResponse(success=True, message="ok", data=data, errors=None)


@router.post(
    "/suggest-missing-ingredients",
    response_model=ApiResponse[MissingIngredientAiResponse],
)
async def suggest_missing(
    request: MissingIngredientAiRequest,
) -> ApiResponse[MissingIngredientAiResponse]:
    data = suggest_missing_ingredients(request)
    return ApiResponse(success=True, message="ok", data=data, errors=None)


@router.post(
    "/check-meal-ingredients",
    response_model=ApiResponse[MealIngredientCheckAiResponse],
)
async def check_meal(
    request: MealIngredientCheckAiRequest,
) -> ApiResponse[MealIngredientCheckAiResponse]:
    data = check_meal_ingredients(request)
    return ApiResponse(success=True, message="ok", data=data, errors=None)
