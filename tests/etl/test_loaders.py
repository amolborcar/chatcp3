from decimal import Decimal

from src.etl.loaders import _parse_game_date, _parse_matchup, _resolve_team_id, _season_type_from_season_id, _to_decimal


def test_to_decimal_minutes_clock_format():
    value = _to_decimal("35:30")
    assert value == Decimal("35.5")


def test_parse_game_date():
    parsed = _parse_game_date("OCT 24, 2024")
    assert parsed is not None
    assert parsed.isoformat() == "2024-10-24"


def test_parse_matchup():
    is_home, opponent = _parse_matchup("LAL vs. GSW")
    assert is_home is True
    assert opponent == "GSW"

    is_home, opponent = _parse_matchup("LAL @ GSW")
    assert is_home is False
    assert opponent == "GSW"


def test_season_type_from_season_id():
    assert _season_type_from_season_id("42024") == "playoffs"
    assert _season_type_from_season_id("22024") == "regular_season"


def test_resolve_team_id_uses_team_abbreviation_when_team_id_missing():
    log = {"TEAM_ABBREVIATION": "LAL", "MATCHUP": "LAL vs. GSW"}
    team_id = _resolve_team_id(log, {"LAL": 1610612747, "GSW": 1610612744})
    assert team_id == 1610612747
