# Release Notes

## v1.0.0-rc.1

- Added Phase 12 admin API aliases.
- Added reason-required admin write policy for user and technician state changes.
- Added admin write audit metadata with previous/new state.
- Added platform health/statistics endpoints.
- Hardened readiness output.
- Added `DJANGO_SECRET_KEY` production support and placeholder-secret rejection.
- Added backup/restore scripts and production runbooks.

Release-candidate closure evidence:

- Backend full regression: 1047 tests passed, 0 failures, 0 errors.
- Production readiness: passed against PostgreSQL.
- Gunicorn smoke: health and readiness endpoints passed without debug or secret fields.
- Deployment artifacts: compose configs, backup/restore syntax, workflow YAML, and secret scan passed.

Tag: `v1.0.0-rc.1-backend`.
