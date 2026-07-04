# Phase 11 Discovery

## Baseline

Phase 11 starts from:
- Backend: `f7265ef323f4b102b28a576cdaaba42428c2d05e`
- Frontend: `f15b1b5fc2b92490a464580bf8844504c978d65d`

Branches:
- Backend: `backend/phase-11-reviews-notifications-trust`
- Frontend: `frontend/phase-11-reviews-notifications-trust`

Both branches were created from clean Phase 10 worktrees and pushed before implementation.

## Existing Backend Review Functionality

Reuse `ratereview`; do not create a duplicate `reputation` or `trust` app for review records.

Existing models:
- `ratereview.Review`
- `ratereview.ReviewHelpful`
- `ratereview.ReviewReport`

Existing review capabilities:
- Public technician review list: `GET /api/reviews/technician/<technician_id>/`
- Public review detail: `GET /api/reviews/<id>/`
- Client review creation: `POST /api/reviews/`
- Reviewer edit: `PATCH /api/reviews/<id>/`
- Technician response: `POST /api/reviews/<id>/respond/`
- Helpful action: `POST /api/reviews/<id>/helpful/`
- Report action: `POST /api/reviews/<id>/report/`
- Direct moderation endpoints under `/api/reviews/<id>/moderate/*`
- Admin review endpoints under `/api/admin/reviews/*`

Existing review constraints and behavior:
- `unique(reviewer, contract)` when `contract` is not null.
- Rating validators enforce 1-5.
- Reviews linked to a contract auto-set `is_verified`.
- Hidden reviews use `is_public=False`, not hard deletion.
- `TechnicianProfile.rate` is recalculated from public verified reviews.

Gaps against Phase 11:
- Reviews only target technicians; technician-to-client reviews are missing.
- Review eligibility is embedded in serializer validation, not a central service.
- Existing create path is not idempotent; duplicate review returns 400.
- No explicit unresolved-dispute eligibility check.
- No review status enum; visibility/moderation is split across booleans.
- No edit-window or edit-count policy.
- No moderation reason or moderation history model.
- No client reputation aggregation.
- No reputation snapshot model with rating distribution and completed-contract count.

## Existing Backend Notification Functionality

Reuse `notification`; do not create a duplicate notification implementation.

Existing models:
- `notification.Notification`
- `notification.ActivityLog`

Existing API:
- `GET /api/notifications/`
- `GET /api/notifications/unread-count/`
- `GET /api/notifications/<id>/`
- `POST /api/notifications/<id>/mark-read/`
- `POST /api/notifications/<id>/mark-unread/`
- `POST /api/notifications/mark-all-read/`
- `GET /api/notifications/activity/` for admin/staff activity

Existing service/realtime hooks:
- `create_notification`
- `mark_notification_read`
- `mark_all_notifications_read`
- `notify_admins`
- review, contract, wallet, payment, withdrawal, technician approval helpers
- Channels consumer for realtime notification events
- cleanup task for old read notifications

Gaps against Phase 11:
- No `deduplication_key`, so duplicate event notifications are possible.
- No `NotificationPreference` model.
- Notification text is stored as rendered English strings, not translation keys.
- Some financial notification text includes raw amounts; Phase 11 should avoid expanding that pattern for user-facing notifications.
- Mark-one-read view calls model method directly, bypassing service realtime helper.

## Existing Profile, Trust, And Rating Fields

Existing profile fields:
- `TechnicianProfile.rate`
- `TechnicianProfile.approved`
- `TechnicianProfile.is_available`
- profile completion fields on `BaseProfile`
- `ClientProfile.is_complete`

Existing frontend auth/user shape already carries:
- `rating`
- `total_reviews`

Existing public marketplace and technician cards display rating-related values.

Gaps:
- `total_reviews` is currently placeholder in multiple backend responses.
- No transparent trust labels.
- No completed-contract count shown as reputation evidence.
- No review-count distribution by rating.
- No distinction between technician reputation and client reputation.

## Existing Event Hooks

Reusable hooks:
- Contract completion notification helper in `notification.services.notify_contract_completed`
- Offer notification helpers in `contract.offer_services`
- Dispute notification helpers in `dispute.services`
- Wallet/settlement notification helpers in `wallet.settlement_services`
- Activity audit via `notification.services.create_activity`
- Dispute audit events via `DisputeAuditEvent`

Phase 11 should add only focused event integrations:
- review received
- review reported
- review hidden/restored
- reputation updated
- representative existing events only where already near existing notification calls

## Existing Frontend Functionality

Existing patterns to reuse:
- Same-origin API route proxies under `app/api/*`
- HTTP-only cookie auth via `authenticateProxy`
- Backend calls through `backend-client`
- Browser calls through `browser-client`
- Domain modules under `lib/<domain>/*`
- Protected shell navigation in `components/profile/auth-shell.tsx`
- Existing unread polling pattern for messages
- Localized namespaces in `messages/en.json`, `messages/ar.json`, `messages/ku.json`

Frontend gaps:
- No review domain modules.
- No reputation domain modules.
- No notification domain modules.
- No notification center page.
- No notification preference page.
- No review creation page.
- No user reviews page.
- No review moderation pages.
- No review/reputation components.
- No notification bell/badge integrated into protected navigation.

## Migration Risks

- Existing `Review` uses `technician` FK as required. Supporting technician-to-client reviews requires either adding nullable `reviewee` fields carefully or creating a new generalized contract review model. Safer path: evolve existing `Review` with explicit `reviewee`, `reviewer_role`, optional `technician`, and migration backfill for existing rows.
- Existing unique constraint is `reviewer, contract`; Phase 11 requires one review per `contract, reviewer, reviewee`. Need a new constraint before loosening behavior.
- Existing `Notification.notification_type` max length is 30. New event names must fit or field length must migrate.
- Adding `deduplication_key` must be nullable first, then unique when set.
- Existing tests expect duplicate review returns 400; Phase 11 idempotency may require test update.

## Permission Risks

- Review creation must validate both participant membership and intended reviewee server-side.
- Technician-to-client review must not allow arbitrary client reviewee injection.
- Hidden reviews should remain visible only to reviewer, reviewee, and staff according to documented policy.
- Notification detail/read endpoints already enforce recipient ownership; new frontend proxy routes must preserve this.
- Notification payload and target URL must not expose email, phone, wallet IDs, provider IDs, or secrets.
- Review moderation must remain staff/content-moderator only and record actor + reason.

## Recommended Architecture

Backend:
- Reuse `ratereview` for review, report, moderation, reputation services.
- Reuse `notification` for notification models/services, adding dedupe and preferences.
- Add central service functions:
  - `get_review_eligibility`
  - `create_contract_review`
  - `update_contract_review`
  - `report_review`
  - `moderate_review`
  - `restore_review`
  - `recalculate_user_reputation`
  - `create_notification_once`
- Add `UserReputationSnapshot` in `ratereview` unless a broader app becomes necessary.
- Add moderation history model rather than overloading booleans.
- Keep trust labels transparent: `new`, `established`, `highly_rated`.

Frontend:
- Add review, reputation, and notification domain modules with Zod validation and mappers.
- Add same-origin proxy routes for review, reputation, notification, and admin moderation endpoints.
- Add protected pages for review creation, notification center, notification preferences, and review moderation.
- Integrate reputation into profile and public technician pages.
- Add one compact navigation entry for notifications with unread count.

Testing:
- Keep Phase 11 focused: representative service/API tests, mapper/schema/component tests, and 12-18 Playwright tests.
- Avoid repeating every locale/status/viewport combination.
