# Operations Runbook

## Daily

- Review admin audit events.
- Check failed payments, refunds, chargebacks, and withdrawals.
- Check Sentry/errors if configured.
- Verify backup job completion.

## Incident Response

1. Identify blast radius.
2. Put affected workflows in maintenance or staff-only mode where possible.
3. Preserve logs and audit events.
4. Stop destructive or financial mutation paths if needed.
5. Decide forward fix vs rollback.
6. Communicate status and resolution.

## Smoke Test

- Login.
- Admin dashboard.
- Marketplace.
- Contract detail.
- Payment/funding view.
- Dispute detail.
- Review flow.
- Notification feed.
- Health/readiness.
- Logout.
