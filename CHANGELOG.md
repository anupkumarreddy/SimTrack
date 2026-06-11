# Changelog

## Unreleased

No unreleased changes.

## 1.1.0 - 2026-06-11

- Added Django REST Framework API under `/api/v1/`.
- Added bearer-token authentication with hashed token storage and scoped `read`, `write`, and `ingest` permissions.
- Added read endpoints for projects, regressions, runs, results, failure signatures, and OpenAPI schema discovery.
- Added scoped write endpoints for creating and patching projects, regressions, and runs.
- Added run ingestion endpoint that creates or updates projects, regressions, runs, results, and failure signatures from CI/tool payloads.
- Made repeated ingestion of the same run idempotent by replacing existing result rows instead of duplicating them.
- Added standardized JSON API error responses.
- Added `create_api_token` management command.
- Added API documentation and implementation plan.
- Added API authentication, permission, endpoint, schema, and ingestion tests.
- Prepared settings for environment-based development and production usage.
- Added authentication pages and read-only demo-user command.
- Added CI, linting, formatting configuration, and release documentation.
- Added smoke and permission tests.
