"""Health and status routes."""

from fastapi import APIRouter

from src.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Simple health endpoint for probes and smoke tests."""

    return HealthResponse(status="ok", service="nba-stats-assistant")


@router.get("/data/freshness")
def get_data_freshness() -> dict:
    """Placeholder freshness endpoint until ingestion tracking is wired."""

    return {"status": "not_ready", "message": "Freshness tracking will be populated by ingestion jobs."}

