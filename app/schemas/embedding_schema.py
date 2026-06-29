from pydantic import BaseModel, Field


class EmbedIngredientAiRequest(BaseModel):
    ingredientId: str
    name: str
    normalizedName: str
    category: str | None = None


class EmbedRecipeAiRequest(BaseModel):
    recipeId: str
    name: str
    description: str | None = None
    ingredientNames: list[str] = Field(default_factory=list)
    instructionText: str | None = None


class EmbeddingAiResponse(BaseModel):
    recipeId: str | None = None
    ingredientId: str | None = None
    embedding: list[float] = Field(default_factory=list)
    dimension: int = 0
