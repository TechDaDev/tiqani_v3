# Contract Management API Documentation

**Last Updated:** January 1, 2026

This document outlines all contract-related API endpoints, request/response formats, business logic, payment workflows, and penalty system for the `contract` app.

---

## Table of Contents

1. [Contracts](#contracts)
2. [Contract Stages](#contract-stages)
3. [Time Extension Requests](#time-extension-requests)
4. [Contract Workflow](#contract-workflow)
5. [Payment System](#payment-system)
6. [Penalties & Fee System](#penalties--fee-system)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Contracts

### List Contracts

**Endpoint**
```
GET /api/contract/contracts/
```

**Authentication:** Required

**Description:** Get all contracts for the authenticated user. Clients see their contracts; technicians see their assigned contracts.

**Success Response (200 OK)**

For Clients:
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "contract_reference": "#A1B2C3D4E5F6",
        "client": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "jane_doe",
            "full_name": "Jane Doe",
            "profile_image": "http://localhost:8000/media/Profile/xyz.jpg"
        },
        "technician": {
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "username": "john_tech",
            "full_name": "John Smith",
            "profile_image": "http://localhost:8000/media/Profile/abc.jpg",
            "job_title": "Senior Web Developer"
        },
        "work_description": "Build a responsive e-commerce website...",
        "agreed_amount": "2000000.00",
        "amount_usd": "1370.00",
        "currency": "IQD",
        "escrow_amount": "2000000.00",
        "total_paid": "500000.00",
        "start_date": "2026-02-01",
        "duration_days": 27,
        "contract_duration": "2026-02-28",
        "stage_number": 4,
        "status": "in_progress",
        "client_accepted": true,
        "technician_accepted": true,
        "created_at": "2026-01-01T10:30:00Z",
        "updated_at": "2026-01-15T14:22:00Z",
        "can_be_accepted": false
    }
]
```

**Field Descriptions:**
- `contract_reference` (string): Auto-generated unique reference (e.g., `#A1B2C3D4E5F6`)
- `agreed_amount` (decimal): Total agreed amount in IQD (Iraqi Dinar)
- `amount_usd` (decimal): USD equivalent for reference only
- `currency` (string): Always "IQD" for this system
- `escrow_amount` (decimal): Amount held in escrow (equal to agreed_amount when activated)
- `total_paid` (decimal): Total amount paid to technician so far
- `start_date` (date): Project start date set by technician
- `duration_days` (integer): Duration of project in days set by technician
- `contract_duration` (date): Calculated deadline (start_date + duration_days)
- `can_be_accepted` (boolean): Whether all required fields are filled for acceptance
- `status` (enum): One of `draft`, `pending_acceptance`, `in_progress`, `completed`, `canceled`

---

### Create Contract

**Endpoint**
```
POST /api/contract/contracts/
```

**Authentication:** Required (client only)

**Description:** Initiate a new contract between client and technician.

**Request Body**
```json
{
    "technician_id": "uuid",
    "work_description": "string (required, max 2000 chars)"
}
```

**Success Response (201 Created)**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "contract_reference": "#A1B2C3D4E5F6",
    "client": {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "jane_doe",
        "full_name": "Jane Doe",
        "profile_image": "http://localhost:8000/media/Profile/xyz.jpg"
    },
    "technician": {
        "user_id": "660e8400-e29b-41d4-a716-446655440001",
        "username": "john_tech",
        "full_name": "John Smith",
        "profile_image": "http://localhost:8000/media/Profile/abc.jpg",
        "job_title": "Senior Web Developer"
    },
    "work_description": "Build a responsive e-commerce website...",
    "agreed_amount": null,
    "amount_usd": null,
    "currency": "IQD",
    "escrow_amount": "0.00",
    "total_paid": "0.00",
    "start_date": null,
    "duration_days": null,
    "contract_duration": null,
    "stage_number": null,
    "status": "draft",
    "client_accepted": false,
    "technician_accepted": false,
    "stages": [],
    "created_at": "2026-01-01T10:30:00Z",
    "updated_at": "2026-01-01T10:30:00Z",
    "can_be_accepted": false,
    "incomplete_fields": [
        "Agreed Amount",
        "Stage Number"
    ]
}
```

**Error Responses**

400 Bad Request:
```json
{
    "detail": "Technician does not exist.",
    "technician_id": ["Technician does not exist."]
}
```

400 Bad Request:
```json
{
    "detail": "Technician is not available for new contracts."
}
```

403 Forbidden:
```json
{
    "detail": "Only clients can create contracts."
}
```

**Notes:**
- Contract is created in `draft` status
- Technician must be available (`is_available=true`)
- Awaiting technician to complete contract details (amount, stages)
- Technician sets `start_date` and `duration_days`; the system computes `contract_duration` (deadline)

---

### Get Contract Detail

**Endpoint**
```
GET /api/contract/contracts/<uuid:contract_id>/
```

**Authentication:** Required

**Description:** Get complete details of a specific contract including nested stages.

**Success Response (200 OK)**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "contract_reference": "#A1B2C3D4E5F6",
    "client": {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "jane_doe",
        "full_name": "Jane Doe",
        "profile_image": "http://localhost:8000/media/Profile/xyz.jpg"
    },
    "technician": {
        "user_id": "660e8400-e29b-41d4-a716-446655440001",
        "username": "john_tech",
        "full_name": "John Smith",
        "profile_image": "http://localhost:8000/media/Profile/abc.jpg",
        "job_title": "Senior Web Developer"
    },
    "work_description": "Build a responsive e-commerce website with shopping cart, payment integration...",
    "agreed_amount": "2000000.00",
    "amount_usd": "1370.00",
    "currency": "IQD",
    "escrow_amount": "2000000.00",
    "total_paid": "500000.00",
    "start_date": "2026-02-01",
    "duration_days": 27,
    "contract_duration": "2026-02-28",
    "stage_number": 4,
    "status": "in_progress",
    "client_accepted": true,
    "technician_accepted": true,
    "stages": [
        {
            "id": 1,
            "contract": "550e8400-e29b-41d4-a716-446655440000",
            "contract_reference": "#A1B2C3D4E5F6",
            "stage_number": 1,
            "stage_description": "Setup and design database schema...",
            "amount": "500000.00",
            "deadline": "2026-01-28",
            "is_approved_by_client": true,
            "completed_at": "2026-01-25T15:30:00Z",
            "created_at": "2026-01-01T10:30:00Z",
            "updated_at": "2026-01-25T15:30:00Z"
        },
        {
            "id": 2,
            "contract": "550e8400-e29b-41d4-a716-446655440000",
            "contract_reference": "#A1B2C3D4E5F6",
            "stage_number": 2,
            "stage_description": "Develop API endpoints...",
            "amount": "500000.00",
            "deadline": "2026-02-10",
            "is_approved_by_client": false,
            "completed_at": null,
            "created_at": "2026-01-01T10:30:00Z",
            "updated_at": "2026-01-01T10:30:00Z"
        }
    ],
    "created_at": "2026-01-01T10:30:00Z",
    "updated_at": "2026-01-20T09:15:00Z",
    "can_be_accepted": false,
    "incomplete_fields": []
}
```

**Error Responses**

403 Forbidden:
```json
{
    "detail": "You do not have permission to access this contract."
}
```

---

### Update Contract

**Endpoint**
```
PATCH /api/contract/contracts/<uuid:contract_id>/
```

**Authentication:** Required

**Description:** Update contract based on user role. Technicians complete contract details; clients/technicians accept.

**Request Body - Technician Completing Contract**
```json
{
    "work_description": "Detailed description of work...",
    "agreed_amount": 2000000,
    "stage_number": 4,
    "start_date": "2026-02-01",
    "duration_days": 27
}
```

**Request Body - Client Accepting**
```json
{
    "client_accepted": true
}
```

**Request Body - Technician Accepting**
```json
{
    "technician_accepted": true
}
```

**Success Response (200 OK)**
Same as Get Contract Detail response.

**Stage Generation Rules**
- Once `agreed_amount`, `stage_number`, `start_date`, and `duration_days` are set, stages are auto-created even while the contract is still in `draft` or `pending_acceptance` so both parties can view timelines and amounts early.
- Amounts are split evenly across stages; any fractional remainder is added to the last stage.
- Duration is split evenly across stages; any leftover days are added to the last stage. Each stage deadline is cumulative from the `start_date`.

**Error Responses**

400 Bad Request - Completed Contract:
```json
{
    "detail": "Cannot modify a completed contract."
}
```

400 Bad Request - Missing Required Fields:
```json
{
    "detail": "Both agreed amount and stage number are required."
}
```

400 Bad Request - Insufficient Wallet Balance:
```json
{
    "detail": "Insufficient funds in wallet. You have 500000 IQD but need 2000000 IQD to initiate this contract. Please recharge your wallet with at least 1500000 IQD more."
}
```

400 Bad Request - Invalid Stage Number:
```json
{
    "detail": {
        "stage_number": ["Stage number must be between 2 and 5."]
    }
}
```

403 Forbidden:
```json
{
    "detail": "You do not have permission to update this contract."
}
```

**Business Logic:**

**Technician Completing Contract:**
- Sets `agreed_amount`, `stage_number`, `work_description`, and `contract_duration`
- Automatically transitions status from `draft` → `pending_acceptance`
- Then technician sets `technician_accepted: true`

**Client Accepting Contract:**
- Sets `client_accepted: true`
- System verifies wallet has sufficient balance
- If balance < `agreed_amount`, returns error with shortfall amount
- When both parties accept, contract transitions `pending_acceptance` → `in_progress`:
  - Escrow is setup (creates wallet transaction)
  - Contract stages are automatically created and divided equally
  - Technician becomes unavailable (`is_available=false`)

**Currency Handling:**
- All amounts specified in IQD (Iraqi Dinar)
- USD equivalent calculated at contract creation using current exchange rate
- Exchange rate is recorded and locked for the contract lifetime

---

## Contract Stages

### List Contract Stages

**Endpoint**
```
GET /api/contract/contracts/<uuid:contract_id>/stages/
```

**Authentication:** Required

**Description:** Get all stages for a specific contract.

**Success Response (200 OK)**
```json
[
    {
        "id": 1,
        "contract": "550e8400-e29b-41d4-a716-446655440000",
        "contract_reference": "#A1B2C3D4E5F6",
        "stage_number": 1,
        "stage_description": "Setup and design database schema...",
        "amount": "500000.00",
        "deadline": "2026-01-28",
        "is_approved_by_client": true,
        "completed_at": "2026-01-25T15:30:00Z",
        "created_at": "2026-01-01T10:30:00Z",
        "updated_at": "2026-01-25T15:30:00Z"
    },
    {
        "id": 2,
        "contract": "550e8400-e29b-41d4-a716-446655440000",
        "contract_reference": "#A1B2C3D4E5F6",
        "stage_number": 2,
        "stage_description": "Develop API endpoints...",
        "amount": "500000.00",
        "deadline": "2026-02-10",
        "is_approved_by_client": false,
        "completed_at": null,
        "created_at": "2026-01-01T10:30:00Z",
        "updated_at": "2026-01-01T10:30:00Z"
    }
]
```

---

### Get Stage Detail

**Endpoint**
```
GET /api/contract/stages/<int:stage_id>/
```

**Authentication:** Required

**Description:** Get detailed information for a specific stage.

**Success Response (200 OK)**
```json
{
    "id": 1,
    "contract": "550e8400-e29b-41d4-a716-446655440000",
    "contract_reference": "#A1B2C3D4E5F6",
    "stage_number": 1,
    "stage_description": "Setup and design database schema...",
    "amount": "500000.00",
    "deadline": "2026-01-28",
    "is_approved_by_client": true,
    "completed_at": "2026-01-25T15:30:00Z",
    "created_at": "2026-01-01T10:30:00Z",
    "updated_at": "2026-01-25T15:30:00Z"
}
```

---

### Update Stage

**Endpoint**
```
PATCH /api/contract/stages/<int:stage_id>/
```

**Authentication:** Required

**Description:** Update stage details (technician) or approve stage (client).

**Request Body - Technician Updates Description/Deadline**
```json
{
    "stage_description": "Updated description of work...",
    "deadline": "2026-01-31"
}
```

**Request Body - Client Approves Stage**
```json
{}
```
(Empty body; approval is determined by user role)

**Success Response (200 OK)**

Technician Update:
```json
{
    "id": 1,
    "contract": "550e8400-e29b-41d4-a716-446655440000",
    "contract_reference": "#A1B2C3D4E5F6",
    "stage_number": 1,
    "stage_description": "Updated description...",
    "amount": "500000.00",
    "deadline": "2026-01-31",
    "is_approved_by_client": false,
    "completed_at": null,
    "created_at": "2026-01-01T10:30:00Z",
    "updated_at": "2026-01-20T10:15:00Z"
}
```

Client Approval:
```json
{
    "detail": "Stage approved and payment released."
}
```

**Error Responses**

400 Bad Request - Not In Progress:
```json
{
    "detail": "Cannot modify stages unless the contract is in progress."
}
```

400 Bad Request - Already Approved:
```json
{
    "detail": "This stage has already been approved."
}
```

403 Forbidden:
```json
{
    "detail": "You do not have permission to update this stage."
}
```

**Business Logic:**

**Payment Release on Stage Approval:**
1. Client approves completed stage
2. System deducts platform fee (default 10%)
3. Remaining amount transferred to technician's wallet
4. `total_paid` increases by stage amount
5. If all stages approved → contract marked as `completed`, technician becomes available

**Example Payment Breakdown:**
```
Stage amount: 500,000 IQD
Platform fee (10%): 50,000 IQD
Technician receives: 450,000 IQD
```

---

## Time Extension Requests

### List Extension Requests

**Endpoint**
```
GET /api/contract/extension-requests/
```

**Authentication:** Required

**Description:** Get all extension requests (technicians see sent requests, clients see requests for their contracts).

**Success Response (200 OK)**
```json
[
    {
        "id": 1,
        "contract": "550e8400-e29b-41d4-a716-446655440000",
        "contract_reference": "#A1B2C3D4E5F6",
        "requested_days": 7,
        "reason": "Unexpected client delay in providing design assets...",
        "status": "pending",
        "requested_by": "660e8400-e29b-41d4-a716-446655440001",
        "requested_by_name": "John Smith",
        "client_response": null,
        "created_at": "2026-01-20T10:30:00Z",
        "updated_at": "2026-01-20T10:30:00Z",
        "responded_at": null
    },
    {
        "id": 2,
        "contract": "550e8400-e29b-41d4-a716-446655440000",
        "contract_reference": "#A1B2C3D4E5F6",
        "requested_days": 5,
        "reason": "Critical bug found in deployment environment...",
        "status": "approved",
        "requested_by": "660e8400-e29b-41d4-a716-446655440001",
        "requested_by_name": "John Smith",
        "client_response": "Okay, but no more extensions after this.",
        "created_at": "2026-01-15T14:15:00Z",
        "updated_at": "2026-01-16T09:45:00Z",
        "responded_at": "2026-01-16T09:45:00Z"
    }
]
```

---

### Create Extension Request

**Endpoint**
```
POST /api/contract/extension-requests/
```

**Authentication:** Required (technician only)

**Description:** Request additional time to complete contract stages.

**Request Body**
```json
{
    "contract": "uuid",
    "requested_days": 7,
    "reason": "Unexpected delays in receiving client assets and additional requirements emerged..."
}
```

**Success Response (201 Created)**
```json
{
    "id": 1,
    "contract": "550e8400-e29b-41d4-a716-446655440000",
    "contract_reference": "#A1B2C3D4E5F6",
    "requested_days": 7,
    "reason": "Unexpected delays in receiving client assets...",
    "status": "pending",
    "requested_by": "660e8400-e29b-41d4-a716-446655440001",
    "requested_by_name": "John Smith",
    "client_response": null,
    "created_at": "2026-01-20T10:30:00Z",
    "updated_at": "2026-01-20T10:30:00Z",
    "responded_at": null
}
```

**Error Responses**

400 Bad Request - Invalid Days:
```json
{
    "detail": "Extension request must be between 1 and 30 days"
}
```

400 Bad Request - Wrong Status:
```json
{
    "detail": "Extensions can only be requested for in-progress contracts"
}
```

400 Bad Request - Pending Request Exists:
```json
{
    "detail": "You already have a pending extension request for this contract. Please wait for it to be processed."
}
```

403 Forbidden:
```json
{
    "detail": "Only technicians can request extensions."
}
```

404 Not Found:
```json
{
    "detail": "Contract not found or you are not the assigned technician."
}
```

**Constraints:**
- Technician can only request 1-30 days
- Contract must be in `in_progress` status
- Only 1 pending request per technician per contract
- Additional constraints checked at model level (clean method)

---

### Respond to Extension Request

**Endpoint**
```
POST /api/contract/extension-requests/<int:request_id>/respond/
```

**Authentication:** Required (client only)

**Description:** Approve or reject technician's extension request.

**Request Body**
```json
{
    "approve": true,
    "client_response": "Okay, but no more extensions after this."
}
```

**Success Response (200 OK)**
```json
{
    "detail": "Extension request has been approved."
}
```

**Error Responses**

400 Bad Request - Already Processed:
```json
{
    "detail": "This extension request has already been processed."
}
```

403 Forbidden:
```json
{
    "detail": "Only the contract client can respond to extension requests."
}
```

**Notes:**
- If `approve: true`, technician can distribute days to stages
- If `approve: false`, request is rejected with optional reason
- Contract deadline is updated only after days are distributed

---

### Distribute Extension Days

**Endpoint**
```
POST /api/contract/extension-requests/<int:request_id>/distribute_days/
```

**Authentication:** Required (technician only)

**Description:** Allocate approved extension days to specific contract stages.

**Request Body**
```json
{
    "distribution": {
        "1": 3,
        "2": 2,
        "3": 2
    }
}
```
(Distributes 7 days total: 3 to stage 1, 2 to stage 2, 2 to stage 3)

**Success Response (200 OK)**
```json
{
    "detail": "Extension days distributed successfully.",
    "contract_duration": "2026-02-04"
}
```

**Error Responses**

400 Bad Request - Not Approved:
```json
{
    "detail": "Only approved extension requests can have days distributed."
}
```

400 Bad Request - Sum Mismatch:
```json
{
    "detail": "Sum of distributed days (10) does not match approved days (7)."
}
```

400 Bad Request - Stage Not Found:
```json
{
    "detail": "One or more stages do not exist in this contract."
}
```

403 Forbidden:
```json
{
    "detail": "Only the requesting technician can distribute extension days."
}
```

**Business Logic:**
1. Sum of distributed days must equal approved days
2. Only incomplete stages (not yet approved by client) can be extended
3. Each stage deadline is individually extended
4. Overall contract deadline is updated accordingly

---

## Contract Workflow

### Flow Diagram

```
1. Contract Creation (Client)
   └─> Status: draft
       - Client provides work description and duration
       - Awaiting technician input

2. Technician Completes Details
   └─> Status: draft → pending_acceptance
       - Technician provides amount, stages, and accepts
       - Awaiting client review and acceptance

3. Client Review & Acceptance
   └─> Status: pending_acceptance → in_progress
       - Client verifies wallet has sufficient balance
       - If balance check passes:
         * Escrow setup (funds locked)
         * Stages automatically created
         * Technician becomes unavailable
       - If balance check fails:
         * Error returned with shortfall
         * Status stays pending_acceptance

4. Active Work Phase
   └─> Status: in_progress
       - Technician updates stage descriptions/deadlines
       - Technician completes stages
       - Client reviews and approves stages
       - Payment released on each approval (minus 10% platform fee)

5. Extension Requests (Optional)
   └─> During in_progress status:
       - Technician can request 1-30 days
       - Client approves/rejects
       - If approved, technician distributes days to stages

6. Contract Completion
   └─> Status: in_progress → completed
       - When all stages approved
       - Technician becomes available again
       - Final settlement processed
```

---

## Payment System

### Payment Flow

**Contract Activation:**
```
1. Both parties accept contract
2. System checks client wallet balance
3. Full agreed_amount transferred to escrow
4. Contract enters in_progress status
```

**Stage Payment Release:**
```
For Each Stage Completion:
1. Client reviews completed work
2. Client approves stage
3. Payment calculation:
   - Stage Amount: 500,000 IQD
   - Platform Fee (10%): 50,000 IQD
   - Technician Receives: 450,000 IQD
4. Transaction recorded in wallet
5. Contract total_paid incremented
6. Check if contract is complete
```

**Contract Completion:**
```
When All Stages Approved:
1. Contract status → completed
2. Technician becomes available for new contracts
3. Final settlement notification sent
```

### Exchange Rate

- **Recording:** Exchange rate is captured at contract creation time (IQD/USD)
- **Storage:** Both IQD and USD amounts stored with the rate
- **Usage:** Used for international payments and reporting
- **Locking:** Rate does not change during contract lifetime (locked at creation)

**Example:**
```
Contract Created: 2026-01-01
IQD Amount: 2,000,000
Exchange Rate: 1,460 IQD/USD
USD Equivalent: 1,370 USD

(Locked for entire contract duration)
```

---

## Penalties & Fee System

### Platform Fee (Stage Approval)

**Default:** 10% of stage amount

**Calculation:**
```
Stage Amount: 500,000 IQD
Platform Fee: 500,000 × 0.10 = 50,000 IQD
Technician Receives: 450,000 IQD
Platform Keeps: 50,000 IQD
```

**When Applied:**
- Applied when client approves a stage
- Deducted before payment released to technician
- Accumulated for platform revenue

### Late Penalties (Future Enhancement)

**Planned Implementation:**
- Automatic penalty calculation if stage deadline passes without completion
- Configurable penalty percentage (e.g., 5% per day, capped at 20%)
- Deducted from technician's payment
- Notification sent to both parties

### Cancellation Refunds

**Client Cancellation (Draft/Pending Status):**
```
Escrow: Not yet locked
Refund: Full amount (if escrow was setup)
```

**During In-Progress:**
```
Escrow: Partially used
Refund: Remaining escrow balance
Impact: Contract cancelled, work halted
```

### Dispute Resolution (Future Enhancement)

**Planned System:**
- Client can flag completed stage as unsatisfactory
- Dispute escrow holding payment for that stage
- Arbitration process initiated
- Resolution recorded with decision and settlement

---

## Error Handling

### Common Error Scenarios

**Authorization Errors:**
```
403 Forbidden - User is not a party to the contract
```

**Validation Errors:**
```
400 Bad Request - Missing required fields
400 Bad Request - Invalid amounts or dates
400 Bad Request - Invalid status transition
```

**Business Logic Errors:**
```
400 Bad Request - Insufficient wallet balance
400 Bad Request - Cannot modify completed contracts
400 Bad Request - Technician not available
```

### Error Response Format

```json
{
    "detail": "Human-readable error message"
}
```

For validation errors:
```json
{
    "field_name": ["Error detail 1", "Error detail 2"]
}
```

---

## Rate Limiting

### Endpoints Affected
- Contract creation: Subject to general API rate limiting
- Extension requests: No special rate limiting (1 pending per technician per contract)
- Payment operations: No rate limiting (critical path)

### Future Enhancement
- Implement rate limiting per user role
- Prevent spam contract creation
- Limit extension requests to prevent abuse

---

## Summary

The contract management system provides:

✅ **Complete workflow** from creation to completion
✅ **Role-based operations** (client/technician specific actions)
✅ **Payment escrow system** with staged releases
✅ **Platform fees** automatically calculated and applied
✅ **Extension requests** with flexible day distribution
✅ **Comprehensive validation** at model and view levels
✅ **Clear error messages** for all failure scenarios
✅ **Wallet integration** for fund management and transfers

All monetary values are in **IQD (Iraqi Dinar)** with USD equivalents calculated using locked exchange rates.
