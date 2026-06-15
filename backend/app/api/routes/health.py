from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response returned when the API is running."""

    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    # This tiny endpoint is useful for tests, Docker checks, and manual smoke tests.
    return HealthResponse(
        status="ok",
        service="breach-analytics-genai-backend",
    )
