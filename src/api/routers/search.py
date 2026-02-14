"""Search endpoints for players and teams."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import SearchResponse, SearchResult
from src.core.config import get_settings
from src.db.models import Player, Team
from src.db.session import get_db

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/players", response_model=SearchResponse)
def search_players(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SearchResponse:
    settings = get_settings()
    capped_limit = min(limit, settings.max_limit)
    query = select(Player).order_by(Player.full_name).limit(capped_limit)
    if q:
        query = query.where(Player.full_name.ilike(f"%{q}%"))
    players = db.execute(query).scalars().all()
    results = [SearchResult(id=p.player_id, name=p.full_name) for p in players]
    return SearchResponse(results=results)


@router.get("/teams", response_model=SearchResponse)
def search_teams(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SearchResponse:
    settings = get_settings()
    capped_limit = min(limit, settings.max_limit)
    query = select(Team).order_by(Team.team_name).limit(capped_limit)
    if q:
        query = query.where(Team.team_name.ilike(f"%{q}%"))
    teams = db.execute(query).scalars().all()
    results = [SearchResult(id=t.team_id, name=t.team_name, meta={"abbreviation": t.abbreviation}) for t in teams]
    return SearchResponse(results=results)


@router.get("/filters/options")
def get_filter_options(entity: str, metric: str | None = None) -> dict:
    """Static fallback options until dynamic metadata generation is added."""

    return {
        "entity": entity,
        "metric": metric,
        "season_type": ["any", "regular_season", "playoffs"],
        "home_away": ["any", "home", "away"],
        "game_result": ["any", "win", "loss"],
    }

