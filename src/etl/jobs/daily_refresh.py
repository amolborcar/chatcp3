"""Budget-mode daily refresh entrypoint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from src.core.config import get_settings
from src.db.models import DataQualityRun
from src.db.session import SessionLocal
from src.etl.loaders import upsert_player_game_logs, upsert_players, upsert_teams


def run(season: str | None = None, max_players: int | None = None) -> None:
    """Execute a lightweight daily refresh workflow."""
    settings = get_settings()
    season = season or settings.ingest_default_season
    max_players = max_players or settings.ingest_max_players

    # Lazy import to avoid expensive nba_api endpoint import cost during module import.
    print(f"[{datetime.utcnow().isoformat()}] Loading NBA client...")
    from src.data_collection.nba_api_client import NBAApiClient

    client = NBAApiClient(
        delay_seconds=settings.ingest_api_delay_seconds,
        timeout_seconds=settings.ingest_api_timeout_seconds,
        max_retries=settings.ingest_api_max_retries,
    )

    print(f"[{datetime.utcnow().isoformat()}] Refresh started (season={season}, max_players={max_players})")
    print(f"[{datetime.utcnow().isoformat()}] Fetching teams...")
    teams = client.get_all_teams()
    print(f"[{datetime.utcnow().isoformat()}] Fetching players...")
    players = client.get_all_players()
    if settings.ingest_active_only:
        players = [p for p in players if p.get("is_active")]
    players = players[:max_players]

    with SessionLocal() as db:
        quality_run = DataQualityRun(
            started_at=datetime.utcnow(),
            status="running",
            checks_passed=0,
            checks_failed=0,
            details_json="{}",
        )
        db.add(quality_run)
        db.flush()

        team_count = upsert_teams(db, teams)
        player_count = upsert_players(db, players)
        team_abbrev_to_id = {t.get("abbreviation"): int(t.get("id")) for t in teams if t.get("abbreviation") and t.get("id")}

        total_games = 0
        total_stats = 0
        for index, player in enumerate(players, start=1):
            player_id = player.get("id")
            if not player_id:
                continue
            print(f"[{datetime.utcnow().isoformat()}] Fetching logs for player {player_id} ({index}/{len(players)})...")
            logs = client.get_player_game_log(player_id=player_id, season=season)
            games_written, stats_written = upsert_player_game_logs(
                db=db,
                logs=logs,
                season=season,
                team_abbrev_to_id=team_abbrev_to_id,
            )
            total_games += games_written
            total_stats += stats_written

        checks_passed = 0
        checks_failed = 0
        if team_count > 0:
            checks_passed += 1
        else:
            checks_failed += 1
        if player_count > 0:
            checks_passed += 1
        else:
            checks_failed += 1
        if total_stats > 0:
            checks_passed += 1
        else:
            checks_failed += 1

        quality_run.status = "success" if checks_failed == 0 else "warning"
        quality_run.finished_at = datetime.utcnow()
        quality_run.checks_passed = checks_passed
        quality_run.checks_failed = checks_failed
        quality_run.details_json = json.dumps(
            {
                "season": season,
                "max_players": max_players,
                "teams_upserted": team_count,
                "players_upserted": player_count,
                "games_upserted": total_games,
                "player_game_stats_upserted": total_stats,
            }
        )

        db.commit()

    print(
        f"[{datetime.utcnow().isoformat()}] Refresh done "
        f"(teams={team_count}, players={player_count}, games={total_games}, player_game_stats={total_stats})"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run budget-mode daily refresh.")
    parser.add_argument("--season", default=None, help='Season format "YYYY-YY", e.g. "2024-25".')
    parser.add_argument("--max-players", type=int, default=None, help="Maximum players to ingest per run.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(season=args.season, max_players=args.max_players)
