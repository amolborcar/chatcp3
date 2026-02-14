# NBA Stats Assistant - Backend V1 Budget Spec (~$25/month)

## 1. Objective
Ship a production-usable, learning-focused version of the NBA stats app with:
- deterministic stats APIs
- basic chat-style query interpretation
- strict monthly infrastructure budget target of `<= $25`

Keep the full spec in `docs/backend_v1_spec.md` as the long-term architecture.

## 2. Budget-First Architecture

## 2.1 Single-Host Deployment
Run everything on one low-cost VPS (`$5-$12/month`):
- FastAPI app
- Postgres
- scheduler (cron/systemd timer) for ingestion
- reverse proxy (Caddy or Nginx)

No separate Redis/queue service in V1 budget mode.

## 2.2 Background Jobs
Use lightweight scheduled commands instead of Celery:
- `python -m src.etl.jobs.daily_refresh`
- optional `python -m src.etl.jobs.bootstrap --season 2024-25`

Jobs write directly to Postgres with idempotent upserts.

## 2.3 Data Freshness
- daily refresh only (off-peak hour)
- no intraday live-game polling in budget mode

## 3. Scope Reductions (Intentional)
1. Seasons limited to recent window (ex: last 2-3 seasons).
2. No real-time game tracking.
3. No heavy materialized view maintenance initially.
4. No paid observability stack.
5. Chat requests rate-limited hard.

## 4. API Surface (Budget MVP)
- `GET /v1/health`
- `GET /v1/search/players`
- `GET /v1/search/teams`
- `POST /v1/stats/player-aggregate/query`
- `POST /v1/stats/player-games/query`
- `POST /v1/chat/query` (limited)

Skip team/leaderboard endpoints initially unless needed.

## 5. LLM Strategy for Cost Control

## 5.1 Default Mode (recommended)
Deterministic backend + optional LLM interpretation.

Chat endpoint behavior:
1. attempt rule-based parse first (cheap/free)
2. fallback to LLM only if needed
3. enforce monthly token and request caps

## 5.2 BYOK Mode
Allow users to provide their own API key:
- server stores encrypted temporary token or session-only use
- your infra cost near-zero for LLM calls

## 5.3 No-LLM Safe Mode
If budget cap hit, chat endpoint returns:
- parsed filter suggestions from rule engine
- deterministic query UI fallback

## 6. Database (Reuse Core, Smaller Dataset)
Reuse schema from full spec with these operational limits:
- ingest fewer seasons
- prune or archive old raw payloads
- add only essential indexes first:
  - player/date
  - team/date
  - game date

## 7. Cost Envelope

Expected monthly:
1. VPS: `$8` (small instance)
2. Backups/snapshots: `$2-$5`
3. Domain: already paid
4. TLS: free (Let's Encrypt)
5. LLM: `$0-$10` (BYOK or strict cap)

Total typical range: `$10-$23` (up to `$25` with small overage buffer).

## 8. Guardrails to Stay Under Budget
1. Hard monthly LLM cap (requests + tokens).
2. Per-IP/per-user rate limits on `/v1/chat/query`.
3. Query constraints:
   - max date range
   - max rows
   - timeout for slow queries
4. Cache responses in-process (LRU/TTL) before adding Redis.
5. Turn off chat fallback-to-LLM automatically when budget threshold reached.

## 9. Implementation Order (Budget Track)
1. FastAPI + Postgres + Alembic on single host.
2. Ingestion scripts with idempotent upserts.
3. Deterministic search/stats endpoints.
4. Rule-based NL parser (basic patterns).
5. Optional LLM fallback + BYOK support.
6. Simple metrics + spend tracker endpoint.

## 10. Budget Exit Criteria (when to scale up)
Move toward full architecture once any are true:
1. sustained user growth causes >70% CPU on single VPS
2. p95 latency > target for common queries
3. monthly LLM use consistently exceeds budget cap
4. need near-real-time data updates
