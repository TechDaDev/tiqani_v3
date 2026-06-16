# Escrow Foundation — Phase 7

## Representation

Escrow=held when `Contract.escrow_amount == Contract.agreed_amount`.

Set atomically inside `confirm_sandbox_payment()` success path via `select_for_update` on PaymentIntent row.

## Current Model

No separate Escrow model. Escrow state inferred from:
- `Contract.escrow_amount` (Decimal, default 0)
- Successful PAID PaymentIntent with DEPOSIT+ESCROW WalletTransaction records

## Phase 7 Allowed States

- PENDING: contract unfunded, escrow_amount=0
- HELD: sandbox confirm success, escrow_amount=agreed_amount
- FAILED: payment failed, escrow_amount=0

## Not Implemented (Deferred)

- RELEASED
- PARTIALLY_RELEASED
- REFUNDED
- DISPUTED
