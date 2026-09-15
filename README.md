# Staff Appraisal

Staff Performance Planning, Review and Appraisal system.

## Current scope

Sprint 4.7 Task 1: an executable application and Docker foundation. Next.js/TypeScript frontend, Django REST Framework backend, PostgreSQL and Redis. Django will own appraisal rules, workflow, permissions and calculations. Staff accounts and domain features are not implemented yet. The landing page contains no sample staff records or invented results.

**Scoring safeguard:** final overall-score aggregation remains unresolved. Do not infer a T-to-Z formula, publish a calculated overall rating, or automate promotion decisions without authoritative guidance and verified fixtures.

## Run with Docker

Requires Docker Engine and Docker Compose. Copy `.env.example` to `.env` and fill the two blank secret values with independently generated random strings (for example, `python -c "import secrets; print(secrets.token_hex(32))"` twice). Never commit `.env`.

```sh
docker compose config --quiet
docker compose up --build -d --wait
```

Open http://localhost:3000. API endpoints:

- `GET http://localhost:8000/api/health/live/` returns 200 if the process responds, without checking dependencies.
- `GET http://localhost:8000/api/health/ready/` runs PostgreSQL `SELECT 1` and Redis `PING`. Returns 200 if both succeed, otherwise 503 with sanitized dependency status.

Host ports bind only to loopback. PostgreSQL and Redis have no host-published ports. All services have health checks; PostgreSQL and Redis use named persistent volumes. `docker compose down` stops services and preserves data. `docker compose down -v` deliberately deletes the volumes; use only for disposable data.

This configuration is for local development and CI. Production TLS, deployment configuration, authentication, authorization and operational hardening remain later work.

## Backend checks

Use Python 3.14 and an isolated environment. Install `backend/requirements.lock`, set `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` to disposable test values, then from `backend`:

```sh
python -m pytest -q
python manage.py check
python -m ruff check .
python -m ruff format --check .
```

Unit tests isolate external PostgreSQL and Redis connections; Compose checks exercise real dependencies. For direct local API development set `POSTGRES_HOST` and `REDIS_URL` for services you can reach, then `python manage.py runserver`. The backend intentionally does not load `.env` itself; Compose injects those variables.

## Frontend checks

Use Node.js 24 (the container/CI baseline), then from `frontend`:

```sh
npm ci
npm run typecheck
npm run lint
npm test
npm run build
npm run dev
```

Dependencies are pinned in `backend/requirements.lock` and `frontend/package-lock.json`. GitHub Actions runs backend checks, frontend checks, and a real Compose startup/dependency outage/recovery check.

See [verification and delivery status](docs/sprint-4.7.md) for observed outcomes and pending work.
