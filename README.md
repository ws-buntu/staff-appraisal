# Staff Appraisal

Staff Performance Planning, Review and Appraisal system.

## Current scope

Sprint 4.7 Tasks 1-4: application/Docker foundation, production-settings guardrails, backend account authentication, departments and employee records. Next.js/TypeScript frontend, Django REST Framework backend, PostgreSQL and Redis. Django will own appraisal rules, workflow, permissions and calculations. Backend authentication and the department/employee directory are available; appraisal workflow and browser sign-in remain pending. The landing page contains no sample staff records or invented results.

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

Health unit tests mock dependency connections; authentication tests use a real PostgreSQL test database and an isolated in-memory throttle cache. Supply a reachable PostgreSQL server and a disposable test role with database-creation permission before running pytest. CI container smoke checks use real PostgreSQL and Redis. For direct local API development set `POSTGRES_HOST` and `REDIS_URL` for services you can reach, then `python manage.py runserver`. The backend intentionally does not load `.env` itself; Compose injects those variables.

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

## Production settings baseline

`config.production` adds strict environment validation and HTTPS/security settings. It is opt-in and is not a ready-to-deploy infrastructure definition. See [Task 2 deployment notes](docs/sprint-4.7.md#task-2-production-settings-baseline) for required configuration and remaining TLS/proxy gates.


## Backend accounts

See [authentication endpoints and operating limits](docs/authentication.md). Compose now applies account/token migrations before backend startup. No default accounts or passwords are created. The browser sign-in flow will be added in a later increment.


## Departments and employees

The [directory API](docs/employees.md) provides HR-managed employee records with role-based read scopes, pagination and protected account relationships. There is no hard-delete endpoint and no seeded staff data.
