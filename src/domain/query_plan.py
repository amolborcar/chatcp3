"""Normalized query contract for deterministic and chat flows."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PLAYER_GAME = "player_game"
    PLAYER_AGGREGATE = "player_aggregate"
    TEAM_AGGREGATE = "team_aggregate"
    LEADERBOARD = "leaderboard"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SeasonType(str, Enum):
    REGULAR = "regular_season"
    PLAYOFFS = "playoffs"
    ANY = "any"


class HomeAway(str, Enum):
    HOME = "home"
    AWAY = "away"
    ANY = "any"


class GameResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    ANY = "any"


class AggregationSpec(BaseModel):
    metric: str
    op: str
    alias: str | None = None


class SortSpec(BaseModel):
    field: str
    direction: SortDirection = SortDirection.DESC


class FilterSpec(BaseModel):
    player_ids: list[int] = Field(default_factory=list)
    team_ids: list[int] = Field(default_factory=list)
    opponent_team_ids: list[int] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)
    season_type: SeasonType = SeasonType.ANY
    date_from: date | None = None
    date_to: date | None = None
    home_away: HomeAway = HomeAway.ANY
    started_only: bool = False
    min_minutes: float = 0
    game_result: GameResult = GameResult.ANY


class QueryPlan(BaseModel):
    entity: EntityType
    metrics: list[str] = Field(default_factory=list)
    aggregations: list[AggregationSpec] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: FilterSpec = Field(default_factory=FilterSpec)
    sort: list[SortSpec] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0

