# Sprint 4.7 delivery ledger

## Task 1: executable foundation

Implemented Django/DRF liveness and dependency readiness endpoints, a Next.js TypeScript landing page, locked dependencies, PostgreSQL/Redis persistent volumes, non-root application containers, loopback-only HTTP ports, and GitHub Actions foundation checks.

No employee records, authentication, appraisal workflow, scoring, or promotion automation exist yet. This is a runnable foundation, not the complete appraisal system or a production deployment.

### Verification executed on 2026-09-15

- `docker compose config --quiet`: passed.
- `docker compose up -d --wait postgres redis`: both dependencies healthy.
- `docker compose build backend`: passed on Linux/Python 3.14.
- `docker compose exec -T backend python manage.py check`: no issues.
- `docker compose exec -T backend pytest -q`: 4 passed; cache-directory permission warning only.
- `docker compose build frontend`: passed on Linux/Node 24, including Next.js production build and TypeScript compilation.

Local Compose project name: `staff-appraisal-s47`; test HTTP ports: frontend 3107, backend 8107. Credentials are randomly generated in ignored `.env` and must never be committed.

### Source and scoring gate

The user supplied `Performance_Appraisal_form_MANUAL (1).pdf`, a 12-page manual. Read-only extraction and visual inspection of page 9 confirmed it prints an overall-score equation. Page 8 states target/core/non-core weights of 60/30/10 percent. Page 9 describes weighted competency items and averages, but the exact indicator catalog and item weights from the actual appraisal form have not been verified here. Page 4 specifies three to five key result areas; this is stricter than the earlier maximum-only design.

Do not treat the manual's printed equation as proof that an arbitrary implementation of M, N and O is correct. Final aggregation remains disabled until the form's indicator weights, missing-item rules, rounding/boundaries and worked examples are reconciled. No overall formula or automated promotion threshold was implemented. The local source PDF and full extracted text are not published to the repository.

## Remaining plan

2. Production settings and deployment checks.
3. User, roles and authentication.
4. Department and employee domain.
5. Performance planning and KRA constraints.
6. Mid-year target and competency review.
7. End-year target assessment.
8. Competency and indicator framework.
9. Policy-gated overall rating engine, after authoritative fixtures.
10. Workflow state machine.
11. Object-level authorization and isolation tests.
12. Audit and signatures.
13. Next.js BFF authentication.
14. Role-specific UI.
15. Appraisal journey and browser tests.
16. Analytics without fabricated data.
17. Expand CI to the full domain/security/browser suite.
18. Production hardening and operational verification.

Each increment must be verified before being reported complete. Task 1 CI is an initial gate, not evidence that later security and appraisal requirements already pass.

### Final local check results

- Frontend `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`: passed; 1 component test. Local Node 26; Docker build independently used Node 24.
- Backend `ruff check` and `ruff format --check`: passed after formatting correction.
- Full `docker compose up -d --wait`: all four services reported healthy.
- Host HTTP smoke check: failed with connection refused after the Docker engine became unavailable. The follow-up Docker command could not find the engine pipe. Redis outage/recovery was not reached locally; CI includes this check and must confirm it.
- Full appraisal workflow, RBAC, browser journeys, migrations for domain models and production readiness: not implemented or claimed tested.
- The implementation subagent hit an account usage limit before final review. The primary agent inspected the resulting files and ran the checks above; an independent reviewer was not available.

## Task 1 CI confirmation

GitHub Actions run [34927210064](https://github.com/ws-buntu/staff-appraisal/actions/runs/34927210064) for commit `ab643c7` completed successfully. Backend, frontend and Compose jobs all passed, including real HTTP, Redis outage (503 readiness with live process) and recovery. This supplies the independent Linux environment check that local Docker instability prevented.

## Task 2: production settings baseline

Select `DJANGO_SETTINGS_MODULE=config.production` explicitly in a deployment. Local Compose continues to use the development/CI foundation settings.

The production module rejects weak/missing secrets, absent or wildcard allowed hosts and enabled debug mode. It enables HTTPS redirects, secure cookies, CSRF middleware and security headers. It does not trust forwarded proxy headers automatically. Configure the trusted TLS termination path before deployment; otherwise an HTTP upstream behind a proxy would redirect repeatedly.

Required environment: generated `DJANGO_SECRET_KEY` (at least 50 characters), `DJANGO_ALLOWED_HOSTS` containing actual hostnames, `POSTGRES_PASSWORD`, `DJANGO_DEBUG=false`. Configure database/Redis connectivity as in the baseline. If cross-origin unsafe browser requests are intentionally supported, list HTTPS origins in `DJANGO_CSRF_TRUSTED_ORIGINS`.

HSTS stays disabled until HTTPS is verified. Then configure `DJANGO_HSTS_SECONDS`; `DJANGO_HSTS_INCLUDE_SUBDOMAINS` and `DJANGO_HSTS_PRELOAD` are separate opt-ins requiring domain-wide readiness. Django's deployment checks intentionally warn while those options are disabled. The fully configured test fixture enables them only for an illustrative test domain; it does not alter a real domain.

Verification: five configuration tests were executed and failed before the production module existed. After implementation, the full backend suite passed 10 tests, including configuration rejection, `manage.py check --deploy --fail-level WARNING` for an explicitly configured fixture, HTTPS redirection and response security headers. Ruff lint passed. No production endpoint or TLS certificate has been deployed or verified.
