# SimTrack

Regression tracking dashboard for DV teams.

## Why SimTrack Exists

Design verification teams run many regressions across projects, branches, suites, and configurations. SimTrack gives those teams a focused place to track projects, regressions, runs, test results, milestones, and recurring failure signatures without needing a general-purpose issue tracker or spreadsheet.

## Features

- Project and regression dashboards
- Regression run history with pass/fail trends
- Per-test result tracking
- Failure signature grouping
- Project milestones
- Authentication with read-only regular users and staff-only write access
- Demo data and demo-user commands
- Tailwind-based responsive UI

## Screenshots

Screenshots live in `docs/images/`.

- Dashboard: `docs/images/dashboard.svg`
- Project page: `docs/images/project-page.svg`
- Regression run page: `docs/images/regression-run-page.svg`
- Failure signature page: `docs/images/failure-signature-page.svg`

## Demo

```bash
python manage.py migrate
python manage.py seed_demo_data --small
python manage.py create_demo_user --username demo --password demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and sign in with `demo` / `demo`.

## Tech Stack

- Python 3.11+
- Django 5.2
- SQLite by default
- Django templates
- Tailwind CSS
- Preline UI via CDN

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm install
cp .env.example .env
python manage.py migrate
npm run build-css
python manage.py createsuperuser
python manage.py runserver
```

## Local Development

Use development settings by default:

```bash
export DJANGO_SETTINGS_MODULE=simtrack.settings.dev
python manage.py test
python manage.py check
npm run build-css
```

Run code quality checks:

```bash
ruff check .
black --check .
isort --check-only .
```

## Demo Data

Create a compact dataset:

```bash
python manage.py seed_demo_data --small
```

Create a read-only demo user:

```bash
python manage.py create_demo_user --username demo --password demo
```

Create the richer demo dataset:

```bash
python manage.py seed_demo_data
```

## Project Architecture

See `docs/architecture.md`.

## Data Model

Core relationship:

```text
Project -> Regression -> RegressionRun -> Result -> FailureSignature
```

Failure signatures group related failed results within a regression run.

## Roadmap

- Import runs from CI artifacts
- PostgreSQL deployment profile
- Project-level role permissions
- CSV/API import endpoints
- Global failure signature clustering

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.
