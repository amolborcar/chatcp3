# Backend Quickstart (Budget Skeleton)

## 1. Install dependencies

```bash
./venv/bin/pip install -r requirements.txt
```

## 2. Configure env

```bash
cp .env.example .env
```

Update `DATABASE_URL` to your local Postgres connection.

Optional budget-mode ETL tuning knobs (in `.env`):
- `INGEST_API_DELAY_SECONDS` (default `0.5`)
- `INGEST_API_TIMEOUT_SECONDS` (default `12.0`)
- `INGEST_API_MAX_RETRIES` (default `1`)

## 3. Run migrations

```bash
./venv/bin/alembic upgrade head
```

## 4. Start API

```bash
./venv/bin/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. Smoke check

```bash
curl http://localhost:8000/v1/health
```

## 6. Run initial ingestion pass

```bash
./venv/bin/python -m src.etl.jobs.daily_refresh --season 2024-25 --max-players 20
```
