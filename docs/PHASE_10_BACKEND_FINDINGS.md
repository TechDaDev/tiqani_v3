# Phase 10 Backend Findings

## 1. Existing Financial & Contract State

### Wallet Model (`wallet/models.py`)
- `Wallet` — per-user balance, constrained to non-negative via `MinValueValidator(0.00)`
- `WalletTransaction.Type` — includes `REFUND`, `ESCROW`, `RELEASE`, `PLATFORM_FEE`, `DEPOSIT`, `WITHDRAWAL`, `PAYMENT`
- `PlatformWallet` — global singleton via `GLOBAL_KEY`, non-negative constraint
- `PlatformWalletTransaction` — tracks fee movements
- `PlatformEarning` — per-contract earning records with statuses `PENDING`, `EARNED`, `REVERSED`
- `ContractSettlement` — immutable settlement record with status `REVERSED` defined but never used
- `WithdrawalRequest` — technician/admin withdrawal pipeline

### Contract Model (`contract/models.py`)
- `Contract.escrow_amount` — escrowed funds, reduced to 0 on settlement
- `Contract.total_paid` — cumulative technician payments
- `Contract.client_platform_fee` / `technician_platform_fee` — non-refundable activation fees
- `Contract.cancel()` — existing cancellation refunds escrow to client wallet

### Existing Audit
- `ContractAuditEvent` — append-only event stream with `event_type`, `actor`, `payload`
- Covers `ESCROW_RELEASED` and other events

## 2. Dispute Gaps
- **No dispute models exist.** Only `dispute_clause_version` in contract document template.
- No dispute state machine.
- No dispute eligibility logic.
- No evidence model.
- No mediation model.

## 3. Refund Gaps
- `WalletTransaction.Type.REFUND` exists but is only used by `Contract.cancel()`.
- No `RefundRecord` model.
- No refund service beyond escrow return on cancel.
- No post-settlement reversal service.
- No platform fee reversal service.
- No idempotent refund mechanism.

## 4. Chargeback Gaps
- No chargeback model or service.
- Sandbox gateway exists (`wallet/sandbox_gateway.py`) but only covers payment confirmation, not chargebacks.
- No chargeback state machine.

## 5. Settlement-Reversal Risks
- `ContractSettlement.Status.REVERSED` is defined but never used by any code.
- No service mutates settlement to reversed.
- No compensating ledger entries exist for reversals.
- Original settlement records are immutable — reversal must create compensating entries.

## 6. Recoverable vs Non-Recoverable Funds

### Pre-Settlement (Recoverable from escrow)
- Escrow still held on contract.
- Technician wallet not yet credited.
- Refund returns escrow to client.

### Post-Settlement Recoverable
- Settlement completed, technician wallet credited.
- If technician has sufficient unwithdrawn balance, reversal can recover.

### Post-Settlement Non-Recoverable
- Funds withdrawn from technician wallet.
- No way to recover from external payment provider.
- Must record outstanding liability.

### Platform Fees
- Client fee and technician commission are non-refundable by policy.
- Phase 10 will allow proportional reversal only for approved refunds.
- Original `PlatformEarning` records preserved; status changed to `REVERSED`.

## 7. Wallet & Platform-Wallet Implications
- Wallet balance has `MinValueValidator(0.00)` — cannot go negative.
- Platform wallet also constrained to non-negative.
- Withdrawal processing reduces wallet balance.
- Paid withdrawals make funds non-recoverable from platform.

## 8. Current Audit Capabilities
- `ContractAuditEvent` works for contract-level events.
- `Notification` and `ActivityLog` exist for user-facing and admin events.
- No dispute-specific audit model.

## 9. Proposed Models

New app: `dispute`

### `ContractDispute`
- UUID PK
- contract FK
- opened_by FK (User)
- respondent FK (User)
- reason (choice code)
- category (PRE_SETTLEMENT / POST_SETTLEMENT_RECOVERABLE / etc.)
- claimed_amount Decimal
- currency (default IQD)
- status (state machine)
- assigned_staff FK (User, nullable)
- opened_at, response_due_at, review_started_at, resolved_at, closed_at
- idempotency_key (unique, nullable)
- resolution_summary TextField
- created_at, updated_at

### `DisputeStatement`
- UUID PK
- dispute FK
- submitted_by FK (User)
- statement TextField
- created_at

### `DisputeEvidence`
- UUID PK
- dispute FK
- submitted_by FK (User)
- evidence_type (choice)
- description TextField
- file (safe attachment)
- mime_type, file_size
- integrity_hash
- created_at (immutable)

### `DisputeResolution`
- UUID PK
- dispute FK (OneToOne)
- resolved_by FK (User)
- resolution_type (choice code)
- client_refund_amount Decimal
- technician_retained_amount Decimal
- platform_fee_reversal_amount Decimal
- escrow_released_amount Decimal
- wallet_reversal_amount Decimal
- unrecoverable_amount Decimal
- outstanding_liability_amount Decimal
- resolution_reason TextField
- resolved_at
- created_at

### `DisputeAuditEvent`
- UUID PK
- dispute FK
- event_type (choice code)
- actor FK (User)
- payload JSON
- created_at

### `RefundRecord`
- UUID PK
- dispute FK
- contract FK
- client FK (User)
- amount Decimal
- currency
- source_type (ESCROW / TECHNICIAN_WALLET_REVERSAL / PLATFORM_FEE_REVERSAL / SPLIT_SOURCES / MANUAL_RECOVERY / SANDBOX_PROVIDER)
- status (PENDING / PROCESSING / COMPLETED / FAILED / CANCELED / PARTIALLY_COMPLETED)
- refund_method
- provider_reference
- wallet_transaction FK
- platform_transaction FK
- created_by FK
- initiated_at, completed_at, failed_at
- failure_code, failure_message
- idempotency_key (unique, nullable)

### `ChargebackEvent`
- UUID PK
- contract FK
- dispute FK (nullable)
- provider_reference
- amount Decimal
- reason_code
- received_at
- evidence_deadline
- status (RECEIVED / UNDER_REVIEW / EVIDENCE_SUBMITTED / UPHELD / REJECTED / PARTIALLY_UPHELD / CLOSED)
- outcome
- resolved_by FK (nullable)
- resolved_at
- idempotency_key (unique, nullable)

### `UserFinancialLiability`
- UUID PK
- user FK
- source_dispute FK
- original_amount Decimal
- recovered_amount Decimal
- remaining_amount Decimal
- status (OPEN / PARTIALLY_RECOVERED / FULLY_RECOVERED / WRITTEN_OFF)
- created_at, updated_at

## 10. Proposed State Machine

### Dispute Status Transitions
```
OPEN → AWAITING_RESPONSE
AWAITING_RESPONSE → UNDER_REVIEW
OPEN → UNDER_REVIEW
UNDER_REVIEW → MEDIATION
MEDIATION → RESOLUTION_PROPOSED
UNDER_REVIEW → RESOLUTION_PROPOSED
RESOLUTION_PROPOSED → RESOLVED
RESOLVED → CLOSED
OPEN → CANCELED
AWAITING_RESPONSE → CANCELED
UNDER_REVIEW → REJECTED
REJECTED → CLOSED
```

## 11. Proposed Endpoint Map

### Participant Endpoints
```
GET  /api/disputes/
POST /api/disputes/
GET  /api/disputes/{dispute_id}/
POST /api/disputes/{dispute_id}/statements/
POST /api/disputes/{dispute_id}/evidence/
POST /api/disputes/{dispute_id}/cancel/
GET  /api/contracts/{contract_id}/dispute-eligibility/
GET  /api/contracts/{contract_id}/active-dispute/
```

### Staff Endpoints
```
GET  /api/admin/disputes/
GET  /api/admin/disputes/{dispute_id}/
POST /api/admin/disputes/{dispute_id}/assign/
POST /api/admin/disputes/{dispute_id}/start-review/
POST /api/admin/disputes/{dispute_id}/start-mediation/
POST /api/admin/disputes/{dispute_id}/propose-resolution/
POST /api/admin/disputes/{dispute_id}/resolve/
POST /api/admin/disputes/{dispute_id}/reject/
POST /api/admin/disputes/{dispute_id}/close/
GET  /api/admin/disputes/{dispute_id}/reconciliation/
```

### Refund Endpoints
```
GET  /api/disputes/{dispute_id}/refunds/
POST /api/admin/disputes/{dispute_id}/refunds/
GET  /api/refunds/{refund_id}/
POST /api/admin/refunds/{refund_id}/sandbox-confirm/
POST /api/admin/refunds/{refund_id}/retry/
```

### Chargeback Endpoints
```
GET  /api/admin/chargebacks/
POST /api/admin/chargebacks/sandbox-create/
GET  /api/admin/chargebacks/{chargeback_id}/
POST /api/admin/chargebacks/{chargeback_id}/start-review/
POST /api/admin/chargebacks/{chargeback_id}/submit-evidence/
POST /api/admin/chargebacks/{chargeback_id}/sandbox-uphold/
POST /api/admin/chargebacks/{chargeback_id}/sandbox-reject/
POST /api/admin/chargebacks/{chargeback_id}/sandbox-partial/
```

## 12. Security Risks
- Participant must not assign staff, resolve disputes, or issue refunds.
- Claimed amount must be backend-derived maximum (contract amount).
- Refund amount must be backend-validated against escrow or recoverable amount.
- Evidence MIME type, size, and extension must be validated.
- No wallet ID spoofing.
- No duplicate refund via idempotency keys.
- No negative wallet balance.
- No secret/token exposure in responses.

## 13. Concurrency Risks
- Two simultaneous dispute-open requests must produce one dispute.
- Refund and settlement must not race.
- Refund and withdrawal must not overdraw wallet.
- Platform fee reversal must not duplicate.
- All mutating services use `transaction.atomic` + `select_for_update`.

## 14. Migration Ownership
New `dispute` app with its own migrations.
No changes to existing `wallet` or `contract` migrations.
New `RefundRecord` and `ChargebackEvent` in `dispute` app referencing `wallet` models.

## 15. Phase 10 Scope and Deferrals

### In Scope
- Dispute opening, reasons, statements, evidence, mediation, admin review
- Pre-settlement refund from escrow
- Post-settlement ledger reversal (when recoverable)
- Partial recovery with liability
- Platform fee proportional reversal
- Sandbox chargeback events
- Financial reconciliation after resolution
- Notifications for all dispute events
- Immutable audit history

### Deferred
- Real card chargebacks
- Production bank reversals
- External payment-provider webhooks
- Court enforcement
- Tax adjustments
- Legal document generation
- Insurance claims
- Ratings and reviews
- Automated AI judgment
- Automatic permanent account suspension
