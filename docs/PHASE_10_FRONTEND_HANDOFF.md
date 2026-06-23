# Phase 10 Frontend Handoff

## Backend Endpoints

### Participant Endpoints
```
GET  /api/disputes/                        — List user's disputes
POST /api/disputes/create/                 — Open a dispute
GET  /api/disputes/{dispute_id}/           — Dispute detail
POST /api/disputes/{dispute_id}/statements/ — Add statement
POST /api/disputes/{dispute_id}/evidence/  — Submit evidence
POST /api/disputes/{dispute_id}/cancel/    — Cancel dispute
GET  /api/disputes/{dispute_id}/refunds/   — List refunds
GET  /api/refunds/{refund_id}/             — Refund detail
GET  /api/contracts/{id}/dispute-eligibility/ — Check eligibility
GET  /api/contracts/{id}/active-dispute/   — Active dispute
```

### Admin Endpoints
```
GET  /api/admin/disputes/                              — Queue
GET  /api/admin/disputes/{id}/                         — Detail
POST /api/admin/disputes/{id}/assign/                  — Assign
POST /api/admin/disputes/{id}/start-review/            — Start review
POST /api/admin/disputes/{id}/start-mediation/         — Mediation
POST /api/admin/disputes/{id}/propose-resolution/       — Propose
POST /api/admin/disputes/{id}/resolve/                  — Resolve
POST /api/admin/disputes/{id}/reject/                   — Reject
POST /api/admin/disputes/{id}/close/                    — Close
GET  /api/admin/disputes/{id}/reconciliation/            — Recon
POST /api/admin/disputes/{id}/refunds/                  — Create refund
POST /api/admin/refunds/{id}/sandbox-confirm/            — Confirm
POST /api/admin/refunds/{id}/retry/                     — Retry
GET  /api/admin/chargebacks/                            — List
POST /api/admin/chargebacks/sandbox-create/             — Create
GET  /api/admin/chargebacks/{id}/                       — Detail
POST /api/admin/chargebacks/{id}/start-review/           — Review
POST /api/admin/chargebacks/{id}/submit-evidence/        — Evidence
POST /api/admin/chargebacks/{id}/sandbox-uphold/         — Uphold
POST /api/admin/chargebacks/{id}/sandbox-reject/         — Reject
POST /api/admin/chargebacks/{id}/sandbox-partial/        — Partial
```

## Domain Modules to Create
```
lib/disputes/types.ts
lib/disputes/schemas.ts
lib/disputes/status.ts
lib/disputes/actions.ts
lib/disputes/mappers.ts
lib/api/disputes.ts

lib/refunds/types.ts
lib/refunds/schemas.ts
lib/refunds/status.ts
lib/refunds/actions.ts
lib/refunds/mappers.ts
lib/api/refunds.ts

lib/chargebacks/types.ts
lib/chargebacks/schemas.ts
lib/chargebacks/status.ts
lib/chargebacks/actions.ts
lib/chargebacks/mappers.ts
lib/api/chargebacks.ts
```

## Key Safety Rules
- Money handled as strings, not floats
- Zod validation for all inputs
- Role-aware action buttons
- No private fields exposed
- Safe evidence metadata only
- Idempotency for all mutations
