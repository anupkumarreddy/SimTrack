# Security Policy

## Supported Versions

Security fixes are accepted for the current `main` branch.

## Reporting Vulnerabilities

Do not open a public issue for a vulnerability. Report privately to the maintainers with:

- Description of the issue
- Reproduction steps
- Impact
- Suggested fix if available

Please do not disclose publicly until a fix is available.

## Security Basics

- Never commit `.env`, database files, or secrets.
- Use `simtrack.settings.prod` for production.
- Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Keep dependencies updated.
