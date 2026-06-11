# SimTrack v1.1.0 Release Notes

Release date: 2026-06-11

## Summary

SimTrack v1.1.0 adds the first versioned REST API for external tools and CI systems. The release enables authenticated model queries, scoped writes, and idempotent regression run ingestion under `/api/v1/`.

## Changes Since v1.0.0

### API

- Added Django REST Framework support and mounted all API routes under `/api/v1/`.
- Added `GET /api/v1/health/` for unauthenticated health checks.
- Added `GET /api/v1/schema/` for OpenAPI schema discovery.
- Added read endpoints for projects, regressions, runs, results, and failure signatures.
- Added scoped write endpoints for projects, regressions, and runs.
- Added `POST /api/v1/ingest/run/` for CI/tool ingestion of regression run payloads.
- Added filtering support for common model query fields including project, regression, run, status, branch, suite, and creation timestamps.

### Authentication And Permissions

- Added bearer-token API authentication.
- Added hashed API token storage with last-used tracking.
- Added token scopes: `read`, `write`, and `ingest`.
- Added `create_api_token` management command for creating scoped tokens.

### Ingestion

- Added ingestion service that creates or updates projects, regressions, runs, results, and failure signatures from one payload.
- Added idempotent re-ingestion behavior for the same regression run number.
- Added server-managed run counters and pass-rate recalculation during ingestion.

### Documentation

- Added API usage documentation in `docs/api.md`.
- Added REST API implementation plan in `docs/rest-api-implementation-plan.md`.
- Updated release checklist and project documentation for release readiness.

### Quality

- Added API tests for authentication, scopes, error responses, schema access, read/write endpoints, and ingestion behavior.
- Added CI, formatting, linting, smoke, and permission test coverage.

## Compatibility Notes

- The API path is versioned as `/api/v1/`.
- API `PUT` and `DELETE` are intentionally not enabled for v1 write endpoints.
- Existing web UI behavior is unchanged.

## Upgrade Notes

- Run database migrations before deploying.
- Create API tokens with `python manage.py create_api_token --user USERNAME_OR_EMAIL --name TOKEN_NAME --scopes read,write,ingest`.
- Use `Authorization: Bearer <token>` for all API endpoints except `/api/v1/health/`.
