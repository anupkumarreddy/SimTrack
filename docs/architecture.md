# SimTrack Architecture

## Apps Overview

- `accounts`: custom user model, sign-up, login, password reset, project memberships.
- `projects`: project metadata and categories.
- `regressions`: regression definitions and run records.
- `results`: individual test results and failure signatures.
- `milestones`: project milestones and milestone updates.
- `dashboard`: cross-project and project-level dashboards.
- `common`: shared choices, utilities, middleware, and mixins.

## Data Flow

1. A project owns regressions.
2. A regression receives runs.
3. A run stores aggregate counters and individual result rows.
4. Failed result rows can be grouped into failure signatures.
5. Dashboards aggregate run counters, milestone state, and signature counts.

## Main Models

- `Project`
- `ProjectCategory`
- `Regression`
- `RegressionRun`
- `Result`
- `FailureSignature`
- `Milestone`
- `MilestoneUpdate`
- `User`

## Relationship

```text
Project -> Regression -> Run -> Result -> FailureSignature
```

`FailureSignature` belongs to a single `RegressionRun` and groups matching failed results for that run.

## Why This Model Was Chosen

DV teams usually reason about failures at run scope first: a run has a branch, suite, configuration, counters, tests, and a current set of failure groups. This keeps dashboard queries straightforward while preserving enough detail to inspect individual tests.
