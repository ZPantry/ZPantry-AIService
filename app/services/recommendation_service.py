from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    MealIngredientCheckAiRequest,
    MealIngredientCheckAiResponse,
    MealIngredientItem,
    RecommendMealAiItem,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
)
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
