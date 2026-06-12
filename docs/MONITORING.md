# Monitoring & Alerting

## Sentry Integration

Sentry is configured in `tiqani_v3/settings/prod.py` and activated when
`SENTRY_DSN` is set in the environment.

### Configuration

| Env Variable | Default | Description |
|---|---|---|
| `SENTRY_DSN` | *(empty)* | Sentry project DSN — leave blank to disable |
| `SENTRY_ENVIRONMENT` | `development` | Tag sent with every event |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Performance tracing rate (0.0–1.0) |

No PII (personally identifiable information) is sent — `send_default_pii=False`.

### Manual Test

```bash
# Send a test event
python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('test', level='warning')"

# Or via Celery (runs every hour via Beat, or manually):
python manage.py shell -c "from tiqani_v3.tasks import send_sentry_test_event_task; send_sentry_test_event_task.delay()"
```

## Structured Logging

The project supports two log formats controlled by `LOG_FORMAT` env var:

- **`verbose`** (default, human-readable): `INFO 2026-06-12 12:00:00 ...`
- **`json`** (structured, machine-parseable): `{"asctime": "...", "levelname": "INFO", ...}`

### Sensitive-Data Redaction

The `SensitiveDataFilter` and `SensitiveHeaderFilter` in
`tiqani_v3/logging_filters.py` automatically mask:

- Passwords, tokens, secrets, API keys, credentials
- HTTP `Authorization`, `Cookie`, `X-API-Key` headers (in
  `django.request` logger)

### Request ID

Every HTTP response includes an `X-Request-ID` header.  The same ID is
available in log records as `request_id` when using the JSON log format,
enabling end-to-end tracing from HTTP through Celery tasks.

## Kubernetes / Docker Health Checks

| Probe | Endpoint / Command | Path |
|---|---|---|
| Liveness | `GET /api/health/live/` | Simple process check |
| Readiness | `GET /api/health/ready/` | Database connectivity |
| Deep | `GET /api/health/deep/` | DB + Celery ping |

For Docker Compose, the built-in HEALTHCHECK runs
`check_operations_ready`.

## Security Events

All security-sensitive operations emit structured events via
`tiqani_v3.security_events.log_security_event()`.  These appear in:

- The `security` logger at `WARNING` level
- Sentry breadcrumbs (when Sentry is active)

Export them via:

```bash
python manage.py export_audit_logs --days 30
```
