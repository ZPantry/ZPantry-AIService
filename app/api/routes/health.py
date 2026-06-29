from fastapi import APIRouter

from app.schemas.common_schema import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    return ApiResponse(success=True, message="ok", data={"status": "healthy"}, errors=None)

