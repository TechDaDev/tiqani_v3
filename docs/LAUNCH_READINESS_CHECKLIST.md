# Launch Readiness Checklist

## Environment

- [ ] `SECRET_KEY` — long, random, unique, rotated from default
- [ ] `DEBUG=False` in `.env` or production environment
- [ ] `ALLOWED_HOSTS` — set to real domain(s)
- [ ] `DATABASE_URL` — PostgreSQL, not SQLite
- [ ] Redis URLs configured (`CELERY_BROKER_URL`, `CHANNEL_LAYERS_REDIS_URL`)
- [ ] Celery worker running
- [ ] Celery Beat running (or DatabaseScheduler active)
- [ ] S3/Media settings configured (`USE_S3_MEDIA=True`)
- [ ] Sentry DSN configured
- [ ] CORS origins set to frontend domain(s)
- [ ] CSRF origins set to frontend domain(s)
- [ ] Email settings configured (SMTP)
- [ ] WebSocket URL matches production

## Security

- [ ] Admin accounts created with strong passwords
- [ ] Password reset flow verified
- [ ] OTP verification flow verified
- [ ] JWT token expiry reviewed (default: 120 min access, 7 day refresh)
- [ ] Rate limits reviewed and documented
- [ ] API docs protected in production (`API_DOCS_PUBLIC=False`)
- [ ] Private media protected (S3 presigned URLs)
- [ ] Audit export tested
- [ ] Request ID header verified (`X-Request-ID`)
- [ ] CORS not set to `*` in production

## Finance

- [ ] Wallet flows tested (deposit, withdrawal, balance check)
- [ ] Dealership recharge flow tested
- [ ] Dealership cash-out flow tested
- [ ] Settlement flow tested
- [ ] Guarantee threshold alerts verified
- [ ] Credit ledger audit trail verified
- [ ] Platform fee configuration active

## Operations

- [ ] Health endpoints respond (`/api/health/live/`, `/ready/`, `/deep/`)
- [ ] Docker Compose config valid
- [ ] Sentry test event received
- [ ] Log format verified (JSON or verbose)
- [ ] Backup/restore procedure tested
- [ ] Incident response plan reviewed
- [ ] `check_operations_ready` passes
- [ ] `audit_api_consistency` passes
- [ ] `audit_permissions` passes
- [ ] `final_backend_qa` passes

## Monitoring

- [ ] Sentry error tracking active
- [ ] Celery health check task running
- [ ] Worker ping task running
- [ ] Logs shipping to aggregation system (if applicable)
- [ ] Docker HEALTHCHECK configured
- [ ] Load balancer health probes configured

## Frontend / Mobile Handoff

- [ ] API schema URL provided (`/api/schema/`)
- [ ] Documentation URLs provided (`/api/docs/`, `/api/redoc/`)
- [ ] Postman collections up to date
- [ ] WebSocket connection docs provided
- [ ] Media upload docs provided
- [ ] Permission matrix provided
- [ ] Demo accounts available
- [ ] Known limitations documented

## Pre-Launch

- [ ] Run `python manage.py check --deploy`
- [ ] Run full test suite: `python manage.py test`
- [ ] Run `python manage.py check_operations_ready`
- [ ] Run `python manage.py final_backend_qa`
- [ ] Verify all health endpoints
- [ ] Verify schema/docs endpoints
- [ ] Run `python manage.py audit_api_consistency`
- [ ] Run `python manage.py audit_permissions`
- [ ] Run `python manage.py performance_smoke_test`
- [ ] Review Sentry for any unexpected errors
- [ ] Verify no pending migrations
- [ ] Verify Docker build succeeds
