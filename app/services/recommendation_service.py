from app.schemas.recommendation_schema import (
    MissingIngredientAiRequest,
    MissingIngredientAiResponse,
    RecommendMealAiItem,
    RecommendMealAiRequest,
    RecommendMealAiResponse,
)
from app.utils.normalizer import tokenize_ingredient_text


MOCK_RECIPE_CATALOG = [
    {
        "recipeId": "00000000-0000-0000-0000-000000000101",
        "recipeName": "Trứng xào cà chua",
        "ingredientNames": ["Trứng gà", "Cà chua", "Hành tím", "Hành lá", "Nước mắm"],
        "instructionText": "Đánh trứng. Xào cà chua với hành tím, thêm trứng, nêm nước mắm và hành lá.",
    },
    {
        "recipeId": "00000000-0000-0000-0000-000000000102",
        "recipeName": "Cơm rang thịt bò",
        "ingredientNames": ["Gạo", "Thịt bò", "Trứng gà", "Cà rốt", "Tỏi"],
        "instructionText": "Xào bò với tỏi. Thêm cơm, trứng, cà rốt, nêm nước mắm rồi đảo lửa lớn.",
    },
    {
        "recipeId": "00000000-0000-0000-0000-000000000103",
        "recipeName": "Cháo gà",
        "ingredientNames": ["Gạo", "Thịt gà", "Hành lá", "Nước mắm"],
        "instructionText": "Nấu gạo với nhiều nước. Luộc gà, xé nhỏ, cho vào cháo và nêm vừa ăn.",
    },
    {
        "recipeId": "00000000-0000-0000-0000-000000000104",
        "recipeName": "Đậu hũ sốt cà chua",
        "ingredientNames": ["Đậu hũ", "Cà chua", "Hành tím", "Hành lá"],
        "instructionText": "Áp chảo đậu hũ. Nấu sốt cà chua với hành tím, cho đậu hũ vào rim thấm.",
    },
    {
        "recipeId": "00000000-0000-0000-0000-000000000105",
        "recipeName": "Canh thịt heo cà rốt",
        "ingredientNames": ["Thịt heo", "Cà rốt", "Hành tím", "Nước mắm"],
        "instructionText": "Xào sơ thịt heo với hành tím. Thêm nước và cà rốt, nấu mềm rồi nêm nước mắm.",
    },
]


def recommend_meals(request: RecommendMealAiRequest) -> RecommendMealAiResponse:
    user_tokens = tokenize_ingredient_text([request.inputIngredientText]) | tokenize_ingredient_text(
        [item.name for item in request.ingredients]
    )
    items: list[RecommendMealAiItem] = []
    candidate_recipes = request.candidateRecipes or MOCK_RECIPE_CATALOG

    for recipe in candidate_recipes:
        recipe_id = recipe.recipeId if hasattr(recipe, "recipeId") else recipe["recipeId"]
        recipe_name = recipe.recipeName if hasattr(recipe, "recipeName") else recipe["recipeName"]
        ingredient_names = recipe.ingredientNames if hasattr(recipe, "ingredientNames") else recipe["ingredientNames"]
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
