# Contract App Documentation

Last updated: 2026-02-26

This document reflects the current implementation in `contract/` and mounted routes in `tiqani_v3/urls.py`.

## Table of Contents

- [Base Route](#base-route)
- [Access Model](#access-model)
- [Features](#features)
- [Endpoints](#endpoints)
- [Contract Status Lifecycle](#contract-status-lifecycle)
- [Stage Auto-Creation](#stage-auto-creation)
- [Key Model Fields](#key-model-fields)
- [Implementation Notes](#implementation-notes)
- [Frontend Notes](#frontend-notes)
- [Frontend Implementation Guideline](#frontend-implementation-guideline)
- [Known Route/Schema Caveat (Current Code)](#known-routeschema-caveat-current-code)

## Base Route

All contract endpoints are mounted under:

- `/api/contract/`

---

## Access Model

- All contract endpoints require authentication.
- Contract access is limited to parties on that contract (client or assigned technician).
- Contract records use soft-delete flag `is_delete`; list/detail views exclude soft-deleted contracts.

---

## Features

- Role-based contract creation and updates (client/technician)
- Multi-stage contract workflow with automatic stage generation
- Escrow and staged release payment flow hooks
- Time-extension request lifecycle (request/respond/distribute)
- Contract completion and technician availability toggling
- Soft-delete-safe contract querying

---

## Endpoints

### 1) Contracts List / Create

- `GET /api/contract/contracts/`
- `POST /api/contract/contracts/`

#### `GET /contracts/`
Returns contracts for current user role:
- client: contracts where user is `contract.client`
- technician: contracts where user is `contract.technician`

#### `POST /contracts/` (client only)
Creates draft contract.

**Request body**
```json
{
  "technician_id": "uuid",
  "work_description": "string"
}
```

**Behavior**
- Technician must exist and be available.
- Contract is created with:
  - `status = "draft"`
  - no amount/stage/timeline yet

---

### 2) Contract Detail / Update

- `GET /api/contract/contracts/<uuid:contract_id>/`
- `PATCH /api/contract/contracts/<uuid:contract_id>/`

#### `GET`
Returns full contract details including nested `stages`, `can_be_accepted`, and `incomplete_fields`.

#### `PATCH`
Role-based update logic:

- **Technician** can set/adjust contract details and their own acceptance:
  - editable: `work_description`, `agreed_amount`, `stage_number`, `start_date`, `duration_days`, `technician_accepted`
  - `start_date` and `duration_days` must be provided together
  - if either `agreed_amount` or `stage_number` is provided, both must be available in final state

- **Client** can only set:
  - `client_accepted: true`
  - if client accepts, contract must be in `pending_acceptance` and wallet balance must cover `agreed_amount`

**Common validation errors**
- cannot modify `completed` or `canceled` contracts
- insufficient wallet balance on client acceptance
- incomplete acceptance prerequisites

---

### 3) Contract Stages List

- `GET /api/contract/contracts/<uuid:contract_id>/stages/`

Returns all stages for contract ordered by `stage_number`.

---

### 4) Contract Stage Detail / Update

- `GET /api/contract/stages/<int:stage_id>/`
- `PATCH /api/contract/stages/<int:stage_id>/`

#### `PATCH` behavior
Only valid while contract status is `in_progress`.

- **Technician**:
  - can update `stage_description` and `deadline`
- **Client**:
  - approves stage completion (payment release)
  - if all stages become approved, contract is auto-marked `completed`

**Response on client approval**
```json
{
  "detail": "Stage approved and payment released."
}
```

---

### 5) Time Extension Requests List / Create

- `GET /api/contract/extension-requests/`
- `POST /api/contract/extension-requests/`

#### `GET`
- Technician sees own sent requests.
- Client sees requests attached to their contracts.

#### `POST` (technician only)
Creates extension request for assigned contract.

**Request body**
```json
{
  "contract": "uuid",
  "requested_days": 1,
  "reason": "string"
}
```

Model-level rules (`full_clean`):
- `requested_days` must be 1..30
- contract must be `in_progress`
- requester must be assigned technician for that contract
- only one pending request per technician+contract pair

---

### 6) Extension Request Respond

- `POST /api/contract/extension-requests/<int:request_id>/respond/`

Client approves/rejects pending request.

**Request body**
```json
{
  "approve": true,
  "client_response": "optional comment"
}
```

Rules:
- only contract client can respond
- only pending requests can be processed

---

### 7) Distribute Approved Extension Days

- `POST /api/contract/extension-requests/<int:request_id>/distribute_days/`

Technician distributes approved days across unapproved stages.

**Request body**
```json
{
  "distribution": {
    "<stage_id>": 2,
    "<stage_id>": 1
  }
}
```

Rules:
- requester must be the same technician who created extension request
- extension request must be `approved`
- sum of distributed days must equal `requested_days`
- cannot distribute to already approved stages
- updates stage deadlines and contract `contract_duration`

---

## Contract Status Lifecycle

`draft` → `pending_acceptance` → `in_progress` → `completed`

Additional terminal status: `canceled`

### Auto transitions in model

- `draft` → `pending_acceptance`
  - when all required fields exist:
    - `agreed_amount`
    - `stage_number`
    - `work_description`
    - `contract_duration`

- `pending_acceptance` → `in_progress`
  - when both `client_accepted` and `technician_accepted` are true
  - escrow setup is attempted

- `in_progress` → `completed`
  - when all stages are approved by client

---

## Stage Auto-Creation

Contract model auto-creates stages when all are present and no stages exist yet:
- `agreed_amount`
- `stage_number`
- `start_date`
- `duration_days`
- `contract_duration`

Distribution logic:
- amount split evenly; remainder assigned to last stage
- duration split evenly; remainder days assigned to last stage
- deadlines are cumulative from `start_date`

---

## Key Model Fields

### Contract
- parties: `client`, `technician`
- reference: `contract_reference`
- financial: `agreed_amount`, `amount_usd`, `currency`, `escrow_amount`, `total_paid`
- timeline: `start_date`, `duration_days`, `contract_duration`
- workflow: `status`, `stage_number`, `client_accepted`, `technician_accepted`

### ContractStage
- `contract`, `stage_number`, `stage_description`, `amount`, `deadline`
- approval/payment: `is_approved_by_client`, `completed_at`, `transaction`

### TimeExtensionRequest
- `contract`, `requested_by`, `requested_days`, `reason`
- response fields: `status`, `client_response`, `responded_at`

---

## Implementation Notes

- Contract list/detail serializers expose basic profile info only for contract parties (`user_id`, `username`, `full_name`, `profile_image`, and technician `job_title`).
- Stage approval triggers payment release transaction and updates contract `total_paid`.
- `Contract.cancel()` supports escrow refund transaction and sets technician available again.

---

## Frontend Notes

- Treat contract update UI as role-aware: technician completes details, client confirms acceptance.
- Surface `can_be_accepted` and `incomplete_fields` to guide users before acceptance.
- Do not expose stage edit controls unless contract status is `in_progress`.
- For extension requests, keep separate queues for technician-submitted and client-actionable items.
- Expect backend validation errors for wallet insufficiency and invalid status transitions.

---

## Frontend Implementation Guideline

- Implement contract screens in lifecycle order: draft → pending acceptance → in progress → completed/canceled.
- Keep acceptance actions explicit and separate (`client_accepted` vs `technician_accepted`).
- Build stage timelines from `/contracts/<id>/stages/` and refresh after each approval.
- Validate extension-day distribution totals in UI before submission to reduce round trips.
- Standardize error handling for `400/403/404` and display backend `detail` messages directly.
- Centralize endpoint URL builders so path converter changes (int vs UUID) can be fixed in one place.

---

## Known Route/Schema Caveat (Current Code)

Current stage and extension detail routes use `int` path converters:
- `/stages/<int:stage_id>/`
- `/extension-requests/<int:request_id>/...`

But `ContractStage` and `TimeExtensionRequest` currently use UUID primary keys in models/migrations. If IDs are UUIDs in DB, these int-based routes will not target those records correctly until route converters are aligned.
