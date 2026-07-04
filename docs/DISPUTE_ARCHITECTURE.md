# Dispute Architecture

## Overview
Phase 10 introduces a complete dispute resolution workflow for the Tiqani platform. Disputes allow contract participants to raise issues and have them mediated/resolved by platform staff.

## Models
- `ContractDispute` — Core dispute record
- `DisputeStatement` — Participant statements (opening + response)
- `DisputeEvidence` — Evidence attachments
- `DisputeResolution` — Resolution outcome (appended after admin review)
- `DisputeAuditEvent` — Immutable audit trail
- `RefundRecord` — Financial refund resulting from resolution
- `ChargebackEvent` — Sandbox chargeback event
- `UserFinancialLiability` — Outstanding liability when funds are unrecoverable

## App: `dispute`
Located at `dispute/` with its own models, services, serializers, views, and URLs.

## Key Patterns
- All financial mutations go through `dispute/services.py`
- Idempotency keys prevent duplicate operations
- `select_for_update` prevents race conditions
- Immutable audit events track every state change
