import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.embedding import router as embedding_router
from app.api.routes.health import router as health_router
from app.api.routes.recommendation import router as recommendation_router
from app.api.routes.pantry_import import router as pantry_import_router

app = FastAPI(title="ZPantry AI Service", version="0.1.0")
logger = logging.getLogger("uvicorn.error")

allowed_origins = [value.strip() for value in os.getenv("AI_CORS_ALLOWED_ORIGINS", "").split(",") if value.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
    )


@app.middleware("http")
async def log_request_metadata(request: Request, call_next):
    """Diagnose service integration without recording request content or secrets."""
    logger.info(
        "AI request: method=%s path=%s content_type=%s content_length=%s",
        request.method,
        request.url.path,
        request.headers.get("content-type"),
        request.headers.get("content-length"),
    )
    if request.method == "OPTIONS" and request.url.path == "/ai/health":
        from fastapi.responses import Response
        return Response(status_code=204, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        })
    response = await call_next(request)
    if request.url.path == "/ai/health":
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response

app.include_router(health_router, prefix="/ai", tags=["health"])
app.include_router(recommendation_router, prefix="/ai", tags=["recommendation"])
app.include_router(embedding_router, prefix="/ai", tags=["embedding"])
app.include_router(pantry_import_router, prefix="/ai", tags=["pantry-import"])

