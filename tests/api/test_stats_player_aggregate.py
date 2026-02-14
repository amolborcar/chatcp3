from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.db.base import Base
from src.db.models import Game, Player, PlayerGameStats, Team
from src.db.session import get_db


def _seed_stats_data(db: Session) -> None:
    db.add_all(
        [
            Team(team_id=10, team_name="Los Angeles Lakers", abbreviation="LAL", conference="West", division="Pacific", active=True),
            Team(team_id=20, team_name="Golden State Warriors", abbreviation="GSW", conference="West", division="Pacific", active=True),
            Team(team_id=30, team_name="Denver Nuggets", abbreviation="DEN", conference="West", division="Northwest", active=True),
            Player(player_id=1, full_name="Player One", first_name="Player", last_name="One", is_active=True),
            Player(player_id=2, full_name="Player Two", first_name="Player", last_name="Two", is_active=True),
            Game(
                game_id=1001,
                game_date=date(2024, 10, 24),
                season="2024-25",
                season_type="regular_season",
                home_team_id=10,
                away_team_id=20,
                game_status="final",
                game_status_text="Final",
                source_last_updated_at=datetime.utcnow(),
            ),
            Game(
                game_id=1002,
                game_date=date(2024, 10, 26),
                season="2024-25",
                season_type="regular_season",
                home_team_id=30,
                away_team_id=10,
                game_status="final",
                game_status_text="Final",
                source_last_updated_at=datetime.utcnow(),
            ),
            PlayerGameStats(
                game_id=1001,
                player_id=1,
                team_id=10,
                opponent_team_id=20,
                game_date=date(2024, 10, 24),
                season="2024-25",
                season_type="regular_season",
                is_home=True,
                started=True,
                win=True,
                minutes=Decimal("35.0"),
                points=Decimal("20"),
                rebounds=Decimal("7"),
                assists=Decimal("6"),
                steals=Decimal("1"),
                blocks=Decimal("0"),
                turnovers=Decimal("2"),
                fg_pct=Decimal("0.5000"),
                fg3_pct=Decimal("0.4000"),
                ft_pct=Decimal("0.8500"),
                plus_minus=Decimal("8"),
                source_endpoint="seed",
                data_version="v1",
                ingested_at=datetime.utcnow(),
            ),
            PlayerGameStats(
                game_id=1002,
                player_id=1,
                team_id=10,
                opponent_team_id=30,
                game_date=date(2024, 10, 26),
                season="2024-25",
                season_type="regular_season",
                is_home=False,
                started=True,
                win=False,
                minutes=Decimal("34.5"),
                points=Decimal("30"),
                rebounds=Decimal("5"),
                assists=Decimal("8"),
                steals=Decimal("2"),
                blocks=Decimal("1"),
                turnovers=Decimal("3"),
                fg_pct=Decimal("0.5500"),
                fg3_pct=Decimal("0.4200"),
                ft_pct=Decimal("0.9000"),
                plus_minus=Decimal("-4"),
                source_endpoint="seed",
                data_version="v1",
                ingested_at=datetime.utcnow(),
            ),
            PlayerGameStats(
                game_id=1002,
                player_id=2,
                team_id=30,
                opponent_team_id=10,
                game_date=date(2024, 10, 26),
                season="2024-25",
                season_type="regular_season",
                is_home=True,
                started=True,
                win=True,
                minutes=Decimal("31.0"),
                points=Decimal("10"),
                rebounds=Decimal("10"),
                assists=Decimal("3"),
                steals=Decimal("0"),
                blocks=Decimal("2"),
                turnovers=Decimal("1"),
                fg_pct=Decimal("0.4700"),
                fg3_pct=Decimal("0.3300"),
                ft_pct=Decimal("0.8000"),
                plus_minus=Decimal("6"),
                source_endpoint="seed",
                data_version="v1",
                ingested_at=datetime.utcnow(),
            ),
        ]
    )
    db.commit()


def _build_test_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        _seed_stats_data(db)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_player_aggregate_query_returns_seeded_aggregates():
    client = _build_test_client()
    try:
        response = client.post(
            "/v1/stats/player-aggregate/query",
            json={
                "entity": "player_aggregate",
                "aggregations": [{"metric": "points", "op": "avg"}],
                "dimensions": ["player_id"],
                "filters": {"seasons": ["2024-25"]},
                "sort": [{"field": "value", "direction": "desc"}],
                "limit": 10,
                "offset": 0,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["rows"][0]["player_id"] == 1
        assert payload["rows"][0]["value"] == 25.0
        assert payload["rows"][1]["player_id"] == 2
        assert payload["rows"][1]["value"] == 10.0
    finally:
        app.dependency_overrides.clear()


def test_player_aggregate_query_rejects_unsupported_metric():
    client = _build_test_client()
    try:
        response = client.post(
            "/v1/stats/player-aggregate/query",
            json={
                "entity": "player_aggregate",
                "aggregations": [{"metric": "usage_rate", "op": "avg"}],
                "dimensions": ["player_id"],
                "filters": {"seasons": ["2024-25"]},
                "limit": 10,
                "offset": 0,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
