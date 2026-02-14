"""Core relational models for budget-mode V1."""

from datetime import date, datetime

from sqlalchemy import BIGINT, BOOLEAN, DATE, INTEGER, NUMERIC, TEXT, TIMESTAMP, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Team(Base):
    __tablename__ = "dim_team"

    team_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    team_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(8), nullable=False)
    conference: Mapped[str | None] = mapped_column(String(16))
    division: Mapped[str | None] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(BOOLEAN, default=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Player(Base):
    __tablename__ = "dim_player"

    player_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    full_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    first_name: Mapped[str | None] = mapped_column(TEXT)
    last_name: Mapped[str | None] = mapped_column(TEXT)
    is_active: Mapped[bool | None] = mapped_column(BOOLEAN)
    primary_team_id: Mapped[int | None] = mapped_column(ForeignKey("dim_team.team_id"))
    first_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Game(Base):
    __tablename__ = "dim_game"

    game_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    game_date: Mapped[date] = mapped_column(DATE, nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    season_type: Mapped[str] = mapped_column(String(32), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("dim_team.team_id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("dim_team.team_id"), nullable=False)
    home_score: Mapped[int | None] = mapped_column(INTEGER)
    away_score: Mapped[int | None] = mapped_column(INTEGER)
    game_status: Mapped[str | None] = mapped_column(String(32))
    game_status_text: Mapped[str | None] = mapped_column(TEXT)
    source_last_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PlayerGameStats(Base):
    __tablename__ = "fact_player_game_stats"

    game_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("dim_game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("dim_player.player_id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("dim_team.team_id"), nullable=False)
    opponent_team_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("dim_team.team_id"), nullable=False)
    game_date: Mapped[date] = mapped_column(DATE, nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    season_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_home: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    started: Mapped[bool | None] = mapped_column(BOOLEAN)
    win: Mapped[bool | None] = mapped_column(BOOLEAN)
    minutes: Mapped[float | None] = mapped_column(NUMERIC(5, 2))
    points: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    rebounds: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    assists: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    steals: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    blocks: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    turnovers: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    fg_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    fg3_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    ft_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    plus_minus: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    source_endpoint: Mapped[str] = mapped_column(TEXT, nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class TeamGameStats(Base):
    __tablename__ = "fact_team_game_stats"

    game_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("dim_game.game_id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("dim_team.team_id"), primary_key=True)
    opponent_team_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("dim_team.team_id"), nullable=False)
    game_date: Mapped[date] = mapped_column(DATE, nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    season_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_home: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    win: Mapped[bool | None] = mapped_column(BOOLEAN)
    points: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    rebounds: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    assists: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    steals: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    blocks: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    turnovers: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    fg_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    fg3_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    ft_pct: Mapped[float | None] = mapped_column(NUMERIC(6, 4))
    pace: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    offensive_rating: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    defensive_rating: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    net_rating: Mapped[float | None] = mapped_column(NUMERIC(6, 2))
    source_endpoint: Mapped[str] = mapped_column(TEXT, nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DataQualityRun(Base):
    __tablename__ = "data_quality_run"

    run_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    checks_passed: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    checks_failed: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    details_json: Mapped[str] = mapped_column(TEXT, nullable=False, default="{}")

