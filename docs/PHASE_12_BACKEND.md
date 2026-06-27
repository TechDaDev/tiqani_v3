# Phase 12 Backend

## Scope

Phase 12 backend prepares Tiqani for controlled production deployment through admin operations, security hardening, readiness checks, deployment artifacts, backup tooling, and release documentation.

## Admin Additions

- Added aliases:
  - `GET /api/admin/dashboard/`
  - `GET /api/admin/platform-health/`
  - `GET /api/admin/platform-statistics/`
  - `GET /api/admin/audit-events/`
  - `POST /api/admin/users/<id>/suspend/`
  - `POST /api/admin/users/<id>/restore/`
  - `POST /api/admin/technicians/<id>/suspend/`
  - `GET /api/admin/payments/`
  - `GET /api/admin/refunds/`
- Admin write actions now require a reason and write `ActivityLog` metadata with previous state, new state, actor, target, and reason.
- No destructive financial-history deletion was added.

## Security

- Added `admin_write` DRF throttle scope.
- Added `ScopedRateThrottle` alongside anon/user throttles.
- `DJANGO_SECRET_KEY` is supported and production rejects missing or placeholder secret keys.
- `/api/ready/` is available and returns summarized dependency status without credentials, stack traces, or topology.
- `/api/health/` remains backward-compatible.

## Focused Validation

- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: passed.
- `python manage.py test dashboard.tests.test_phase12_admin_ops --keepdb --noinput`: 19 passed.

## Known Warnings

- Existing DRF `min_value should be an integer or Decimal instance` warning remains.
- Redis realtime warnings remain expected locally when Redis is absent.

## Deferred

- Antivirus scanning.
- Production SMS/push providers.
- ML fraud scoring.
- Advanced trust scoring.
- Kubernetes, multi-region deployment, and autoscaling infrastructure.
