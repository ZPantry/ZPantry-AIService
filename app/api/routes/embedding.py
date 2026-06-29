from fastapi import APIRouter

from app.schemas.common_schema import ApiResponse
from app.schemas.embedding_schema import (
    EmbedIngredientAiRequest,
    EmbedRecipeAiRequest,
    EmbeddingAiResponse,
)
from app.services.embedding_service import build_embedding

router = APIRouter()


@router.post("/embed-ingredient", response_model=ApiResponse[EmbeddingAiResponse])
async def embed_ingredient(request: EmbedIngredientAiRequest) -> ApiResponse[EmbeddingAiResponse]:
    embedding = build_embedding(f"{request.ingredientId}:{request.normalizedName}")
    return ApiResponse(
        success=True,
        message="ok",
        data=EmbeddingAiResponse(
            ingredientId=request.ingredientId,
            embedding=embedding,
            dimension=len(embedding),
        ),
        errors=None,
    )


@router.post("/embed-recipe", response_model=ApiResponse[EmbeddingAiResponse])
async def embed_recipe(request: EmbedRecipeAiRequest) -> ApiResponse[EmbeddingAiResponse]:
    joined = "|".join([request.recipeId, request.name, request.description or "", *request.ingredientNames, request.instructionText or ""])
    embedding = build_embedding(joined)
    return ApiResponse(
        success=True,
        message="ok",
        data=EmbeddingAiResponse(
            recipeId=request.recipeId,
            embedding=embedding,
            dimension=len(embedding),
        ),
        errors=None,
    )

