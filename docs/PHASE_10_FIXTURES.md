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
