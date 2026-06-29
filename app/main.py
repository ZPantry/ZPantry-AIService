from fastapi import FastAPI

from app.api.routes.embedding import router as embedding_router
from app.api.routes.health import router as health_router
from app.api.routes.recommendation import router as recommendation_router

app = FastAPI(title="ZPantry AI Service", version="0.1.0")

app.include_router(health_router, prefix="/ai", tags=["health"])
app.include_router(recommendation_router, prefix="/ai", tags=["recommendation"])
app.include_router(embedding_router, prefix="/ai", tags=["embedding"])

