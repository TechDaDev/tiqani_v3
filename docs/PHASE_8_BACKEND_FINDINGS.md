# Phase 8 Backend Findings

## Current Contract Model (`contract/models.py`)

### Contract Statuses
- `draft` → `pending_acceptance` → `pending_signatures` → `pending_finalization` → `in_progress` → `completed` → `canceled`
- No `active` or `completion_requested` status exists.
- `in_progress` is overloaded (used for both "active execution" and "funded+active").
- `mark_completed()` sets status to `completed` and releases technician availability.

### Existing ContractStage (Payment Stages)
- Already exists: `ContractStage` with `stage_number`, `amount`, `deadline`, `is_approved_by_client`, `completed_at`, `transaction`.
- **`approve_by_client()` RELEASES PAYMENT** — creates WalletTransaction with Type.RELEASE, credits technician wallet. This is Phase 9+ behavior.
- Must NOT use `ContractStage` for Phase 8 execution milestones. Create separate model.

### Funding State
- No `FundingStatus` model. Funding state derived from `wallet/services.py` → `get_contract_funding_status()`.
- Funding statuses: `UNFUNDED`, `PENDING`, `FUNDED`, `FAILED`.
- `_setup_contract_escrow()` creates escrow WalletTransaction.

### Existing Models
| Model | Purpose | Phase 8 Use |
|---|---|---|
| `Contract` | Work agreement | Extend statuses |
| `ContractStage` | Payment stages (releases money) | Do NOT use |
| `ContractVersion` | Immutable snapshots | Reuse for execution snapshots |
| `ContractAuditEvent` | Append-only audit trail | Reuse (rename events) |
| `ContractDocument` | File attachments (PDF only) | Extend for deliverables |
| `TimeExtensionRequest` | Deadline extension | Independent |

### What's Missing (Phase 8 Scope)
1. **ExecutionMilestone** — work-tracking milestones (no payment release)
2. **DeliverableSubmission** — technician deliverables
3. **RevisionRequest** — client revision requests
4. **ExecutionHistory** — event log (can use existing ContractAuditEvent)
5. Contract statuses: `active`, `completion_requested`
6. Completion request/confirm/reject flow
7. File attachment support for deliverables

### Permissions
Existing: role checks in views (`is_client`, `is_technician`). No execution-specific permissions.

### Endpoints
Existing contract endpoints cover CRUD, stages, extensions, signatures. No execution endpoints.

### Tests
Existing: `contract/tests/` — coverage for contract CRUD, stages, offers. No execution tests.

### OpenAPI
Regenerated via `drf-spectacular`. Will update after implementation.
