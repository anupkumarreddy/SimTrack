# SimTrack API

SimTrack exposes a versioned Django REST Framework API under `/api/v1/`.

## Authentication

All API endpoints except `GET /api/v1/health/` require a bearer token:

```http
Authorization: Bearer <token>
```

Create a token with:

```bash
./.venv/bin/python manage.py create_api_token --user USERNAME_OR_EMAIL --name ci-runner --scopes read,write,ingest
```

The raw token is printed once. SimTrack stores only a SHA-256 hash of the token.

## Scopes

- `read`: retrieve projects, regressions, runs, results, failure signatures, and schema.
- `write`: create and patch projects, regressions, and runs.
- `ingest`: submit run ingestion payloads from tools or CI.

## Health

```http
GET /api/v1/health/
```

Response:

```json
{
  "status": "ok"
}
```

## Read Endpoints

These endpoints require `read` scope:

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
- `GET /api/v1/schema/`

List responses are paginated:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": []
}
```

Pagination parameters:

```text
?limit=50&offset=0
```

Common filters:

- `project`
- `regression`
- `run`
- `status`
- `branch`
- `suite`
- `created_after`
- `created_before`

Example:

```bash
curl -H "Authorization: Bearer $SIMTRACK_TOKEN" \
  "http://127.0.0.1:8000/api/v1/runs/?project=1&status=completed&branch=main"
```

## Write Endpoints

These endpoints require `write` scope:

- `POST /api/v1/projects/`
- `PATCH /api/v1/projects/<id>/`
- `POST /api/v1/regressions/`
- `PATCH /api/v1/regressions/<id>/`
- `POST /api/v1/runs/`
- `PATCH /api/v1/runs/<id>/`

`PUT` and `DELETE` are not enabled in API v1.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/projects/" \
  -H "Authorization: Bearer $SIMTRACK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Chip Top","slug":"chip-top","status":"active"}'
```

Run counters such as `total_count`, `pass_count`, `fail_count`, and `pass_rate` are server-managed.

## Run Ingestion

The ingestion endpoint requires `ingest` scope:

```http
POST /api/v1/ingest/run/
```

The endpoint creates or updates:

- project
- regression
- regression run
- result rows
- failure signatures

Re-ingesting the same regression/run number replaces that run's result rows so retrying the same tool upload does not duplicate results.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/run/" \
  -H "Authorization: Bearer $SIMTRACK_TOKEN" \
  -H "Content-Type: application/json" \
  -d @run-payload.json
```

Payload:

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
    "run_number": 1042,
    "run_name": "nightly-smoke-2026-05-28",
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

## Error Format

API errors use this shape:

```json
{
  "error": "validation_error",
  "message": "Request validation failed.",
  "fields": {
    "name": ["This field is required."]
  }
}
```

Common error codes:

- `authentication_required`
- `invalid_token`
- `permission_denied`
- `not_found`
- `validation_error`
- `method_not_allowed`
- `server_error`

