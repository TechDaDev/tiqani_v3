# Payment Security — Phase 7

## Amount Authority

- Amount derives from contract agreed_amount + fee config
- Browser-submitted amount ignored
- Backend calculates `client_total_amount` from ContractPaymentBreakdown

## IDOR Prevention

- ContractFundingEligibilityView: checks contract ownership
- ContractPaymentIntentCreateView: checks eligibility (contract owner)
- ContractFundingStatusView: participant-only (client/technician)
- PaymentIntentSandboxConfirmView: authenticated only

## Production Sandbox Guard

- `is_sandbox_enabled()` checks `settings.DEBUG or PAYMENT_SANDBOX_ENABLED`
- Sandbox confirmation raises RuntimeError(503) if not enabled

## Private Fields Not Exposed

PaymentIntentSerializer excludes: card number, CVV, payment token, provider secret, webhook secret, raw provider payload, internal exceptions, private contact info.

## Idempotency

- `create_contract_payment_intent`: checks for existing non-terminal intent before creating
- `confirm_sandbox_payment`: checks `status != PAID`, raises ValueError if already paid
- `select_for_update` used for row-level locking
