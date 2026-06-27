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

Final fixture gate:
- Reset command: `E2E_FIXTURE_PASSWORD='local-test-only' python manage.py seed_e2e_fixtures --reset --force`
- Removed 43 fixture users and related records before reseed.
- Reviews: 3.
- Review reports: 1.
- Moderation actions: 1.
- Reputation snapshots: 3.
- Notifications: 126.
- Notification prefs: 1.
- Full backend suite: 1028 passed.
- Full Playwright suite: 371 passed.

Integrity proof:
- Published visible verified reviews: 2.
- Hidden reviews: 1.
- Duplicate `contract + reviewer + reviewee`: 0.
- Invalid ratings: 0.
- Self reviews: 0.
- Duplicate notification keys: 0.
- Owner-B notification fixture isolated from primary client: true.
