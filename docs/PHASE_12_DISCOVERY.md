# Phase 12 Discovery

## Current Readiness

- Backend already has environment-separated settings, PostgreSQL support, Redis/Channels/Celery hooks, Sentry hook, structured logging filter, upload validators, Docker/Compose files, and health endpoints.
- Admin APIs already cover dashboard summary, users, technicians, contracts, reviews, finance, disputes, refunds, chargebacks, withdrawals, dealerships, and activity logs.
- Frontend already has HTTP-only cookie auth, same-origin proxy routes, admin dispute/review/finance screens, and full Playwright coverage from prior phases.

## Gaps Found

- Admin API names did not fully match Phase 12 aliases: `/api/admin/dashboard/`, `/api/admin/platform-health/`, `/api/admin/platform-statistics/`, `/api/admin/audit-events/`, suspend/restore aliases.
- Some admin write actions accepted missing reasons and did not include previous/new state in activity metadata.
- Readiness output exposed local debug state and deep health exposed dependency error strings.
- Frontend admin navigation omitted staff admin areas added across prior phases.
- Frontend security headers were not configured in `next.config.ts`.
- Production docs existed in fragments but not as final deployment, rollback, operations, backup, observability, and checklist runbooks.

## Security Findings

- JWTs live in HTTP-only cookies on the frontend and are forwarded server-side only.
- DRF throttles exist for auth, wallets, chat, reviews, notifications, and schema. Phase 12 adds `admin_write`.
- Upload validators reject executable extensions, blocked MIME types, and oversized profile/document/proof files. Antivirus scanning is not implemented.
- Local Redis absence causes non-fatal realtime warnings.

## Deployment Findings

- Dockerfile uses non-root runtime user and Gunicorn default command.
- Compose files include PostgreSQL, Redis, web, Celery worker, and Celery beat.
- Production compose currently uses Daphne for WebSocket support; Gunicorn is documented for HTTP-only deployment.
- Nginx reference config was missing.

## Implementation Plan

1. Add missing admin aliases and Phase 12 admin write policy.
2. Harden readiness response and production secret validation.
3. Add focused backend tests for admin/security/config.
4. Add frontend admin dashboard/users/technicians/audit/system pages, role guard, security headers, and focused tests.
5. Add focused Playwright coverage.
6. Add production runbooks, backup scripts, and release docs.

## Release Blockers

- Production secrets, real domains, TLS certificates, SMTP credentials, Sentry DSN, Redis URL, and database credentials must be supplied by deployment environment.
- Antivirus scanning, production SMS/push providers, ML fraud scoring, advanced trust scoring, and multi-region infrastructure remain deferred.
