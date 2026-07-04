# Phase 7 Payment State Machine

## Funding Status (derived from PaymentIntent records)

```
UNFUNDED ──→ PENDING ──→ FUNDED  (success)
                │
                └──→ FAILED ──→ PENDING (retry)
```

Derived by `get_contract_funding_status()` at `wallet/services.py`.

## PaymentIntent Status

```
PENDING ──→ PAID
PENDING ──→ FAILED
FAILED  ──→ PENDING (retry via new intent creation)
PAID    ──→ (terminal)
CANCELED──→ (terminal)
```

## Contract Funding Transitions

- `UNFUNDED`: No CONTRACT_FUNDING PaymentIntent exists
- `PENDING`: Active (non-terminal, non-canceled) PaymentIntent exists
- `FUNDED`: At least one PAID PaymentIntent exists
- `FAILED`: All intents are in FAILED state

## Escrow

Escrow=held when contract.escrow_amount == contract.agreed_amount.
Set atomically during sandbox payment confirmation success.
