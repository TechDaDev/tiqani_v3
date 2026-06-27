# Phase 11 Backend

## Scope

Phase 11 backend reuses existing apps:
- `ratereview` for reviews, moderation, and reputation.
- `notification` for in-app notifications, read state, realtime hooks, and preferences.

No duplicate review or notification app was created.

## Endpoints

Participant:
- `GET /api/contracts/<contract_id>/review-eligibility/`
- `POST /api/contracts/<contract_id>/reviews/`
- `GET /api/reviews/<review_id>/`
- `PATCH /api/reviews/<review_id>/`
- `POST /api/reviews/<review_id>/report/`
- `GET /api/users/<user_id>/reputation/`
- `GET /api/users/<user_id>/reviews/`
- `GET /api/notifications/`
- `GET /api/notifications/unread-count/`
- `POST /api/notifications/<notification_id>/mark-read/`
- `POST /api/notifications/mark-all-read/`
- `GET /api/notifications/preferences/`
- `PATCH /api/notifications/preferences/`

Staff:
- Existing `/api/admin/reviews/`
- Existing `/api/admin/reviews/flagged/`
- Existing `/api/admin/reviews/<review_id>/hide/`
- Existing `/api/admin/reviews/<review_id>/publish/`
- Existing direct `/api/reviews/<review_id>/moderate/*`

## Review Policy

Eligibility is centralized in `ratereview.services.get_review_eligibility`.

Rules:
- Actor must be client or technician on the contract.
- Contract must be `completed`.
- Actor cannot review themselves.
- Open or in-progress disputes block review creation.
- One review per `contract + reviewer + reviewee`.
- Repeat create returns the existing review idempotently.

Edit policy:
- Reviewer may edit once.
- Edit window defaults to 14 days.
- Hidden, flagged, or moderated reviews cannot be edited.
- Moderation preserves original review history.

## Reputation

`UserReputationSnapshot` stores backend-owned aggregates:
- Average rating.
- Review count.
- 1-5 star distribution.
- Completed contract count.
- Transparent label: `new`, `established`, `highly_rated`.

Frontend values are display-only and never authoritative.

## Notifications

`Notification.deduplication_key` prevents duplicate event notifications.

`NotificationPreference` stores in-app category preferences. Email and push fields exist only as inactive/deferred flags.

Focused event dedupe was added through `create_notification_once`.

## Final Regression Closure

Commands run:
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py spectacular --file docs/openapi-schema.yml`
- `E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures --reset --force`
- `E2E_FIXTURE_PASSWORD='local-test-only' python manage.py test --keepdb --noinput`

Result:
- PostgreSQL vendor/host/port verified as `postgresql`, `127.0.0.1`, `5433`.
- Fixture reset completed with 3 reviews, 1 report, 1 moderation action, 3 reputation snapshots, 126 notifications, and 1 notification preference.
- Integrity proof found 0 duplicate review contracts, 0 invalid ratings, 0 self reviews, 0 duplicate notification keys, preserved moderation content, and matched reputation snapshot averages.
- Django checks passed.
- Migration dry run passed with no model changes.
- OpenAPI schema regenerated successfully.
- Full backend suite passed: 1028 tests in 1308.954s.
- Initial full-suite pass exposed missing moderation activity logging in the shared `moderate_review` service. The service now emits `review_moderated` activity records; focused regression passed, then the full suite passed.

Known warning:
- Existing DRF `min_value should be an integer or Decimal instance`.
- Redis is not running locally, so realtime notification delivery logs non-fatal connection warnings.
- Existing readiness smoke tests log database-threading errors inside expected failure coverage; suite result remains OK.
- OpenAPI generation still reports existing schema warnings/errors but exits 0.

Deferred:
- Production email, SMS, and push delivery providers.
- ML fraud scoring and advanced trust scoring.
- Large admin redesign.
