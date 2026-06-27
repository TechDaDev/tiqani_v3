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

## Focused Validation

Commands run:
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test ratereview.tests.test_phase11_services --noinput --keepdb`
- `python manage.py test ratereview notification --noinput --keepdb`

Result:
- Phase 11 service tests: 8 passed.
- Combined review/notification suite: 111 passed.

Known warning:
- Existing DRF `min_value should be an integer or Decimal instance`.
- Local PostgreSQL no-keepdb run passed all 111 tests but exited 1 during teardown because one session held `test_tiqani_db`; same suite passed with `--keepdb`.
- Redis is not running locally, so realtime notification delivery logs non-fatal connection warnings.
