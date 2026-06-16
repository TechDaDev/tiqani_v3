# Payments API — Phase 7

## Base URL
`/api/wallet/` (Next.js proxies via `/api/`)

## Endpoints

### Contract Funding Eligibility
- **GET** `/api/contracts/{id}/funding/eligibility/`
- Auth: Required (client)
- Returns: eligibility, funding_status, agreed_amount, client_total_amount
- 403: Not owner, 404: Not found

### Create Payment Intent
- **POST** `/api/contracts/{id}/funding/intents/`
- Auth: Required (client)
- Idempotent: returns existing pending intent
- Returns: PaymentIntent (201 CREATED)
- 400: Not eligible, already funded

### Contract Funding Status
- **GET** `/api/contracts/{id}/funding/status/`
- Auth: Required (client or technician)
- Returns: funding_status, escrow_amount, active_intent
- Technician: read-only, no active_intent details

### Sandbox Confirm Payment
- **POST** `/api/payments/{intentId}/sandbox-confirm/`
- Auth: Required (client)
- Body: `{"simulate_failure": true|false}`
- Returns: payment_intent + provider_result
- 503: Sandbox not enabled
- 400: Invalid state

## Payment States
- unfunded → pending → funded (success)
- unfunded → pending → failed (can retry)
- failed → pending (retry)
