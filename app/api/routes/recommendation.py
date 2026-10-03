from fastapi import APIRouter

from app.schemas.common_schema import ApiResponse
from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    MealIngredientCheckAiRequest,
    MealIngredientCheckAiResponse,
    TodayMenuCompletionAiRequest,
    TodayMenuCompletionAiResponse,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
    RecommendMealV2Request,
    RecommendMealV2Response,
)
from app.services.recommendation_service import (
    check_meal_ingredients,
    check_today_menu_completion,
    recommend_meals,
    recommend_meals_v2,
    suggest_missing_ingredients,
)

router = APIRouter()


@router.post("/recommend-meals", response_model=ApiResponse[RecommendMealAiResponse])
async def recommend_meal(request: RecommendMealAiRequest) -> ApiResponse[RecommendMealAiResponse]:
    data = recommend_meals(request)
    return ApiResponse(success=True, message="ok", data=data, errors=None)


@router.post("/recommend-meals/v2", response_model=RecommendMealV2Response)
async def recommend_meal_v2(request: RecommendMealV2Request) -> RecommendMealV2Response:
    if request.contractVersion != "1":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Unsupported contractVersion")
    return recommend_meals_v2(request)


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


@router.post(
    "/check-today-menu-completion",
    response_model=ApiResponse[TodayMenuCompletionAiResponse],
)
async def check_today_menu_completion_route(
    request: TodayMenuCompletionAiRequest,
) -> ApiResponse[TodayMenuCompletionAiResponse]:
    data = check_today_menu_completion(request)
    return ApiResponse(success=True, message="ok", data=data, errors=None)
