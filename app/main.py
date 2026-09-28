import logging

from fastapi import FastAPI, Request

from app.api.routes.embedding import router as embedding_router
from app.api.routes.health import router as health_router
from app.api.routes.recommendation import router as recommendation_router
from app.api.routes.pantry_import import router as pantry_import_router

app = FastAPI(title="ZPantry AI Service", version="0.1.0")
logger = logging.getLogger("uvicorn.error")


@app.middleware("http")
async def log_request_metadata(request: Request, call_next):
    """Diagnose service integration without recording request content or secrets."""
    body = await request.body()
    logger.info(
        "AI request: method=%s path=%s content_type=%s content_length=%s body_bytes=%s",
        request.method,
        request.url.path,
        request.headers.get("content-type"),
        request.headers.get("content-length"),
        len(body),
    )
    return await call_next(request)

app.include_router(health_router, prefix="/ai", tags=["health"])
app.include_router(recommendation_router, prefix="/ai", tags=["recommendation"])
app.include_router(embedding_router, prefix="/ai", tags=["embedding"])
app.include_router(pantry_import_router, prefix="/ai", tags=["pantry-import"])

