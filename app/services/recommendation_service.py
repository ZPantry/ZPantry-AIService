from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    RecommendMealAiItem,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
)
from app.utils.normalizer import tokenize_ingredient_text


def recommend_meals(request: RecommendMealAiRequest) -> RecommendMealAiResponse:
    user_tokens = tokenize_ingredient_text([request.inputIngredientText]) | tokenize_ingredient_text(
        [item.name for item in request.ingredients]
    )
    items: list[RecommendMealAiItem] = []
    for recipe in request.candidateRecipes:
        recipe_tokens = tokenize_ingredient_text(recipe.ingredientNames)
        overlap = len(user_tokens & recipe_tokens)
        total = max(len(recipe_tokens), 1)
        score = round(overlap / total, 3)
        missing = sorted(recipe_tokens - user_tokens)
        items.append(
            RecommendMealAiItem(
                recipeId=recipe.recipeId,
                recipeName=recipe.recipeName,
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
