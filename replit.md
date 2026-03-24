# ConformExpert — Replit Setup

## Project Overview

ConformExpert is a Django web application for analyzing thermal compliance documents (RT2012, RE2020, DPE, etc.) for French building regulations. It uses Claude AI (Anthropic) to extract and validate thermal performance data from PDFs.

## Architecture

- **Backend**: Django 5.2 (Python 3.12) with Django REST Framework
- **Database**: PostgreSQL (Replit managed), fallback to SQLite
- **Static files**: WhiteNoise
- **Email**: SendGrid
- **AI**: Anthropic Claude API for PDF analysis
- **Web server**: Gunicorn on port 5000

## Key Directories

- `backend/` — Django settings, URLs, WSGI/ASGI config
- `main/` — Main app: models, views, templates, migrations, forms
- `main/templates/main/` — Django HTML templates
- `main/migrations/` — Database migrations
- `staticfiles/` — Collected static files (generated)
- `media/` — User uploaded PDFs and files
- `frontend/` — Unused React app (legacy, not active)
- `src/` — Unused React components (legacy, not active)

## Environment Variables

- `SECRET_KEY` — Django secret key (has a dev default)
- `DEBUG` — Django debug mode (default: True)
- `DATABASE_URL` — PostgreSQL connection string (auto-set by Replit)
- `ANTHROPIC_API_KEY` — Claude AI API key for document analysis
- `SENDGRID_API_KEY` — SendGrid API key for emails
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` — Gmail SMTP credentials
- `CONTACT_EMAIL` — Contact email address
- `DJANGO_SUPERUSER_PASSWORD` — Auto-create admin superuser

## Running Locally

The "Start application" workflow runs:
```
python manage.py migrate && python manage.py collectstatic --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:5000 --timeout 120 --workers 2
```

## Deployment

Configured for autoscale deployment:
- **Build**: `python manage.py migrate && python manage.py collectstatic --noinput`
- **Run**: `gunicorn --bind=0.0.0.0:5000 --reuse-port --timeout=120 --workers=2 backend.wsgi:application`

## Notes

- Migrations 0008 and 0009 were patched to handle the missing `main_documentfile` table in the existing database
- ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS are configured for Replit domains
- SSL redirect is disabled for development (controlled by `SECURE_SSL_REDIRECT` env var)
