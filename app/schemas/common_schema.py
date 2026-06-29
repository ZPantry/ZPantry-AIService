from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiErrorDetail(BaseModel):
    field: str = ""
    code: str = ""
    message: str = ""


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str = ""
    data: T | None = None
    errors: list[ApiErrorDetail] | None = None
    traceId: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)


class PagedResponse(ApiResponse[list[T]], Generic[T]):
    pageIndex: int = 1
    pageSize: int = 10
    totalItems: int = 0
    totalPages: int = 0
    hasNextPage: bool = False
    hasPreviousPage: bool = False
