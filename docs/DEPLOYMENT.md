# Deployment

## Release Candidate

Current candidate: `v1.0.0-rc.1`.

## Steps

1. Take PostgreSQL and media backups.
2. Pull release branch or tag.
3. Validate `.env.production` values.
4. Install dependencies.
5. Run `python manage.py check`.
6. Run `python manage.py makemigrations --check --dry-run`.
7. Run database migrations.
8. Run `python manage.py collectstatic --noinput`.
9. Start backend with Daphne for WebSockets or Gunicorn for HTTP-only.
10. Start Celery worker and beat when background jobs are enabled.
11. Build and start frontend in production mode.
12. Verify `/api/health/`, `/api/ready/`, login, marketplace, admin dashboard, payment, dispute, review, notifications, and logout.

## Backend Command

HTTP-only:

`gunicorn tiqani_v3.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120`

WebSocket-enabled:

`daphne -b 0.0.0.0 -p 8000 tiqani_v3.asgi:application`

Worker count guidance: start with `2 * CPU + 1` for Gunicorn and tune after measuring memory and latency.
