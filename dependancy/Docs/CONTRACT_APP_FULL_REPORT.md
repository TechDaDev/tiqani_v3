# Contract App Full Technical Report

Last updated: 2026-02-26
Code analyzed from: `contract/models.py`, `contract/serializers.py`, `contract/views.py`, `contract/urls.py`, `contract/admin.py`, related migrations.

## Table of Contents
- [1. Executive Summary](#1-executive-summary)
- [2. Scope and Components](#2-scope-and-components)
- [3. Domain Model and Data Design](#3-domain-model-and-data-design)
- [4. API Surface and Access Rules](#4-api-surface-and-access-rules)
- [5. Core Business Workflows](#5-core-business-workflows)
- [6. State Machine and Transition Logic](#6-state-machine-and-transition-logic)
- [7. Payment and Escrow Logic](#7-payment-and-escrow-logic)
- [8. Stage Management Logic](#8-stage-management-logic)
- [9. Time Extension Request Logic](#9-time-extension-request-logic)
- [10. Serializer and Validation Behavior](#10-serializer-and-validation-behavior)
- [11. Admin Behavior](#11-admin-behavior)
- [12. Observed Risks, Gaps, and Inconsistencies](#12-observed-risks-gaps-and-inconsistencies)
- [13. Recommended Improvements (Prioritized)](#13-recommended-improvements-prioritized)
- [14. Frontend Integration Notes](#14-frontend-integration-notes)
- [15. Conclusion](#15-conclusion)

---

## 1. Executive Summary

The `contract` app implements a strong end-to-end contract lifecycle between client and technician, including:
- contract creation and acceptance flow,
- staged milestone payments,
- escrow setup hooks,
- extension request/approval/distribution,
- completion and cancellation actions.

Most critical business rules are centralized in model methods and serializer update logic. The implementation is functional and structured, but there are a few high-impact consistency issues (notably URL converters vs UUID IDs, wallet transaction type alignment risk, and some missing transactional protections).

---

## 2. Scope and Components

### Files and responsibilities
- `contract/models.py`
  - Core entities and business logic
  - State transitions, stage generation, escrow/payment hooks
- `contract/serializers.py`
  - Role-aware input validation and response shaping
- `contract/views.py`
  - API endpoints, permission gating, orchestrating model/serializer actions
- `contract/urls.py`
  - Route exposure under `/api/contract/`
- `contract/admin.py`
  - Admin operations and moderation/override actions

### External dependencies used by this app
- `accounts.ClientProfile`, `accounts.TechnicianProfile`
- `accounts.WalletTransaction`
- `accounts.Wallet`
- Django REST Framework (`APIView`, serializers)

---

## 3. Domain Model and Data Design

## 3.1 Contract

`Contract` is the aggregate root.

### Key fields
- Party fields: `client`, `technician`
- Reference: `contract_reference` (auto-generated)
- Financials: `agreed_amount`, `amount_usd`, `currency`, `escrow_amount`, `total_paid`
- Timeline: `start_date`, `duration_days`, `contract_duration`
- Workflow: `status`, `stage_number`, `client_accepted`, `technician_accepted`
- Soft delete + timestamps from `TimestampedModel`

### Key helper methods
- `generate_contract_reference()`
- `can_be_accepted()`
- `get_incomplete_fields()`
- `_setup_contract_escrow()`
- `_create_contract_stages()`
- `mark_completed()`
- `cancel(reason='')`

## 3.2 ContractStage

Represents contract milestones with per-stage amount and deadline.

### Key fields
- `contract`, `stage_number`, `stage_description`
- `amount`, `deadline`
- `is_approved_by_client`, `completed_at`
- `transaction` (linked wallet transaction)

### Key methods
- `mark_complete()`
- `approve_by_client()` → creates release transaction and increments `contract.total_paid`

## 3.3 TimeExtensionRequest

Represents technician-requested extension to active contracts.

### Key fields
- `contract`, `requested_by`, `requested_days`, `reason`
- `status` (`pending|approved|rejected`)
- `client_response`, `responded_at`

### Key methods
- `clean()` business validation
- `approve(client_response='')`
- `reject(rejection_reason='')`

---

## 4. API Surface and Access Rules

Base path: `/api/contract/`

### Contract endpoints
- `GET /contracts/` → list by user role
- `POST /contracts/` → create (client only)
- `GET /contracts/<uuid:contract_id>/` → detail for contract party
- `PATCH /contracts/<uuid:contract_id>/` → role-aware update/acceptance

### Stage endpoints
- `GET /contracts/<uuid:contract_id>/stages/`
- `GET /stages/<int:stage_id>/`
- `PATCH /stages/<int:stage_id>/`

### Extension request endpoints
- `GET /extension-requests/`
- `POST /extension-requests/` (technician only)
- `POST /extension-requests/<int:request_id>/respond/` (client)
- `POST /extension-requests/<int:request_id>/distribute_days/` (requesting technician)

### Access model summary
- All endpoints require authentication.
- Contract/stage data access restricted to contract parties.
- Create contract: client role only.
- Create extension request and distribute days: technician role only.
- Respond to extension: contract client only.

---

## 5. Core Business Workflows

## 5.1 Contract creation
1. Client submits `technician_id` + `work_description`.
2. Serializer validates technician existence and availability.
3. Contract is created in `draft`.
4. No stages are created yet until required fields are present.

## 5.2 Contract completion and acceptance preparation
Technician updates contract with:
- `agreed_amount`
- `stage_number`
- `start_date`
- `duration_days`
- (optionally `work_description`)

Model `save()` auto-calculates `contract_duration` and may move `draft -> pending_acceptance` when required data exists.

## 5.3 Mutual acceptance and activation
- Technician can mark `technician_accepted`.
- Client can mark `client_accepted` only if:
  - contract status is `pending_acceptance`
  - wallet balance >= `agreed_amount + 10% client platform fee`

When both accepted, model transitions to `in_progress`, executes activation wallet operations, and marks technician unavailable.

Activation wallet operations now include:
- Escrow lock from client: `agreed_amount`.
- Non-refundable client fee: `10%` of `agreed_amount`.
- Non-refundable technician fee: `10%` of `agreed_amount`.
- Both fees are credited to a global platform wallet for financial tracking.

## 5.4 Stage approval and payout
- Client approves each stage via stage PATCH path.
- `approve_by_client()` creates a release wallet transaction to technician and increases `contract.total_paid`.
- When all stages approved, contract is marked `completed`, technician available again.

## 5.5 Extension workflow
1. Technician creates pending extension request (with model validation).
2. Client approves/rejects.
3. If approved, technician distributes additional days across non-approved stages.
4. Deadlines and contract `contract_duration` are updated.

---

## 6. State Machine and Transition Logic

### Status values
- `draft`
- `pending_acceptance`
- `in_progress`
- `completed`
- `canceled`

### Transition triggers
- `draft -> pending_acceptance`:
  - when `agreed_amount`, `stage_number`, `work_description`, `contract_duration` are set.
- `pending_acceptance -> in_progress`:
  - when both acceptance booleans true.
- `in_progress -> completed`:
  - when all stages approved.
- `* -> canceled`:
  - via `cancel()`, except completed/canceled cannot be canceled.

### Important implementation detail
Stage creation runs once requirements are ready (`agreed_amount`, `stage_number`, `start_date`, `duration_days`, `contract_duration`) and no existing stages.

---

## 7. Payment and Escrow Logic

## 7.1 Escrow setup
In `_setup_contract_escrow()`:
- sets `escrow_amount = agreed_amount` if escrow still zero
- deducts from client wallet: `agreed_amount + client_platform_fee`
- deducts from technician wallet: `technician_platform_fee`
- creates wallet transactions:
  - `escrow` (client wallet)
  - `platform_fee` (client wallet, non-refundable)
  - `platform_fee` (technician wallet, non-refundable)
- stores fee amounts on contract:
  - `client_platform_fee`
  - `technician_platform_fee`
- credits global platform wallet aggregates:
  - `balance`
  - `total_fees_collected`
  - `total_client_fees`
  - `total_technician_fees`
- logs each fee ingress in `PlatformWalletTransaction` with:
  - `contract`
  - `source_user`
  - `source_wallet`
  - `source_type` (`client` or `technician`)
  - `amount`
  - `balance_after`

## 7.2 Stage release
In `ContractStage.approve_by_client()`:
- creates wallet transaction on technician wallet with `transaction_type='release'`
- credits technician wallet balance by stage amount
- binds transaction to stage
- increments `contract.total_paid`

## 7.3 Cancellation refund
In `Contract.cancel()`:
- if `escrow_amount > 0`, refunds escrow amount to client wallet and logs `refund` transaction
- platform fees remain non-refundable by design

---

## 8. Stage Management Logic

### Stage generation algorithm
For `stage_number` in 2..5:
- split amount evenly using decimal quantization
- assign amount remainder to last stage
- split duration days evenly using integer division
- assign day remainder to last stage
- compute cumulative deadlines from `start_date`

### Stage update logic
- Only editable in `in_progress` contracts.
- Technician can update only `stage_description` and `deadline`.
- Client action in this endpoint is approval/payment release.

---

## 9. Time Extension Request Logic

### Model validation (`clean()`)
- `requested_days` must be 1 to 30.
- Requester must be assigned technician of contract.
- Contract must be `in_progress`.
- One pending request per technician+contract at a time.

### Approval/rejection
- Only pending requests can be approved or rejected.
- Client response text and responded timestamp are persisted.

### Distribution
- Distribution map values must sum exactly to `requested_days`.
- Cannot extend already approved stages.
- Stage deadlines updated by distributed days.
- Contract deadline updated by total approved requested days.

---

## 10. Serializer and Validation Behavior

## 10.1 ContractCreateSerializer
- validates technician exists and is available
- creates draft contract tied to requesting client

## 10.2 ContractUpdateSerializer
- enforces role-specific writable fields
- enforces `start_date` and `duration_days` together
- blocks updates for completed/canceled contracts
- client acceptance requires `pending_acceptance` status and sufficient wallet
- technician setting amount/stages requires both amount and stage count present in final state

## 10.3 Output serializers
- `ContractListSerializer` for summary list
- `ContractDetailSerializer` includes nested stages and `incomplete_fields` (only while draft)
- basic client/technician serializers intentionally avoid sensitive fields

---

## 11. Admin Behavior

### ContractAdmin
- inline view for stages and extension requests
- actions: mark completed, cancel contracts

### ContractStageAdmin
- visibility into stage completion/approval/payment linkage

### TimeExtensionRequestAdmin
- actions: approve/deny pending requests

Admin exposes strong operational override controls, but bypasses API-level role checks by design (standard admin behavior).

---

## 12. Observed Risks, Gaps, and Inconsistencies

### Status update (work started and applied)
- ✅ Route converter mismatch fixed in URL config (stage/request detail routes now UUID-based).
- ✅ Wallet transaction type mismatch addressed by extending `WalletTransaction.Type` with `escrow`, `release`, and `platform_fee`.
- ✅ Atomic transaction hardening added in activation and stage approval money paths.
- ✅ Platform fee policy implemented: 10% client fee + 10% technician fee on activation, non-refundable.

## High priority

1. **Wallet balance consistency still depends on application-level updates**
- Wallet balances are now updated in contract activation/release/refund flows.
- Remaining risk: no centralized ledger-enforced balance manager exists across the whole platform.

2. **Fee policy operational consideration**
- Activation now requires technician wallet to contain the non-refundable 10% fee.
- This can block activation if technician wallet is underfunded, even when client is ready.
- Product/ops should confirm this is desired UX/business behavior.

## Medium priority

3. **Broad exception handling in several views**
- Multiple `except Exception` blocks return generic 400s.
- Can hide operational defects and make debugging harder.

4. **Unused imports / dead abstractions in views**
- `IsContractParty`, `action`, `ModelViewSet`, and some imports are currently unused.
- Not critical, but increases noise and maintenance overhead.

## Low priority

5. **Contract duration update assumes non-null current value in distribution path**
- `contract.contract_duration += timedelta(...)` assumes contract duration exists.
- Usually true in normal flow, but guard would improve resilience.

6. **No automated tests currently present in `contract/tests.py`**
- Increases regression risk for complex state/payment flows.

---

## 13. Recommended Improvements (Prioritized)

## Immediate (P0)
1. ✅ **Completed**: Route converters changed to UUID where models use UUID.

2. ✅ **Completed**: Wallet transaction types aligned with contract flow.

3. ✅ **Completed**: 10% non-refundable platform fee implemented for both client and technician at contract activation.

## Near-term (P1)
4. ✅ **Completed**: Activation and payout paths wrapped in `transaction.atomic()`.
5. Narrow exception handling to expected exception classes.
6. Add defensive null guards around deadline arithmetic in extension distribution.

## Mid-term (P2)
7. Add contract app test coverage for:
- status transitions,
- wallet balance acceptance gate,
- bilateral platform-fee deductions and non-refund behavior,
- stage payment release,
- extension full cycle,
- permission boundaries.

8. Remove unused imports and unused permission class unless wired.

---

## 14. Frontend Integration Notes

- Treat contract lifecycle as role-aware finite states, not free-form editing.
- Use contract detail payload fields `can_be_accepted` and `incomplete_fields` to drive actionable UI.
- For stage approvals, refresh contract + stages after each approval to detect completion transition.
- For extension distribution UI, enforce sum validation client-side before submit.
- Be prepared for backend-side validation messages in `detail` and show them directly.
- Activation now includes non-refundable platform fees for both parties:
  - client charged `agreed_amount + 10% fee`
  - technician charged `10% fee`
  - show these as explicit agreement-time charges in confirmation UI.
- Finance/admin dashboards can now consume global platform wallet totals plus per-entry platform fee transactions for auditability.

---

## 15. Conclusion

The contract app has a well-structured core domain model and a coherent workflow for staged contracts, acceptance, payout, and extension handling. The architecture is strong for production use, but it needs a small set of targeted fixes (ID routing alignment, wallet transaction type alignment, and transactional integrity hardening) to reduce failure risk in financial/stateful paths.
