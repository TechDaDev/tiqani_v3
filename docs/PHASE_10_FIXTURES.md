# Phase 10 Fixtures

## E2E Fixture Scenarios
The `seed_e2e_fixtures` command should be extended to create:

1. Active contract eligible for dispute
2. Completion-requested contract
3. Completed pre-settlement contract
4. Settled recoverable contract
5. Settled partially recoverable contract
6. Settled non-recoverable contract
7-30. Various dispute states and workflows

## Deterministic UUIDs
All mutable records use deterministic UUIDs for repeatability.

## Fixture Repeatability
Run twice with `--reset --force`:
- Same dispute UUIDs
- Same refund UUIDs
- Same chargeback UUIDs
- Same balances
- Same status counts

## PostgreSQL Closure Evidence

Phase 10 closure used PostgreSQL only:
- Docker container: `tiqani_phase10_postgres`
- Host: `127.0.0.1`
- Port: `5433`
- Database: `tiqani_db`
- Django vendor: `postgresql`

SQLite is not a closure path for Phase 10 dispute/refund/settlement validation.

Final deterministic reset produced:
- Service requests: 7
- Chat messages: 5
- Offers: 5
- Payment intents: 30
- Wallet transactions: 15
- Execution milestones: 13
- Completion requests: 3
- Disputes: 16
- Dispute statements: 17
- Dispute evidence: 1
- Dispute resolutions: 9
- Dispute audit events: 62
- Refunds: 6
- Chargebacks: 5
- Liabilities: 2

The liability count is intentionally 2:
- One open liability
- One partially recovered liability

The manual-recovery fixture must not create a duplicate liability outside the refund/reversal service path.
