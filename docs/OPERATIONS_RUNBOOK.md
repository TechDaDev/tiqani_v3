# Operations Runbook

## Overview

This document covers day-to-day operational procedures for the tiqani_v3
platform.  It complements the deployment and monitoring docs.

## Health Endpoints

| Endpoint | Purpose | Expected Status |
|---|---|---|
| `GET /api/health/` | Readiness (alias) | 200 + `database: "ok"` |
| `GET /api/health/live/` | Liveness probe | 200 + `status: "alive"` |
| `GET /api/health/ready/` | Readiness (explicit) | 200 + `database: "ok"` |
| `GET /api/health/deep/` | Deep check (DB + Celery) | 200 if all green, 503 otherwise |

## Management Commands

### `check_operations_ready`

Verifies all production dependencies in one shot:

```bash
python manage.py check_operations_ready
```

Checks: database connectivity, Sentry DSN, Celery broker, channel layer,
static files directory, log format, and APP_VERSION env var.

### `export_audit_logs`

Exports security-relevant events as JSON (default) or CSV:

```bash
python manage.py export_audit_logs --days 30 --format json
python manage.py export_audit_logs --days 7 --format csv > audit.csv
```

Sources: admin LogEntry, token blacklist, user login/registration events.

### `check_celery_setup`

Verifies Celery configuration (from Phase 13):

```bash
python manage.py check_celery_setup
```

### `check_realtime_setup`

Verifies WebSocket / Channels configuration (from Phase 14):

```bash
python manage.py check_realtime_setup
```

## Celery Beat Tasks

| Task | Interval | Description |
|---|---|---|
| `celery_health_check_task` | 5 min | Verifies worker responsiveness |
| `celery_ping_workers_task` | 5 min | Pings all workers, reports count |
| `send_sentry_test_event_task` | 1 hour | Sends test event to Sentry |
| `generate_media_orphan_report_task` | Daily | Dry-run orphan media report |
| `cleanup_old_read_notifications_task` | Daily | Purges old read notifications |
| `otp_cleanup_task` | Hourly | Cleans expired OTP codes |

## Docker HEALTHCHECK

Both `docker-compose.yml` and `docker-compose.prod.yml` include a
HEALTHCHECK that runs `check_operations_ready` every 30 s.
