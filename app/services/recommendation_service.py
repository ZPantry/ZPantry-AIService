from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    MealIngredientCheckAiRequest,
    MealIngredientCheckAiResponse,
    MealIngredientItem,
    TodayMenuCompletionAiRequest,
    TodayMenuCompletionAiResponse,
    RecommendMealAiItem,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
    RecommendMealV2Request,
    RecommendMealV2Response,
    RecommendMealV2Item,
    RecommendationComponentsV2,
)
import time
from app.utils.normalizer import normalize_text, tokenize_ingredient_text


def recommend_meals(request: RecommendMealAiRequest) -> RecommendMealAiResponse:
    user_tokens = tokenize_ingredient_text([request.inputIngredientText]) | tokenize_ingredient_text(
        [item.name for item in request.ingredients]
    )
    items: list[RecommendMealAiItem] = []

    for recipe in request.candidateRecipes:
        recipe_id = recipe.recipeId
        recipe_name = recipe.recipeName
        ingredient_names = recipe.ingredientNames
        recipe_tokens = tokenize_ingredient_text(ingredient_names)
        overlap = len(user_tokens & recipe_tokens)
        total = max(len(recipe_tokens), 1)
        score = round(overlap / total, 3)
        missing = sorted(recipe_tokens - user_tokens)
        items.append(
            RecommendMealAiItem(
                recipeId=recipe_id,
                recipeName=recipe_name,
                matchScore=score,
                missingIngredientCount=len(missing),
                missingIngredientNames=missing[:5],
                reason=f"Matched {overlap} of {total} required ingredients using mock overlap scoring.",
                rank=0,
            )
        )

    ranked_items = sorted(
        items,
        key=lambda item: (item.matchScore, -item.missingIngredientCount, item.recipeName.lower()),
        reverse=True,
    )[: max(request.topK, 0)]

    for index, item in enumerate(ranked_items, start=1):
        item.rank = index

    return RecommendMealAiResponse(items=ranked_items)


def recommend_meals_v2(request: RecommendMealV2Request) -> RecommendMealV2Response:
    """Pure deterministic ranker. It never invents recipes, nutrition, or missing ingredients."""
    started = time.perf_counter()
    weighted: list[tuple[float, RecommendMealV2Item]] = []
    for recipe in request.candidateRecipes:
        components: dict[str, float] = {}
        if request.mode != "PROFILE_BASED":
            components["pantryMatch"] = min(1.0, max(0.0, recipe.pantryMatchRatio + (0.05 if recipe.expiringSoonUsed else 0.0)))
        if recipe.kcalPerServing is not None and request.profile.targetKcalPerMeal:
            target = request.profile.targetKcalPerMeal
            components["nutritionFit"] = max(0.0, 1.0 - abs(recipe.kcalPerServing - target) / max(target, 1.0))
        if recipe.cookTimeMinutes is not None and request.profile.maxCookTimeMinutes:
            limit = request.profile.maxCookTimeMinutes
            components["practical"] = 1.0 if recipe.cookTimeMinutes <= limit else max(0.0, 1.0 - (recipe.cookTimeMinutes - limit) / max(limit, 1))
        components["preference"] = 1.0 if "QUICK_COOK" in request.profile.goals and components.get("practical") == 1.0 else 0.5
        score = sum(components.values()) / len(components)
        weighted.append((score, RecommendMealV2Item(recipeId=recipe.recipeId, rank=0, score=round(score, 4),
            components=RecommendationComponentsV2(**components), advice=None)))
    ranked = sorted(weighted, key=lambda value: (-value[0], value[1].recipeId))[:request.topK]
    items = [item.model_copy(update={"rank": index}) for index, (_, item) in enumerate(ranked, start=1)]
    return RecommendMealV2Response(requestId=request.requestId, items=items,
        usage={"tokens": 0, "latencyMs": round((time.perf_counter() - started) * 1000)})


def suggest_missing_ingredients(request: MissingIngredientAiRequest) -> MissingIngredientAiResponse:
    required = tokenize_ingredient_text(request.requiredIngredients)
    owned = tokenize_ingredient_text(request.userIngredients)
    missing = sorted(required - owned)
    return MissingIngredientAiResponse(recipeId=request.recipeId, missingIngredients=missing)


def check_meal_ingredients(request: MealIngredientCheckAiRequest) -> MealIngredientCheckAiResponse:
    fridge_by_id = {
        item.ingredientId: item
        for item in request.fridgeIngredients
        if item.ingredientId
    }
    fridge_names = {
        normalize_text(item.name)
        for item in request.fridgeIngredients
        if normalize_text(item.name)
    }

    available: list[MealIngredientItem] = []
    missing: list[MealIngredientItem] = []

    for ingredient in request.requiredIngredients:
        has_item = False

        if ingredient.ingredientId:
            fridge_item = fridge_by_id.get(ingredient.ingredientId)
            has_item = fridge_item is not None

        if not has_item:
            normalized_name = normalize_text(ingredient.name)
            if normalized_name:
                has_item = normalized_name in fridge_names

        if has_item:
            available.append(ingredient)
        else:
            missing.append(ingredient)

    note = (
        "You already have all required ingredients for this meal."
        if not missing
        else f"You are missing {len(missing)} ingredient(s) for this meal."
    )

    return MealIngredientCheckAiResponse(
        mealId=request.meal.mealId,
        mealName=request.meal.mealName,
        availableIngredients=available,
        missingIngredients=missing,
        note=note,
    )


def check_today_menu_completion(
    request: TodayMenuCompletionAiRequest,
) -> TodayMenuCompletionAiResponse:
    pantry_by_id = {
        item.ingredientId: item
        for item in request.pantryIngredients
        if item.ingredientId
    }
    pantry_names = {
        normalize_text(item.name)
        for item in request.pantryIngredients
        if normalize_text(item.name)
    }

    available: list[MealIngredientItem] = []
    missing: list[MealIngredientItem] = []
    warnings: list[str] = []

    for ingredient in request.requiredIngredients:
        has_item = False

        if ingredient.ingredientId:
            pantry_item = pantry_by_id.get(ingredient.ingredientId)
            has_item = pantry_item is not None

        if not has_item:
            normalized_name = normalize_text(ingredient.name)
            if normalized_name:
                has_item = normalized_name in pantry_names

        if has_item and ingredient.unit:
            matched = None
            if ingredient.ingredientId:
                matched = pantry_by_id.get(ingredient.ingredientId)
            if matched and matched.unit and normalize_text(matched.unit) != normalize_text(ingredient.unit):
                warnings.append(
                    f"Unit mismatch for {ingredient.name}: pantry={matched.unit}, recipe={ingredient.unit}."
                )
                missing.append(ingredient)
                continue

        if has_item:
            available.append(ingredient)
        else:
            missing.append(ingredient)

    if warnings:
        note = "Meal can be completed, but there are unit warnings to review."
    else:
        note = (
            "You already have all required ingredients for this meal."
            if not missing
            else f"You are missing {len(missing)} ingredient(s) for this meal."
        )

    return TodayMenuCompletionAiResponse(
        mealId=request.meal.mealId,
        mealName=request.meal.mealName,
        availableIngredients=available,
        missingIngredients=missing,
        warnings=warnings,
        note=note,
    )
