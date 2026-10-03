from pydantic import BaseModel, Field
from pydantic import ConfigDict


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


class RecommendationContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RecommendationProfileV2(RecommendationContractModel):
    targetKcalPerMeal: float | None = None
    proteinGPerMeal: float | None = None
    diet: str | None = None
    goals: list[str] = Field(default_factory=list)
    maxCookTimeMinutes: int | None = None


class PantryIngredientV2(RecommendationContractModel):
    ingredientId: str
    name: str
    expiringSoon: bool = False


class CandidateRecipeV2(RecommendationContractModel):
    recipeId: str
    recipeName: str
    mainIngredients: list[str] = Field(default_factory=list)
    kcalPerServing: float | None = None
    proteinG: float | None = None
    cookTimeMinutes: int | None = None
    pantryMatchRatio: float = 0.0
    missingIngredients: list[str] = Field(default_factory=list)
    expiringSoonUsed: bool = False
    descriptionSnippet: str = Field(default="", max_length=300)


class RecommendMealV2Request(RecommendationContractModel):
    requestId: str
    contractVersion: str
    mode: str
    profile: RecommendationProfileV2
    pantryIngredients: list[PantryIngredientV2] = Field(default_factory=list)
    candidateRecipes: list[CandidateRecipeV2] = Field(default_factory=list, max_length=15)
    topK: int = Field(default=5, ge=1, le=20)
    withAdvice: bool = True


class RecommendationComponentsV2(RecommendationContractModel):
    pantryMatch: float | None = None
    nutritionFit: float | None = None
    preference: float | None = None
    practical: float | None = None


class RecommendMealV2Item(RecommendationContractModel):
    recipeId: str
    rank: int
    score: float
    components: RecommendationComponentsV2
    advice: str | None = None


class RecommendMealV2Response(RecommendationContractModel):
    requestId: str
    modelVersion: str = "rank-v1"
    llmApplied: bool = False
    items: list[RecommendMealV2Item] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=lambda: {"tokens": 0, "latencyMs": 0})


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
