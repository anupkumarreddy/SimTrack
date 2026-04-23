# SimTrack

SimTrack is a production-style Django web application for tracking verification regressions, regression runs, grouped failure signatures, and individual test results. It is designed as an internal engineering productivity tool for design verification teams.

## Tech Stack

- **Python 3.11+**
- **Django 5.2**
- **SQLite** (default, structured for easy PostgreSQL migration)
- **Django Templates** (server-rendered pages only)
- **Tailwind CSS** (via npm build pipeline)
- **Preline UI** (JS components via CDN)

## Project Structure

This is a multi-app Django project with the following apps:

- `accounts` — Custom user model, authentication, project memberships
- `common` — Shared base models, choices/enums, utilities
- `projects` — Project master data
- `milestones` — Project milestones and update history
- `regressions` — Regression metadata definitions and regression runs
- `results` — Per-test results, failure signatures
- `dashboard` — Summary pages and project health views

## Installation

### 1. Clone and enter the project

```bash
cd SimTrack
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install django
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Install Node dependencies and build Tailwind CSS

```bash
npm install
npm run build-css
```

To watch for changes during development:

```bash
npm run watch-css
```

### 7. Load demo data

```bash
python manage.py seed_demo_data
```

### 8. Run the development server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## URL Overview

| Path | Description |
|------|-------------|
| `/` | Global dashboard |
| `/dashboard/project/<slug>/` | Project dashboard |
| `/projects/` | Project list |
| `/projects/<slug>/` | Project detail |
| `/projects/create/` | Create project |
| `/projects/<slug>/edit/` | Edit project |
| `/milestones/` | Milestone list |
| `/milestones/<id>/` | Milestone detail |
| `/milestones/create/` | Create milestone |
| `/regressions/` | Regression list |
| `/regressions/<id>/` | Regression detail |
| `/regressions/create/` | Create regression |
| `/runs/` | Run list |
| `/runs/<id>/` | Run detail |
| `/runs/create/` | Create run |
| `/results/` | Result list |
| `/results/<id>/` | Result detail |
| `/failure-signatures/<id>/` | Failure signature detail |
| `/accounts/login/` | Login |
| `/accounts/logout/` | Logout |
| `/admin/` | Django admin |

## Tailwind and Preline Setup

- **Tailwind CSS** is built via the official Tailwind CLI using npm.
- Input file: `static/css/input.css`
- Output file: `static/css/output.css`
- Configuration: `tailwind.config.js`
- Build command: `npm run build-css`
- **Preline UI** JavaScript is loaded via CDN in `templates/base.html`.

## Demo Data

The `seed_demo_data` management command creates:

- 3 users (including an admin with password `admin`)
- 3 projects with varied statuses
- 7 regressions across projects
- Multiple runs per regression with realistic counters
- Results per run distributed across statuses
- Failure signatures grouping multiple failed results
- Milestones with updates

Log in with:
- Username: `admin`
- Password: `admin`

## Database

SQLite is used for local development. To switch to PostgreSQL later, update the `DATABASES` setting in `simtrack/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'simtrack',
        'USER': 'simtrack',
        'PASSWORD': '...',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Key Design Decisions

- **Regression** is metadata only (definition).
- **RegressionRun** holds actual execution counters and stats.
- **Result** holds individual test rows for a run.
- **FailureSignature** groups multiple results within a run (not globally).
- Counter recalculation is handled via Django signals (`post_save`, `post_delete` on `Result`).
- Signature normalization and hashing utilities live in `results/services.py`.

## Code Quality

- Clean separation of concerns across 7 apps
- Thin views, business logic in service modules
- Shared abstract base model (`TimeStampedModel`) in `common`
- All models registered in Django admin with list display, filters, and search
- Comprehensive filtering and search on list pages
- Polished UI with status badges, stat cards, tables, tabs, and empty states
