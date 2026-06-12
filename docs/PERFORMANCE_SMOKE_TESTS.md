# Performance Smoke Tests

## Overview

The `performance_smoke_test` management command runs lightweight performance
checks on critical read-only endpoints using Django's RequestFactory.

It is NOT a replacement for real load testing — it verifies that endpoints
respond within reasonable time ranges on the current infrastructure.

## Usage

```bash
# Default: 5 iterations per endpoint
python manage.py performance_smoke_test

# Custom iterations
python manage.py performance_smoke_test --iterations 10

# JSON output (for monitoring systems)
python manage.py performance_smoke_test --iterations 3 --json
```

## Endpoints Tested

| Endpoint | Purpose |
|---|---|
| `GET /api/health/` | Health summary |
| `GET /api/health/live/` | Liveness (fastest — no DB) |
| `GET /api/health/ready/` | Readiness (DB check) |
| `GET /api/health/deep/` | Deep health (DB + Celery ping) |
| `GET /api/categories/` | Public listing |

## Interpreting Results

- **Health/live**: Should be < 1ms (pure in-memory response)
- **Health/ready**: Should be < 10ms (simple DB connection check)
- **Categories**: Should be < 100ms (depends on DB and cache)
- **Health/deep**: Can be slow (up to several seconds) because it tries to
  ping Celery workers with a timeout — expected to be slow without Redis.

## Integration with Monitoring

```bash
# Alert if any endpoint exceeds 500ms average
python manage.py performance_smoke_test --json | python -c "
import json, sys
results = json.load(sys.stdin)
for r in results:
    if r['avg_ms'] > 500 and r['label'] not in ('Deep Health',):
        print(f'SLOW: {r[\"endpoint\"]} avg={r[\"avg_ms\"]}ms')
        sys.exit(1)
print('All endpoints OK')
"
```

## What This Does NOT Cover

- Authenticated endpoints (requires session/token setup)
- Write endpoints (POST/PUT/DELETE)
- Concurrent/load testing
- External service latency (S3, email, Sentry)
- WebSocket performance
