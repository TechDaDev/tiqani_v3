# Administration

## Capabilities

- Dashboard statistics.
- User listing, detail, suspension, and restoration.
- Technician listing, approval, and suspension.
- Contract oversight and force-cancel for eligible contracts.
- Review moderation and report oversight.
- Finance visibility across payment intents, platform earnings, withdrawals, refunds, chargebacks, and settlements.
- Dispute oversight and resolution workflows.
- Audit trail viewing.

## Action Policy

Administrative write actions must:
- require staff permission;
- validate reason;
- record actor, target, timestamp, previous state, new state, and reason;
- avoid hard deletion of financial or contract history.

## Non-Destructive Rule

Do not hard-delete:
- contracts;
- payments;
- refunds;
- disputes;
- reviews;
- ledger entries;
- audit events.
# Wallet Recharge Administration

Finance admins review wallet recharge requests from the admin financial recharge queue.
Approval credits the user wallet once and links the request to the resulting wallet transaction.
Rejection records the finance review note and leaves the wallet balance unchanged.
Receipt access is restricted to the request owner and finance/admin reviewers.
