# Release Checklist

- [ ] Tests pass with `python manage.py test`
- [ ] `python manage.py makemigrations --check --dry-run` passes
- [ ] `python manage.py check --deploy --settings=simtrack.settings.prod` passes with production env vars
- [ ] `ruff check .` passes
- [ ] `black --check .` passes
- [ ] `isort --check-only .` passes
- [ ] No secrets are committed
- [ ] `.env.example` is current
- [ ] README is updated
- [ ] Changelog is updated
- [ ] Demo data works
- [ ] Version tag is created
- [ ] Static assets build with `npm run build-css`
