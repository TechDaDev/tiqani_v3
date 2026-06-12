# Production Checklist — tiqani_v3

Verify each item before deploying to production.

## Configuration

- [ ] `DEBUG=False` in environment
- [ ] Strong, unique `SECRET_KEY` (at least 50 random characters)
- [ ] `ALLOWED_HOSTS` set to your domain(s)
- [ ] `DATABASE_URL` points to production PostgreSQL (not SQLite)
- [ ] `CORS_ALLOWED_ORIGINS` set to your frontend domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS` set to your frontend domain(s)
- [ ] `EMAIL_BACKEND` configured for SMTP
- [ ] SMTP credentials are valid and tested

## Security

- [ ] HTTPS enabled (SSL/TLS certificate installed)
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] HSTS configured (default: 1 year)
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF=True`
- [ ] `X_FRAME_OPTIONS=DENY`
- [ ] Database password is strong and unique
- [ ] Admin user has strong password
- [ ] No secrets committed to git (check .env is in .gitignore)
- [ ] Platform wallet credentials are secured

## Database

- [ ] Database backup configured (daily minimum)
- [ ] Backup retention policy in place
- [ ] Database connection pooling configured if needed
- [ ] Migration safety reviewed (no long-running locks expected)

## Application

- [ ] Migrations run successfully
- [ ] `collectstatic` run and files are accessible
- [ ] Platform fees seeded: `python manage.py seed_platform_fees`
- [ ] Superuser/admin account created
- [ ] Health endpoint returns 200: `GET /api/health/`
- [ ] All tests pass: `python manage.py test`
- [ ] No pending migrations: `python manage.py makemigrations --check --dry-run`
- [ ] Django system checks pass: `python manage.py check`

## Monitoring & Logging

- [ ] Logging configured (console at minimum)
- [ ] Error tracking configured (Sentry or similar)
- [ ] Uptime monitoring in place
- [ ] Database query monitoring configured
- [ ] Disk space / S3 bucket size monitoring for media uploads
- [ ] S3 lifecycle policy configured for cost control (see `docs/MEDIA_STORAGE.md`)

## Performance

- [ ] Gunicorn worker count set appropriately (`2 * CPU + 1`)
- [ ] Static files compressed and cached
- [ ] Database indexes reviewed
- [ ] API rate limiting configured

## Operations

- [ ] Deployment rollback plan documented
- [ ] Access to production servers restricted
- [ ] SSH keys / VPN configured for admin access
- [ ] Incident response contact defined
- [ ] Regular dependency update schedule established
