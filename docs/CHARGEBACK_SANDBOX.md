# Chargeback Sandbox

## Overview
Sandbox chargeback events allow testing the chargeback workflow without real payment provider integration.

## Creation
Staff creates via `POST /api/admin/chargebacks/sandbox-create/`
- Requires contract_id, amount, optional reason_code
- Deterministic provider reference (`sandbox-cb-{hex}`)
- Idempotent via idempotency_key

## Lifecycle
1. `RECEIVED` → Event created, notification to admins
2. `UNDER_REVIEW` → Staff reviews
3. `EVIDENCE_SUBMITTED` → Staff submits evidence
4. Decision: `UPHELD` / `REJECTED` / `PARTIALLY_UPHELD`

## Financial Impact
- Upheld chargeback creates a linked dispute and resolution
- Resolution records client refund amount
- Financial reconciliation tracks chargeback exposure
- No automatic wallet mutations without admin resolution

## Safety
- Only works in DEBUG/dev environments
- No external network calls
- No real funds movement
- All outcomes require explicit staff action
