# Development Guide

## Python Version

Use Python 3.11 or newer.

## Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements-dev.txt
npm install
```

## Environment

```bash
cp .env.example .env
export DJANGO_SETTINGS_MODULE=simtrack.settings.dev
```

## Migrations

```bash
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

## Create Superuser

```bash
python manage.py createsuperuser
```

## Load Seed Data

```bash
python manage.py seed_demo_data --small
python manage.py create_demo_user --username demo --password demo
```

## Run Tests

```bash
python manage.py test
```

## Run Formatter and Linter

```bash
ruff check .
black .
isort .
```

## Static Assets

```bash
npm run build-css
npm run watch-css
python manage.py collectstatic --noinput
```
