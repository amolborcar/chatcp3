"""Health and status routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.schemas import HealthResponse
from src.db.models import DataQualityRun, PlayerGameStats
from src.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Simple health endpoint for probes and smoke tests."""

    return HealthResponse(status="ok", service="nba-stats-assistant")


@router.get("/data/freshness")
def get_data_freshness(db: Session = Depends(get_db)) -> dict:
    """Return basic data freshness metadata from fact and quality tables."""
    latest_ingested = db.execute(select(func.max(PlayerGameStats.ingested_at))).scalar_one_or_none()
    latest_game_date = db.execute(select(func.max(PlayerGameStats.game_date))).scalar_one_or_none()
    latest_quality_run = db.execute(select(DataQualityRun).order_by(DataQualityRun.run_id.desc()).limit(1)).scalar_one_or_none()

    freshness_status = "empty" if latest_ingested is None else "ready"
    quality_payload = None
    if latest_quality_run:
        quality_payload = {
            "run_id": latest_quality_run.run_id,
            "status": latest_quality_run.status,
            "started_at": latest_quality_run.started_at,
            "finished_at": latest_quality_run.finished_at,
            "checks_passed": latest_quality_run.checks_passed,
            "checks_failed": latest_quality_run.checks_failed,
        }

    return {
        "status": freshness_status,
        "latest_ingested_at": latest_ingested,
        "latest_game_date": latest_game_date,
        "latest_quality_run": quality_payload,
    }
