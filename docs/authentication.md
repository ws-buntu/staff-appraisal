# Backend authentication (Sprint 4.7 Task 3)

This increment supplies the backend account boundary. Browser login, secure cookie storage, password reset, account provisioning UI and appraisal permissions are later increments. Do not connect browser token storage directly to these endpoints; the planned Next.js backend-for-frontend will manage HttpOnly cookies.

## Account model

`accounts.User` extends Django's password-hashing account model with UUID identifiers and a role constrained by PostgreSQL. The roles are EMPLOYEE, APPRAISER, HOD, HR and ADMIN. New accounts default to EMPLOYEE. These business roles are separate from Django's `is_staff` and `is_superuser` flags. Tokens do not grant role authority: authenticated requests load the current account from the database.

There is no public registration or account-edit endpoint. `GET /api/auth/me/` is read-only. Posting a role or identity in an authentication request cannot update the account.

## Endpoints

All paths end with `/` and accept JSON where applicable.

| Endpoint | Input | Success |
| --- | --- | --- |
| POST `/api/auth/login/` | username, password | 200 with access and refresh tokens |
| POST `/api/auth/refresh/` | refresh | 200 with new access and refresh tokens |
| POST `/api/auth/logout/` | refresh; bearer access header required | 204; revokes that account's submitted refresh token |
| GET `/api/auth/me/` | bearer access header | 200 with id, username, first_name, last_name, email, role |

Invalid credentials and invalid, expired or revoked tokens are rejected. Deactivated or deleted accounts cannot refresh or authenticate. Incomplete or incorrectly typed requests receive validation errors. Supplying another account's refresh token to logout is forbidden. Profile modifications are not supported.

Access tokens last 10 minutes. Refresh tokens last 8 hours and rotate on use; each successful refresh receives a new 8-hour expiry. Refresh rotation uses a PostgreSQL row lock and verifies the token again under that lock to prevent concurrent replay. An old refresh token cannot be used after rotation. This is a sliding refresh window, not an absolute session lifetime.

Logout revokes the submitted refresh token, not every device or descendant token in a session family. Already-issued access tokens can remain valid for up to 10 minutes. Logout and refresh use the same token row lock; logout refuses an already-rotated token. A client should serialize refresh and logout and clear its credentials after logout. Account deactivation is an immediate database-backed block. Saving a changed password invalidates previously issued access and refresh tokens. All authentication responses use `Cache-Control: no-store`. Session-family management and browser cookie clearing belong to the subsequent authentication and operational work.

Login and refresh share a five-attempts-per-minute limit per connection IP, backed by Redis. Untrusted `X-Forwarded-For` is ignored (`NUM_PROXIES=0`). Configure and test trusted proxy identity before deploying behind the Next.js BFF or a reverse proxy, otherwise users may share the proxy's quota. This application throttle is not a replacement for infrastructure abuse protection.

## Migration and local testing

Docker Compose runs a one-shot migration service before starting the backend. A failed migration prevents backend startup. Existing PostgreSQL/Redis volumes are preserved.

For a native backend, supply the environment variables described in the README and use a reachable PostgreSQL database:

```sh
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py check
python -m pytest -q
```

Tests create a temporary PostgreSQL test database; the test role must be permitted to create databases. Do not give that elevated test permission to a production application role. The auth unit/integration tests replace Redis with an isolated in-memory cache; the separate CI HTTP smoke check uses the actual Redis service.

CI uses PostgreSQL 17. The local isolated native test cluster uses PostgreSQL 18. Both apply the same migrations. `infrastructure/check_auth.py` creates and deletes one randomly named disposable account and checks real HTTP login, identity, refresh, replay and logout without printing credentials or tokens. Run it only against disposable CI/test databases.

Create administrative accounts with Django's management commands only in an explicitly selected environment. There are no seeded production users or default passwords. No production account has been created by this increment.

Later operational setup must schedule `python manage.py flushexpiredtokens` and establish account recovery and session policies. The overall appraisal-score formula remains unimplemented.
