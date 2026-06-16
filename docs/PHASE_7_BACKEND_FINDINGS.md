# Phase 7 — Backend Findings

## Existing Payment Infrastructure

### Wallet App (`wallet/`)
Fully functional wallet app with:

- **Wallet** — one per user, holds `balance` in IQD (Decimal, 15 digits, 2 places)
- **WalletTransaction** — immutable ledger: DEPOSIT, WITHDRAWAL, PAYMENT, REFUND, ESCROW, RELEASE, PLATFORM_FEE
- **PaymentIntent** — purpose (CONTRACT_FUNDING, WALLET_DEPOSIT, WITHDRAWAL), provider (MANUAL), status (PENDING, REQUIRES_ACTION, PAID, FAILED, CANCELED), metadata JSON, paid_at
- **WithdrawalRequest** — for technician payouts (PENDING, APPROVED, REJECTED, PAID, CANCELED)
- **PlatformFeeConfig** — configurable fee rates (default: 10% tech commission, 5% client service fee)
- **ContractPaymentBreakdown** — snapshot of fee breakdown per contract
- **PlatformEarning** — ledger record of platform revenue per contract/stage
- **PlatformWallet** / **PlatformWalletTransaction** — global platform fee tracking

### Contract Model (`contract/models.py`)
Financial fields already present:
- `agreed_amount` (Decimal, 15 digits, 2 places)
- `currency` (CharField, default "IQD")
- `escrow_amount` (Decimal, default 0)
- `total_paid` (Decimal, default 0)
- `client_platform_fee`, `technician_platform_fee` (Decimal, default 0)
- `_setup_contract_escrow()` — locks agreed_amount in client wallet, creates WalletTransaction records

### Existing Services (`wallet/services.py`)
- `create_contract_funding_intent(contract, user)` — creates/reuses PaymentIntent for contract funding
- `mark_payment_intent_paid(payment_intent)` — marks PAID, credits wallet, creates WalletTransaction
- `ensure_contract_payment_breakdown(contract)` — creates fee breakdown snapshot
- `record_platform_earnings_for_contract(contract)` — records platform earnings
- `record_stage_release_with_fees(stage)` — stage approval with proportional fee release
- `create_withdrawal_request(...)` — creates withdrawal request

### Existing Endpoints (`wallet/urls.py`)
All under `/api/wallet/`:
- `me/` — wallet detail
- `transactions/` — transaction list
- `withdrawals/` — CRUD + approve/reject (admin)
- `payment-intents/` — list, detail, mark-paid (admin)
- `fee-config/` — CRUD (admin)
- `contracts/<uuid>/breakdown/` — contract payment breakdown

## Gaps for Phase 7

### Missing
1. **Idempotency key** on PaymentIntent — needs `idempotency_key` (unique, nullable)
2. **Sandbox gateway** — provider-neutral sandbox adapter for local/test
3. **Webhook endpoint** — secure webhook receiver
4. **Contract funding eligibility endpoint** — check if contract can be funded
5. **Create payment intent for contract** — client-facing endpoint (existing `create_contract_funding_intent` is service-only)
6. **Confirm sandbox payment** — trusted internal confirmation
7. **Funding status on contract** — need `funding_status` field or use existing PaymentIntent status
8. **E2E fixture seeds** — deterministic payment fixtures

### What Already Works
- Money representation: Decimal, IQD, 2 decimal places
- PaymentIntent model with contract/user/amount/currency/status
- Contract financial fields: agreed_amount, escrow_amount, total_paid
- Fee calculation service
- Wallet credit on payment

## Phase 7 Plan

1. Add `funding_status` to Contract model
2. Add `idempotency_key` to PaymentIntent
3. Create sandbox gateway service
4. Create funding eligibility endpoint
5. Create client-facing create payment intent endpoint
6. Create sandbox confirm success/failure endpoints
7. Create webhook receiver endpoint
8. Create funding status endpoint
9. Update E2E fixtures with deterministic payment states
10. Tests for all new endpoints
