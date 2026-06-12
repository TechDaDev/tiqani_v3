# Incident Response

## Severity Levels

| Level | Response Time | Example |
|---|---|---|
| P1 — Critical | Immediate | Service down, data loss, security breach |
| P2 — High | 1 hour | Feature broken for all users |
| P3 — Medium | 1 day | Feature broken for subset of users |
| P4 — Low | Next sprint | Cosmetic issue, non-critical bug |

## Response Steps

### 1. Detection

Health check endpoints:

```bash
curl http://app:8000/api/health/live/
curl http://app:8000/api/health/ready/
curl http://app:8000/api/health/deep/
```

### 2. Triage

- Check Sentry for recent errors
- Check Celery worker logs: `docker logs celery_worker --tail 100`
- Check database connectivity: `python manage.py check_operations_ready`
- Verify Redis: `redis-cli -h redis ping`

### 3. Mitigation

Common scenarios:

| Symptom | Likely Cause | Action |
|---|---|---|
| `database: "error"` | DB down / overloaded | Check PostgreSQL logs, restart container |
| `celery: "no_workers"` | Workers crashed | `docker compose restart celery_worker` |
| Sentry errors spike | Code regression | Rollback last deploy |
| 502 / 503 errors | Web process saturated | Increase replicas / workers |
| WebSocket disconnected | Redis / channel layer | `docker compose restart redis` |

### 4. Resolution

1. Apply hotfix or rollback
2. Verify via health endpoints
3. Confirm in Sentry that error rate drops

### 5. Postmortem

After every P1/P2 incident, create a postmortem covering:

- Timeline
- Root cause
- Detection gap
- Prevention plan
