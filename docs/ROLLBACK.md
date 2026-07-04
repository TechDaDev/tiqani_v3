# Rollback

## Application Rollback

1. Stop web and worker processes.
2. Check whether database migrations were applied.
3. If no irreversible migration ran, deploy previous image/commit and restart services.
4. Verify `/api/health/` and `/api/ready/`.
5. Run smoke tests.

## Database Rollback

- Prefer forward fixes for migrated production databases.
- Restore PostgreSQL only after explicit incident decision, stakeholder approval, and fresh backup capture.
- Verify restored database with `python manage.py check` and read-only smoke tests before opening traffic.

## Frontend Rollback

1. Deploy previous frontend artifact.
2. Verify locale routes, login, admin dashboard, and proxy routes.
3. Clear CDN cache if applicable.
