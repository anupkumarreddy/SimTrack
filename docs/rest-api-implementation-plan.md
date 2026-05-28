# REST API Implementation Plan

## Goal

Add a secured REST interface that external tools and CI jobs can use to populate and retrieve SimTrack data for projects, regressions, regression runs, results, failure signatures, and related records.

The API will be versioned under `/api/v1/`, implemented with Django REST Framework, and secured with bearer tokens.

## Non-Goals

- Replace the existing Django HTML views.
- Add a public unauthenticated API.
- Build a full UI for API token self-service in the first pass.
- Introduce broad model refactors unrelated to ingestion or retrieval.

## Guiding Decisions

- Create a dedicated `api` Django app.
- Keep the existing page routes unchanged.
- Use Django REST Framework for serializers, views, routers, permissions, request parsing, pagination, and API tests.
- Store only hashed API tokens.
- Implement a custom DRF bearer-token authentication class backed by the hashed token model.
- Keep ingestion business logic in service functions, not directly in views.
- Implement a high-value run ingestion endpoint before broad write coverage.

## Phase 1: DRF Dependency, API App, And Routing

### Deliverables

- Add `djangorestframework` to project dependencies.
- Add `rest_framework` and the new `api` app to `INSTALLED_APPS`.
- Add a new `api` Django app.
- Add `api.urls`.
- Add a DRF router for model endpoints.
- Mount API routes under `/api/v1/` from `simtrack.urls`.
- Add a basic health endpoint:
  - `GET /api/v1/health/`
- Configure default DRF settings for:
  - custom authentication
  - authenticated-only access
  - limit/offset pagination
  - JSON renderer/parser defaults

### Acceptance Checks

- `/api/v1/health/` returns JSON.
- Existing HTML routes continue to work.
- No API route is mounted outside `/api/v1/`.
- DRF is installed and available in the Django app registry.

## Phase 2: DRF Bearer Token Authentication

### Deliverables

- Add an `ApiToken` model with:
  - token name
  - associated user
  - hashed token
  - scopes
  - active flag
  - last-used timestamp
  - created timestamp
- Add a custom DRF authentication class, for example `BearerTokenAuthentication`, for:
  - missing token
  - malformed `Authorization` header
  - invalid token
  - inactive token
- Add DRF permission helpers/classes for scope checks:
  - `HasReadScope`
  - `HasWriteScope`
  - `HasIngestScope`
- Add token management command:

```bash
python manage.py create_api_token --user user@example.com --name ci-runner --scopes read,write,ingest
```

- Register `ApiToken` in Django admin.

### Acceptance Checks

- API endpoints reject missing bearer token with `401`.
- API endpoints reject invalid bearer token with `401`.
- API endpoints reject insufficient scope with `403`.
- Valid tokens authenticate successfully.
- Raw tokens are shown only once at creation time and are not stored in plaintext.
- `request.user` is populated from the token owner for authenticated API requests.

## Phase 3: Serializers And Read-Only Retrieval Endpoints

### Deliverables

Add DRF serializers for the core models:

- `ProjectSerializer`
- `RegressionSerializer`
- `RegressionRunSerializer`
- `ResultSerializer`
- `FailureSignatureSerializer`
- Supporting compact serializers where nested representation is useful.

Add DRF read endpoints for the core models:

- `GET /api/v1/projects/`
- `GET /api/v1/projects/<id>/`
- `GET /api/v1/regressions/`
- `GET /api/v1/regressions/<id>/`
- `GET /api/v1/runs/`
- `GET /api/v1/runs/<id>/`
- `GET /api/v1/results/`
- `GET /api/v1/results/<id>/`
- `GET /api/v1/failure-signatures/`
- `GET /api/v1/failure-signatures/<id>/`

Support common filters where applicable:

- `project`
- `regression`
- `run`
- `status`
- `branch`
- `suite`
- `created_after`
- `created_before`

Use simple pagination:

```text
?limit=50&offset=0
```

Implementation options:

- Use DRF `ReadOnlyModelViewSet` for list/detail endpoints.
- Use `LimitOffsetPagination`.
- Implement filtering in `get_queryset()` initially.
- Add `django-filter` later only if filtering grows beyond simple query params.

### Acceptance Checks

- Read endpoints require `read` scope.
- List endpoints return `count`, `limit`, `offset`, and `results`.
- Detail endpoints return `404` for missing objects.
- Filters return scoped datasets correctly.
- Querysets avoid obvious N+1 issues with `select_related` where needed.

## Phase 4: Run Ingestion Endpoint

### Deliverables

Add the primary tool/CI ingestion endpoint using DRF `APIView` or `GenericAPIView`:

- `POST /api/v1/ingest/run/`

The endpoint should support creating or updating:

- project
- regression
- regression run
- result rows
- failure signatures for failed results

Use existing services where possible:

- `results.services.get_or_create_signature`
- `results.services.update_signature_counts`
- `results.services.recalculate_run_counters`
- `regressions.services.get_next_run_number`

Add DRF serializers for ingestion validation:

- `IngestProjectSerializer`
- `IngestRegressionSerializer`
- `IngestRunSerializer`
- `IngestResultSerializer`
- `IngestRunPayloadSerializer`

Example payload shape:

```json
{
  "project": {
    "slug": "chip-top",
    "name": "Chip Top"
  },
  "regression": {
    "name": "nightly-smoke",
    "branch_name": "main",
    "suite_name": "smoke",
    "config_name": "default"
  },
  "run": {
    "run_name": "nightly-smoke-2026-05-28",
    "run_number": 1042,
    "status": "completed",
    "trigger_type": "ci",
    "build_id": "build-123",
    "git_commit": "abc123",
    "start_time": "2026-05-28T01:00:00Z",
    "end_time": "2026-05-28T01:12:30Z",
    "metadata": {
      "ci_url": "https://ci.example.com/build/123"
    }
  },
  "results": [
    {
      "test_name": "test_reset_sequence",
      "status": "pass",
      "seed": "1001",
      "duration_seconds": "12.4",
      "machine_name": "runner-01"
    },
    {
      "test_name": "test_axi_timeout",
      "status": "fail",
      "seed": "1002",
      "duration_seconds": "35.8",
      "machine_name": "runner-02",
      "error_message": "AXI timeout waiting for response",
      "failure_signature": {
        "title": "AXI timeout waiting for response",
        "category": "timeout",
        "is_infra_issue": false,
        "is_known_issue": false
      }
    }
  ]
}
```

### Acceptance Checks

- Endpoint requires `ingest` scope.
- Missing required fields return DRF validation errors with `400`.
- Ingestion creates missing project, regression, run, and results.
- Re-ingestion with the same natural keys is idempotent where practical.
- Run counters and pass rate are recalculated after ingestion.
- Failure signatures are created and attached to failed results.
- The view stays thin and delegates creation/update behavior to an ingestion service.

## Phase 5: Write Endpoints For Core Models

### Deliverables

Extend selected DRF viewsets with create/update support:

- `POST /api/v1/projects/`
- `PATCH /api/v1/projects/<id>/`
- `POST /api/v1/regressions/`
- `PATCH /api/v1/regressions/<id>/`
- `POST /api/v1/runs/`
- `PATCH /api/v1/runs/<id>/`

Keep deletes out of the first API version unless there is a concrete tool need.

### Acceptance Checks

- Write endpoints require `write` scope.
- Invalid enum values return DRF validation errors.
- `PATCH` only updates supplied fields.
- Existing staff-only HTML form behavior is unchanged.
- Model serializers do not expose fields that should stay server-managed.

## Phase 6: Error Format, Validation, And Schema

### Deliverables

Use DRF serializers as the primary validation layer.

Optionally add a custom DRF exception handler to standardize errors:

```json
{
  "error": "validation_error",
  "message": "Request validation failed.",
  "fields": {
    "regression": "This field is required."
  }
}
```

Use consistent error codes:

- `authentication_required`
- `invalid_token`
- `permission_denied`
- `not_found`
- `validation_error`
- `method_not_allowed`
- `server_error`

Add OpenAPI/schema support after the endpoint shapes stabilize. Preferred options:

- DRF built-in schema support for a minimal baseline.
- `drf-spectacular` if richer OpenAPI output is needed.

### Acceptance Checks

- All API failures return JSON.
- API failures do not return Django HTML error pages.
- Validation errors identify the failing field where possible.
- API schema generation is either implemented or explicitly deferred in this phase.

## Phase 7: Tests

### Deliverables

Add DRF API tests using `APITestCase` and `APIClient` for:

- missing bearer token
- invalid bearer token
- valid bearer token
- read scope
- write scope
- ingest scope
- list/detail retrieval
- filtering and pagination
- run ingestion
- failure signature grouping
- counter recalculation

### Acceptance Checks

- Full Django test suite passes.
- API tests cover authentication, authorization, retrieval, and ingestion.
- Regression coverage confirms existing HTML routes still resolve.
- Serializer validation tests cover key invalid payloads.

## Phase 8: Documentation

### Deliverables

Add `docs/api.md` with:

- authentication model
- token creation command
- endpoint list
- scopes
- filtering and pagination
- ingestion payload
- curl examples
- error response format
- DRF browsable API availability, if enabled in development

### Acceptance Checks

- A CI/tool owner can create a token and ingest a run using only the docs.
- Example payloads match implemented field names.
- Documentation states that tokens are shown only once.

## Phase 9: Hardening And Follow-Up

### Deliverables

Evaluate and add as needed:

- token expiration
- token revocation workflow
- per-token rate limiting
- request audit logging
- OpenAPI schema generation
- CSV upload endpoint
- bulk result streaming for very large runs
- `django-filter` integration for richer filtering
- `drf-spectacular` integration for richer OpenAPI docs

### Acceptance Checks

- Follow-up work is tracked separately.
- First API version remains small, documented, and testable.

## Suggested Implementation Order

1. Phase 1: DRF dependency, API app, and routing.
2. Phase 2: DRF bearer token authentication.
3. Phase 3: serializers and read-only endpoints.
4. Phase 4: run ingestion endpoint.
5. Phase 7: tests for the implemented surface.
6. Phase 8: docs for the implemented surface.
7. Phase 5 and Phase 6 after the first ingestion path is stable.
