# Contributing

## Issues

Use GitHub issues for bugs, usability problems, documentation gaps, and feature requests. Include reproduction steps, expected behavior, actual behavior, and screenshots when useful.

## Feature Requests

Describe the DV workflow problem first, then the proposed solution. Include sample data shape or UI expectations if relevant.

## Branch Naming

- `feature/<short-name>`
- `fix/<short-name>`
- `docs/<short-name>`
- `chore/<short-name>`

## Commit Style

Use short imperative messages:

```text
Add regression pass-rate chart
Fix milestone status badge alignment
```

## Pull Request Checklist

- Tests pass with `python manage.py test`
- Migrations are intentional and checked in
- `ruff check .`, `black --check .`, and `isort --check-only .` pass
- UI changes include screenshots or a short description
- Documentation is updated when behavior changes

## Code Style

Use `black`, `isort`, and `ruff`. Keep Django views thin and put reusable business logic in services or helpers.

## Test Requirement

Add or update tests for model behavior, permissions, core views, and management commands touched by the change.
