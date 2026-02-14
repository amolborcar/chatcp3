"""Data loading helpers for NBA API -> Postgres upserts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models import Game, Player, PlayerGameStats, Team


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and ":" in value:
        try:
            minutes, seconds = value.split(":", maxsplit=1)
            return Decimal(minutes) + (Decimal(seconds) / Decimal(60))
        except (ValueError, ArithmeticError):
            return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None


def _parse_game_date(raw_date: str | None) -> datetime.date | None:
    if not raw_date:
        return None
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw_date.title(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_matchup(matchup: str | None) -> tuple[bool, str | None]:
    if not matchup:
        return True, None
    if " vs. " in matchup:
        return True, matchup.split(" vs. ", maxsplit=1)[1].strip().upper()
    if " @ " in matchup:
        return False, matchup.split(" @ ", maxsplit=1)[1].strip().upper()
    return True, None


def _season_type_from_season_id(season_id: str | int | None) -> str:
    raw = str(season_id) if season_id is not None else ""
    if raw.startswith("4"):
        return "playoffs"
    return "regular_season"


def _resolve_team_id(log: dict[str, Any], team_abbrev_to_id: dict[str, int]) -> int | None:
    team_id = _to_int(log.get("Team_ID") or log.get("TEAM_ID"))
    if team_id:
        return team_id

    team_abbr = str(log.get("TEAM_ABBREVIATION") or "").strip().upper()
    if team_abbr:
        return team_abbrev_to_id.get(team_abbr)

    matchup = str(log.get("MATCHUP") or "")
    if " vs. " in matchup:
        team_abbr = matchup.split(" vs. ", maxsplit=1)[0].strip().upper()
        return team_abbrev_to_id.get(team_abbr)
    if " @ " in matchup:
        team_abbr = matchup.split(" @ ", maxsplit=1)[0].strip().upper()
        return team_abbrev_to_id.get(team_abbr)
    return None


def upsert_teams(db: Session, teams: list[dict[str, Any]]) -> int:
    if not teams:
        return 0
    rows = [
        {
            "team_id": t.get("id"),
            "team_name": t.get("full_name"),
            "abbreviation": t.get("abbreviation") or "",
            "conference": t.get("conference"),
            "division": t.get("division"),
            "active": True,
        }
        for t in teams
        if t.get("id") and t.get("full_name")
    ]
    if not rows:
        return 0
    stmt = insert(Team).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Team.team_id],
        set_={
            "team_name": stmt.excluded.team_name,
            "abbreviation": stmt.excluded.abbreviation,
            "conference": stmt.excluded.conference,
            "division": stmt.excluded.division,
            "updated_at": datetime.utcnow(),
        },
    )
    db.execute(stmt)
    return len(rows)


def upsert_players(db: Session, players: list[dict[str, Any]]) -> int:
    if not players:
        return 0
    rows = []
    for p in players:
        full_name = p.get("full_name")
        if not p.get("id") or not full_name:
            continue
        first, *last = full_name.split(" ")
        rows.append(
            {
                "player_id": p.get("id"),
                "full_name": full_name,
                "first_name": first,
                "last_name": " ".join(last) if last else None,
                "is_active": p.get("is_active"),
            }
        )
    if not rows:
        return 0
    stmt = insert(Player).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Player.player_id],
        set_={
            "full_name": stmt.excluded.full_name,
            "first_name": stmt.excluded.first_name,
            "last_name": stmt.excluded.last_name,
            "is_active": stmt.excluded.is_active,
            "updated_at": datetime.utcnow(),
        },
    )
    db.execute(stmt)
    return len(rows)


def upsert_player_game_logs(
    db: Session,
    logs: list[dict[str, Any]],
    season: str,
    team_abbrev_to_id: dict[str, int],
) -> tuple[int, int]:
    if not logs:
        return 0, 0

    games_rows = []
    stat_rows = []
    now = datetime.utcnow()

    for log in logs:
        game_id = _to_int(log.get("Game_ID") or log.get("GAME_ID"))
        player_id = _to_int(log.get("Player_ID") or log.get("PLAYER_ID") or log.get("player_id"))
        team_id = _resolve_team_id(log, team_abbrev_to_id)
        game_date = _parse_game_date(log.get("GAME_DATE"))
        matchup = log.get("MATCHUP")
        is_home, opponent_abbr = _parse_matchup(matchup)
        opponent_team_id = team_abbrev_to_id.get(opponent_abbr) if opponent_abbr else None

        if not game_id or not player_id or not team_id or not opponent_team_id or not game_date:
            continue

        home_team_id = team_id if is_home else opponent_team_id
        away_team_id = opponent_team_id if is_home else team_id
        season_type = _season_type_from_season_id(log.get("SEASON_ID"))
        wl = str(log.get("WL", "")).upper()
        started = bool(log.get("START_POSITION"))

        games_rows.append(
            {
                "game_id": game_id,
                "game_date": game_date,
                "season": season,
                "season_type": season_type,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "game_status": "final",
                "game_status_text": "Final",
                "source_last_updated_at": now,
            }
        )
        stat_rows.append(
            {
                "game_id": game_id,
                "player_id": player_id,
                "team_id": team_id,
                "opponent_team_id": opponent_team_id,
                "game_date": game_date,
                "season": season,
                "season_type": season_type,
                "is_home": is_home,
                "started": started,
                "win": True if wl == "W" else (False if wl == "L" else None),
                "minutes": _to_decimal(log.get("MIN")),
                "points": _to_decimal(log.get("PTS")),
                "rebounds": _to_decimal(log.get("REB")),
                "assists": _to_decimal(log.get("AST")),
                "steals": _to_decimal(log.get("STL")),
                "blocks": _to_decimal(log.get("BLK")),
                "turnovers": _to_decimal(log.get("TOV")),
                "fg_pct": _to_decimal(log.get("FG_PCT")),
                "fg3_pct": _to_decimal(log.get("FG3_PCT")),
                "ft_pct": _to_decimal(log.get("FT_PCT")),
                "plus_minus": _to_decimal(log.get("PLUS_MINUS")),
                "source_endpoint": "playergamelog",
                "data_version": "v1",
                "ingested_at": now,
            }
        )

    if games_rows:
        stmt_games = insert(Game).values(games_rows)
        stmt_games = stmt_games.on_conflict_do_update(
            index_elements=[Game.game_id],
            set_={
                "game_date": stmt_games.excluded.game_date,
                "season": stmt_games.excluded.season,
                "season_type": stmt_games.excluded.season_type,
                "home_team_id": stmt_games.excluded.home_team_id,
                "away_team_id": stmt_games.excluded.away_team_id,
                "game_status": stmt_games.excluded.game_status,
                "game_status_text": stmt_games.excluded.game_status_text,
                "source_last_updated_at": stmt_games.excluded.source_last_updated_at,
            },
        )
        db.execute(stmt_games)

    if stat_rows:
        stmt_stats = insert(PlayerGameStats).values(stat_rows)
        stmt_stats = stmt_stats.on_conflict_do_update(
            index_elements=[PlayerGameStats.game_id, PlayerGameStats.player_id],
            set_={
                "team_id": stmt_stats.excluded.team_id,
                "opponent_team_id": stmt_stats.excluded.opponent_team_id,
                "game_date": stmt_stats.excluded.game_date,
                "season": stmt_stats.excluded.season,
                "season_type": stmt_stats.excluded.season_type,
                "is_home": stmt_stats.excluded.is_home,
                "started": stmt_stats.excluded.started,
                "win": stmt_stats.excluded.win,
                "minutes": stmt_stats.excluded.minutes,
                "points": stmt_stats.excluded.points,
                "rebounds": stmt_stats.excluded.rebounds,
                "assists": stmt_stats.excluded.assists,
                "steals": stmt_stats.excluded.steals,
                "blocks": stmt_stats.excluded.blocks,
                "turnovers": stmt_stats.excluded.turnovers,
                "fg_pct": stmt_stats.excluded.fg_pct,
                "fg3_pct": stmt_stats.excluded.fg3_pct,
                "ft_pct": stmt_stats.excluded.ft_pct,
                "plus_minus": stmt_stats.excluded.plus_minus,
                "source_endpoint": stmt_stats.excluded.source_endpoint,
                "data_version": stmt_stats.excluded.data_version,
                "ingested_at": stmt_stats.excluded.ingested_at,
            },
        )
        db.execute(stmt_stats)

    return len(games_rows), len(stat_rows)
