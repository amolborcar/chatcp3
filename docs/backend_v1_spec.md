# NBA Stats Assistant - Backend V1 Spec

## 1. Product Scope (V1)

### Goal
Build a backend that supports:
- deterministic stat retrieval APIs for UI filters
- NL (chat) queries mapped to a constrained query contract
- structured responses that always echo applied filters

### Out of Scope (V1)
- predictive modeling
- DFS lineup optimization
- cross-sport support

## 2. System Architecture

### Services
1. `api-service` (FastAPI)
- REST endpoints for search, stats, leaderboards, chat query execution
- auth, rate limiting, validation, response shaping

2. `ingestion-worker` (Celery/RQ)
- pulls NBA data on schedule
- transforms and upserts into Postgres
- emits data quality checks

3. `llm-orchestrator` (module in api-service for V1)
- NL -> query plan JSON (strict schema)
- ambiguity detection and clarification prompts
- never executes raw SQL from model output

### Core Infra
- Postgres (primary datastore)
- Redis (cache + queue broker)
- object storage optional (raw payload archive; can defer)

## 3. Data Model (Postgres)

### 3.1 Dimensions

```sql
CREATE TABLE dim_team (
  team_id            INTEGER PRIMARY KEY,
  team_name          TEXT NOT NULL,
  abbreviation       TEXT NOT NULL,
  conference         TEXT,
  division           TEXT,
  active             BOOLEAN DEFAULT TRUE,
  first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dim_player (
  player_id          INTEGER PRIMARY KEY,
  full_name          TEXT NOT NULL,
  first_name         TEXT,
  last_name          TEXT,
  is_active          BOOLEAN,
  primary_team_id    INTEGER REFERENCES dim_team(team_id),
  first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dim_game (
  game_id                    BIGINT PRIMARY KEY,
  game_date                  DATE NOT NULL,
  season                     TEXT NOT NULL, -- e.g. 2024-25
  season_type                TEXT NOT NULL, -- regular_season | playoffs
  home_team_id               INTEGER NOT NULL REFERENCES dim_team(team_id),
  away_team_id               INTEGER NOT NULL REFERENCES dim_team(team_id),
  home_score                 INTEGER,
  away_score                 INTEGER,
  game_status                TEXT,
  game_status_text           TEXT,
  arena_name                 TEXT,
  source_last_updated_at     TIMESTAMPTZ,
  ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.2 Facts

```sql
CREATE TABLE fact_player_game_stats (
  game_id                    BIGINT NOT NULL REFERENCES dim_game(game_id),
  player_id                  INTEGER NOT NULL REFERENCES dim_player(player_id),
  team_id                    INTEGER NOT NULL REFERENCES dim_team(team_id),
  opponent_team_id           INTEGER NOT NULL REFERENCES dim_team(team_id),
  game_date                  DATE NOT NULL,
  season                     TEXT NOT NULL,
  season_type                TEXT NOT NULL,
  is_home                    BOOLEAN NOT NULL,
  started                    BOOLEAN,
  win                        BOOLEAN,
  minutes                    NUMERIC(5,2),
  points                     NUMERIC(6,2),
  rebounds                   NUMERIC(6,2),
  assists                    NUMERIC(6,2),
  steals                     NUMERIC(6,2),
  blocks                     NUMERIC(6,2),
  turnovers                  NUMERIC(6,2),
  fg_made                    NUMERIC(6,2),
  fg_attempted               NUMERIC(6,2),
  fg_pct                     NUMERIC(6,4),
  fg3_made                   NUMERIC(6,2),
  fg3_attempted              NUMERIC(6,2),
  fg3_pct                    NUMERIC(6,4),
  ft_made                    NUMERIC(6,2),
  ft_attempted               NUMERIC(6,2),
  ft_pct                     NUMERIC(6,4),
  plus_minus                 NUMERIC(6,2),
  source_endpoint            TEXT NOT NULL,
  data_version               TEXT NOT NULL,
  ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (game_id, player_id)
);

CREATE TABLE fact_team_game_stats (
  game_id                    BIGINT NOT NULL REFERENCES dim_game(game_id),
  team_id                    INTEGER NOT NULL REFERENCES dim_team(team_id),
  opponent_team_id           INTEGER NOT NULL REFERENCES dim_team(team_id),
  game_date                  DATE NOT NULL,
  season                     TEXT NOT NULL,
  season_type                TEXT NOT NULL,
  is_home                    BOOLEAN NOT NULL,
  win                        BOOLEAN,
  points                     NUMERIC(6,2),
  rebounds                   NUMERIC(6,2),
  assists                    NUMERIC(6,2),
  steals                     NUMERIC(6,2),
  blocks                     NUMERIC(6,2),
  turnovers                  NUMERIC(6,2),
  fg_pct                     NUMERIC(6,4),
  fg3_pct                    NUMERIC(6,4),
  ft_pct                     NUMERIC(6,4),
  pace                       NUMERIC(6,2),
  offensive_rating           NUMERIC(6,2),
  defensive_rating           NUMERIC(6,2),
  net_rating                 NUMERIC(6,2),
  source_endpoint            TEXT NOT NULL,
  data_version               TEXT NOT NULL,
  ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (game_id, team_id)
);
```

### 3.3 Indexes

```sql
CREATE INDEX idx_fpgs_player_date ON fact_player_game_stats(player_id, game_date);
CREATE INDEX idx_fpgs_team_date ON fact_player_game_stats(team_id, game_date);
CREATE INDEX idx_fpgs_opponent_date ON fact_player_game_stats(opponent_team_id, game_date);
CREATE INDEX idx_fpgs_season_type ON fact_player_game_stats(season, season_type);

CREATE INDEX idx_ftgs_team_date ON fact_team_game_stats(team_id, game_date);
CREATE INDEX idx_ftgs_season_type ON fact_team_game_stats(season, season_type);

CREATE INDEX idx_dim_game_date ON dim_game(game_date);
CREATE INDEX idx_dim_game_season_type ON dim_game(season, season_type);
```

### 3.4 Optional Materialized Views (recommended in V1.1)
- `mv_player_season_agg`
- `mv_player_last_n`
- `mv_team_season_agg`

## 4. Ingestion and Data Freshness

### 4.1 Jobs
1. `bootstrap_historical`
- loads past seasons selected in config

2. `daily_refresh`
- pulls prior day complete game stats
- updates late corrections

3. `intra_day_scoreboard_refresh`
- updates game metadata/status for current day

### 4.2 Idempotency Rules
- upsert by primary keys
- compare hashes/version stamps when available
- write `data_version` and `ingested_at` each load

### 4.3 Data Quality Gates
- min row counts by season/day
- null/range checks on critical fields
- referential integrity checks between facts and dims
- publish quality report table:

```sql
CREATE TABLE data_quality_run (
  run_id               BIGSERIAL PRIMARY KEY,
  started_at           TIMESTAMPTZ NOT NULL,
  finished_at          TIMESTAMPTZ,
  status               TEXT NOT NULL,
  checks_passed        INTEGER NOT NULL DEFAULT 0,
  checks_failed        INTEGER NOT NULL DEFAULT 0,
  details_json         JSONB NOT NULL DEFAULT '{}'::jsonb
);
```

## 5. API Design (FastAPI)

### 5.1 Health/Admin
- `GET /v1/health`
- `GET /v1/data/freshness`

### 5.2 Search APIs (for filter UI)
- `GET /v1/search/players?q=lebron&limit=10`
- `GET /v1/search/teams?q=lakers&limit=10`
- `GET /v1/filters/options?entity=player&metric=points`

### 5.3 Deterministic Stats APIs
- `POST /v1/stats/player-games/query`
- `POST /v1/stats/player-aggregate/query`
- `POST /v1/stats/team-aggregate/query`
- `POST /v1/stats/leaderboard/query`

Each endpoint accepts the same filter contract and returns:
- `applied_filters`
- `rows`
- `summary`
- `meta` (latency, cache hit, data freshness)

### 5.4 Chat/NL API
- `POST /v1/chat/query`

Request:
- `message`
- optional `conversation_id`
- optional `ui_filter_context` (already selected chips)

Response modes:
1. `result`
- includes resolved query plan, data rows, narrative summary

2. `clarification_required`
- includes 1..3 targeted clarification questions + suggested filter chips

## 6. Query Contract (single normalized schema)

Use one internal JSON query plan used by both UI filters and chat.

```json
{
  "entity": "player_game",
  "metrics": ["points", "assists", "rebounds"],
  "aggregations": [
    { "metric": "points", "op": "avg", "alias": "avg_points" }
  ],
  "dimensions": ["player_id", "player_name", "season"],
  "filters": {
    "player_ids": [2544],
    "team_ids": [],
    "opponent_team_ids": [],
    "seasons": ["2024-25"],
    "season_type": "regular_season",
    "date_from": "2024-10-01",
    "date_to": "2025-04-30",
    "home_away": "any",
    "started_only": false,
    "min_minutes": 0,
    "game_result": "any"
  },
  "sort": [{ "field": "avg_points", "direction": "desc" }],
  "limit": 50,
  "offset": 0
}
```

### Guardrails
- allow-list metrics, dimensions, operators
- limit max date range and max row count
- reject unknown fields

## 7. LLM Orchestration Contract

### 7.1 LLM Output Schema (strict)
The model only outputs:
- `intent`
- `entities`
- `filters`
- `requested_metrics`
- `clarification_needed` + `questions`

Then backend compiler converts this into normalized query plan.

### 7.2 Ambiguity Rules
If any of these are ambiguous, return clarification:
- player/team name collision
- relative date phrase without anchor
- season type omitted when query implies splits
- metric not mapped to known schema

### 7.3 Safety Rules
- model cannot submit SQL
- model cannot use unrestricted tool calls
- all plans pass schema validation before execution

## 8. Auth, Rate Limit, and Caching

### Auth (V1)
- API key per user/app
- request quota by key

### Rate limiting
- fixed window in Redis (per minute + per day)
- stricter limits on `/v1/chat/query`

### Caching
- key by canonicalized query plan hash
- TTL default 5 minutes for live season queries
- stale-while-revalidate for heavy aggregate queries

## 9. Observability

### Logging fields (JSON)
- `request_id`, `user_id`, `endpoint`
- `query_plan_hash`, `query_plan_entity`
- `latency_ms`, `row_count`
- `cache_hit`
- `clarification_required`

### Metrics
- p50/p95 latency by endpoint
- DB query time
- cache hit rate
- clarification rate
- error rate by failure type

## 10. V1 Delivery Plan

### Sprint 1 - Data + deterministic APIs
1. Postgres schema + Alembic migrations
2. ingestion jobs for players, teams, games, player game stats
3. deterministic search + player aggregate endpoints
4. baseline tests (unit + integration)

### Sprint 2 - NL interface + clarifications
1. normalized query plan validator
2. chat endpoint with parser/orchestrator
3. clarification flow and UI-ready response format
4. cache + rate limiting + observability

### Sprint 3 - hardening
1. load/performance testing
2. quality monitors + freshness endpoint
3. leaderboard/team endpoints
4. docs + runbooks

## 11. Recommended Project Setup Additions

### Dependencies
- `fastapi`, `uvicorn`
- `sqlalchemy`, `alembic`, `psycopg[binary]`
- `pydantic`
- `redis`
- `celery` or `rq`
- `httpx`
- `structlog` (or stdlib JSON logging)
- `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-timeout`

### Repo structure
- `src/api/`
- `src/domain/query_planner/`
- `src/db/models/`
- `src/db/repositories/`
- `src/etl/jobs/`
- `src/etl/transformers/`
- `src/llm/`
- `tests/unit/`
- `tests/integration/`
- `tests/evals/`

## 12. Definition of Done (V1)
- deterministic endpoint returns correct rows with applied filters echoed
- chat endpoint returns either valid result or explicit clarification
- no direct model-to-SQL path
- ingestion is idempotent and monitored
- data freshness visible by endpoint
- p95 under target for common queries (set target after first benchmark)
