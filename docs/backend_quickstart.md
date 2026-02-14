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

