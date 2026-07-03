from pydantic import BaseModel, Field


class IngredientItem(BaseModel):
    ingredientId: str | None = None
    name: str
    quantity: float | None = None
    unit: str | None = None


class CandidateRecipeItem(BaseModel):
    recipeId: str
    recipeName: str
    ingredientNames: list[str] = Field(default_factory=list)
    instructionText: str | None = None


class RecommendMealAiRequest(BaseModel):
    userId: str
    inputIngredientText: str
    ingredients: list[IngredientItem] = Field(default_factory=list)
    candidateRecipes: list[CandidateRecipeItem] = Field(default_factory=list)
    topK: int = 5


class RecommendMealAiItem(BaseModel):
    recipeId: str
    recipeName: str
    matchScore: float
    missingIngredientCount: int
    missingIngredientNames: list[str] = Field(default_factory=list)
    reason: str
    rank: int


class RecommendMealAiResponse(BaseModel):
    items: list[RecommendMealAiItem] = Field(default_factory=list)


class MissingIngredientAiRequest(BaseModel):
    recipeId: str
    recipeName: str
    requiredIngredients: list[str] = Field(default_factory=list)
    userIngredients: list[str] = Field(default_factory=list)


class MissingIngredientAiResponse(BaseModel):
    recipeId: str
    missingIngredients: list[str] = Field(default_factory=list)


class MealIngredientItem(BaseModel):
    ingredientId: str | None = None
    name: str
    quantity: float | None = None
    unit: str | None = None


class MealInfo(BaseModel):
    mealId: str
    mealName: str


class MealIngredientCheckAiRequest(BaseModel):
    userId: str
    meal: MealInfo
    requiredIngredients: list[MealIngredientItem] = Field(default_factory=list)
    fridgeIngredients: list[MealIngredientItem] = Field(default_factory=list)


class MealIngredientCheckAiResponse(BaseModel):
    mealId: str
    mealName: str
    availableIngredients: list[MealIngredientItem] = Field(default_factory=list)
    missingIngredients: list[MealIngredientItem] = Field(default_factory=list)
    note: str | None = None


class TodayMenuCompletionAiMeal(BaseModel):
    mealId: str
    mealName: str


class TodayMenuCompletionAiRequest(BaseModel):
    userId: str
    meal: TodayMenuCompletionAiMeal
    requiredIngredients: list[MealIngredientItem] = Field(default_factory=list)
    pantryIngredients: list[MealIngredientItem] = Field(default_factory=list)


class TodayMenuCompletionAiResponse(BaseModel):
    mealId: str
    mealName: str
    availableIngredients: list[MealIngredientItem] = Field(default_factory=list)
    missingIngredients: list[MealIngredientItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    note: str | None = None
