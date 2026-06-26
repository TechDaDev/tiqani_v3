# Phase 10 Reconciliation

Per disputed contract, the reconciliation extends Phase 9 to return:
- funded_total, principal, escrow original
- original settlement amounts
- recovered technician amount
- refunded client amount
- reversed platform fees
- remaining escrow
- outstanding liability
- chargeback exposure
- refund status
- dispute status
- reconciliation status

## Reconciliation Statuses
| Status | Meaning |
|---|---|
| BALANCED | All financial records match |
| DISPUTED | Active dispute exists |
| REFUND_PENDING | Refund in progress |
| PARTIALLY_RECOVERED | Only partial recovery achieved |
| MANUAL_RECOVERY_REQUIRED | Outstanding liability exists |
| MISMATCH | Discrepancy found |
| CLOSED_BALANCED | Dispute closed, financials match |

## Service
`get_dispute_reconciliation()` returns structured data for a dispute.

## PostgreSQL Financial Proof

Final proof ran against PostgreSQL (`127.0.0.1:5433/tiqani_db`).

Aggregate status counts:
- Refunds: 5 completed, 1 failed
- Liabilities: 1 open, 1 partially recovered
- Chargebacks: 5 received
- Negative user wallets: 0
- Negative platform wallets: 0

Scenario coverage:
- `full-refund`: pre-settlement, 500000.00 client refund, no liability, no platform reversal.
- `partial-refund`: pre-settlement, 200000.00 client refund, no liability, no platform reversal.
- `split-resolution`: 250000.00 client refund.
- `post-settle-refund`: settlement preserved, 500000.00 refund, 500000.00 technician reversal, 25000.00 platform reversal, seeded remaining liability 60000.00.
- `manual-recovery`: settlement preserved, 300000.00 refund, 300000.00 technician reversal, 15000.00 platform reversal, remaining liability 50000.00.
- `closed`: no refund and no liability.

Chargebacks in the E2E fixture set are sandbox exposure/status fixtures only. All five remain `received`; no outcome is set in closure evidence.

## Validation Gates

Backend:
- Targeted PostgreSQL fixture regression after liability fix: `Ran 19 tests in 101.003s OK`.
- Full backend regression: `Ran 671 tests in 945.331s OK`.
- `manage.py check`: passed with existing DRF `min_value` schema warning.
- `makemigrations --check --dry-run`: no changes detected.
- `spectacular --file docs/openapi-schema.yml`: generated with existing schema documentation warnings/errors.

Frontend:
- Final full Playwright run: `360 passed (25.0m)`.
- Previous full Playwright runs also passed: `360 passed (25.4m)` and `360 passed (24.9m)`.
- Dispute gates passed with workers 4 and serial workers 1.
- Reverse-order mutation gate passed: 29 tests.
- Independent suite matrix passed: auth, marketplace, requests, messages, offers, payments, execution, settlement, disputes.
- `npm run lint`: passed with existing warnings.
- `npx tsc --noEmit`: passed before and after final offer detail wait fix.
- `vitest`: 49 files, 552 tests passed.
- `next build`: passed.
- `npm audit`: 8 known vulnerabilities remain (6 moderate, 1 high, 1 critical); fixes require breaking package upgrades.

Known residual warnings:
- Next lint deprecation and hook dependency warnings.
- Vite CJS deprecation, Intl missing-message warnings, jsdom navigation warning, React `act` warnings.
- Playwright `NO_COLOR` warnings under `FORCE_COLOR`.
- Negative-path empty-body JSON parse warning in `app/api/milestones/[milestoneId]/submit/route.ts`.
- Production payment provider integration remains outside Phase 10 fixture closure.
