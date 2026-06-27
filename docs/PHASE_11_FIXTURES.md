# Phase 11 Fixtures

Deterministic labels use:

`uuid5(NAMESPACE_DNS, "e2e-p11-{label}.tiqani.local")`

Contracts:
- `client-review-eligible-contract`
- `create-review-contract`
- `technician-review-eligible-contract`
- `incomplete-contract`
- `disputed-contract`
- `reviewed-contract`

Reviews and moderation:
- `published-review`
- `hidden-review`
- `reported-review`
- `review-report`
- `hidden-review-moderation`

Notifications and preferences:
- `unread-notification`
- `read-notification`
- `notification-owner-b`
- Client `NotificationPreference`

Reputation:
- `e2e-approved-tech@tiqani.local` has deterministic published review aggregation.
- `e2e-approved-tech2@tiqani.local` is the no-review/owner-B notification fixture.
- `e2e-client@tiqani.local` has client-role reputation snapshot.

Reset behavior:
- `seed_e2e_fixtures --reset` deletes Phase 11 reviews, dimensions, reports, moderation actions, reputation snapshots, notifications, and preferences tied to fixture users/contracts before deleting users/contracts.
- Two reset+seed runs were verified with stable deterministic IDs and expected eligibility states.

Focused E2E fixture gate:
- 5 spec files under `e2e/reviews` and `e2e/notifications`.
- 11 focused Playwright tests.
- `CI=1 PLAYWRIGHT_HTML_OPEN=never NEXT_DIST_DIR=.next-e2e npx playwright test e2e/reviews e2e/notifications --workers=2 --retries=0 --reporter=line`: 11 passed.
