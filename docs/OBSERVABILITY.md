# Observability

## Logs

- Use `LOG_FORMAT=json` in production.
- Logs include timestamp, level, logger, message, and request id where available.
- Sensitive fields are redacted.

## Error Monitoring

- Sentry is optional and enabled only when `SENTRY_DSN` is present.
- `send_default_pii=False` is configured.

## Health Monitoring

- `/api/health/`: summarized readiness alias.
- `/api/ready/`: database/config readiness without secrets.
- `/api/health/live/`: process liveness.
- `/api/health/deep/`: deeper diagnostic endpoint; restrict at proxy if exposed externally.

## Metrics

Full metrics/OpenTelemetry export is deferred. Add provider-specific instrumentation after deployment target is selected.
