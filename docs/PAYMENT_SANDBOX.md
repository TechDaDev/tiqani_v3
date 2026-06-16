# Payment Sandbox — Phase 7

## Provider

Provider-neutral sandbox adapter at `wallet/sandbox_gateway.py`.

## Enable

```bash
PAYMENT_PROVIDER=sandbox  # default
PAYMENT_SANDBOX_ENABLED=true  # only needed when DEBUG=False
```

Production must NOT set `PAYMENT_SANDBOX_ENABLED=true`.

## Behavior

- `sandbox_confirm_payment()`: returns deterministic success/failure
- `simulate_failure=True`: returns failed result
- `simulate_failure=False/omitted`: returns success result
- No real funds, no credentials, no external API calls
