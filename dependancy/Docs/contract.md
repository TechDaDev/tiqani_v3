# Contract API Documentation

## Table of Contents
- [Contracts](#contracts)
  - [List Contracts](#list-contracts)
  - [Create Contract](#create-contract)
  - [Get Contract Detail](#get-contract-detail)
  - [Update Contract](#update-contract)
- [Contract Stages](#contract-stages)
  - [List Contract Stages](#list-contract-stages)
  - [Get Stage Detail](#get-stage-detail)
  - [Update Stage](#update-stage)
- [Time Extension Requests](#time-extension-requests)
  - [List Extension Requests](#list-extension-requests)
  - [Create Extension Request](#create-extension-request)
  - [Respond to Extension Request](#respond-to-extension-request)
  - [Distribute Extension Days](#distribute-extension-days)
- [Contract Workflow](#contract-workflow)
- [Frontend Implementation Guide](#frontend-implementation-guide)
  - [Contract Management](#contract-management)
  - [Stage Management](#stage-management)
  - [UI Components](#ui-components)

## Contracts

### List Contracts
- **URL**: `/api/contract/contracts/`
- **Method**: `GET`
- **Description**: Get all contracts for the authenticated user (client sees their contracts, technician sees their contracts)
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "contract_reference": "string",
        "client": {
            "id": "uuid",
            "user": {
                "username": "string",
                "first_name": "string",
                "last_name": "string"
            },
            "profile_image": "url"
        },
        "technician": {
            "id": "uuid",
            "user": {
                "username": "string",
                "first_name": "string",
                "last_name": "string"
            },
            "profile_image": "url"
        },
        "work_description": "string",
        "agreed_amount": "decimal",
        "amount_usd": "decimal",
        "exchange_rate": "decimal",
        "currency": "IQD",
        "escrow_amount": "decimal",
        "total_paid": "decimal",
        "contract_duration": "date",
        "stage_number": "integer",
        "status": "draft|pending_acceptance|in_progress|completed|canceled",
        "client_accepted": "boolean",
        "technician_accepted": "boolean",
        "created_at": "datetime",
        "updated_at": "datetime",
        "stages": ["integer"],
        "can_be_accepted": "boolean"
    }
]
```
- **API Response Notes**:
  - Sensitive fields like `email` and `phone_number` are filtered out from client and technician profile data in contract API responses for security purposes
  - Only basic profile information (username, first_name, last_name, profile_image) is returned in contract contexts
- **Frontend Notes**:
  - Implement a contracts dashboard with filterable list
  - Display contract status with appropriate colors (pending: yellow, in_progress: blue, completed: green, canceled: red)
  - Show contract reference prominently for easy identification
  - Calculate and display progress (total_paid/agreed_amount) as a percentage or progress bar
  - Sort contracts by created_at (newest first) by default with option to change sort order
  - Add "Create New Contract" button for clients only
  - Display amounts in IQD with USD equivalent in parentheses when available
  - Show exchange rate information for completed contracts

### Create Contract
- **URL**: `/api/contract/contracts/`
- **Method**: `POST`
- **Description**: Initiate a new contract (client only)
- **Authentication**: Required
- **Request Body**:
```json
{
    "technician_id": "uuid",
    "work_description": "string",
    "contract_duration": "date"
}
```
- **Notes**:
  - Creating a contract doesn't require amount or stage information initially
  - Contract is created in "draft" status waiting for technician input
- **Response**:
  - Success (201): Contract object with status "draft"
  - Error (400): 
    - {"detail": "Technician does not exist or is not available."}
    - {"detail": "Work description and contract duration are required for contract creation"}
- **Frontend Notes**:
  - Implement a "Hire Me" button on technician profile page
  - Create a form for work description and duration
  - Clearly indicate this is an initial draft that requires technician input
  - Explain the contract workflow to client
  - Show loading state during submission
  - Redirect to contract detail view on successful creation
  - Display notification that technician will be notified to complete the contract

### Get Contract Detail
- **URL**: `/api/contract/contracts/<uuid:id>/`
- **Method**: `GET`
- **Description**: Get details of a specific contract
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "contract_reference": "string",
    "client": {
        "id": "uuid",
        "user": {
            "username": "string",
            "first_name": "string",
            "last_name": "string"
        },
        "profile_image": "url"
    },
    "technician": {
        "id": "uuid",
        "user": {
            "username": "string",
            "first_name": "string",
            "last_name": "string"
        },
        "profile_image": "url"
    },
    "work_description": "string",
    "agreed_amount": "decimal",
    "amount_usd": "decimal",
    "exchange_rate": "decimal",
    "currency": "IQD",
    "escrow_amount": "decimal",
    "total_paid": "decimal",
    "contract_duration": "date",
    "stage_number": "integer",
    "status": "draft|pending_acceptance|in_progress|completed|canceled",
    "client_accepted": "boolean",
    "technician_accepted": "boolean",
    "created_at": "datetime",
    "updated_at": "datetime",
    "stages": ["integer"],
    "can_be_accepted": "boolean"
}
```
- **Frontend Notes**:
  - Display comprehensive contract details in a well-organized layout
  - Show different action buttons based on user role and contract status
  - For clients with draft contracts: "Update Details" button
  - For technicians with draft contracts: "Complete Contract" button
  - For clients with pending_acceptance contracts: "Accept Contract" button
  - For technicians with pending_acceptance contracts: "Accept Contract" button
  - Include a timeline/stepper component showing current stage in the workflow
  - Display contract stages in a timeline or card-based layout
  - Show countdown to contract duration expiry date
  - Highlight the acceptance status (who has accepted and who hasn't)
  - Include communication channel or link to chat with other party
  - Display exchange rate and USD equivalent when available
  - Show escrow status and total paid progress

### Update Contract
- **URL**: `/api/contract/contracts/<uuid:id>/`
- **Method**: `PUT`/`PATCH`
- **Description**: 
  - For technicians: Complete contract details (amount, stages, duration)
  - For clients: Review and accept the contract
- **Authentication**: Required
- **Request Body (Technician Adding Details)**:
```json
{
    "work_description": "string",
    "contract_duration": "date",
    "agreed_amount": "decimal",
    "stage_number": "integer"
}
```
- **Notes**:
  - When technician adds amount or stage information, contract status automatically changes to "pending_acceptance"
  - Both agreed_amount and stage_number must be provided together
  - **Currency**: The agreed_amount must be specified in IQD (Iraqi Dinar)
  - The system will automatically calculate the USD equivalent based on the current exchange rate
  - The exchange rate is recorded at contract creation time for reference
- **Request Body (Client Accept)**:
```json
{
    "client_accepted": true
}
```
- **Request Body (Technician Accept)**:
```json
{
    "technician_accepted": true
}
```
- **Response**:
  - Success (200): Updated contract object
  - Error (400): 
    - "Cannot modify a completed contract."
    - "Invalid update request for current contract status."
    - "Only technician can set amount and stages."
    - "Both agreed amount and number of stages are required."
    - "Contract must be completed by technician before acceptance."
    - "Insufficient funds in wallet. You have X IQD but need Y IQD to initiate this contract. Please recharge your wallet with at least Z IQD more."
  - Error (403): "You do not have permission to update this contract."
- **Notes**:
  - When both client and technician accept the contract:
    - Client's wallet balance is checked against the agreed_amount in IQD
    - If sufficient funds exist, they are moved to escrow
    - If insufficient funds, client receives a notification and must add funds to their wallet
    - Exchange rate is recorded at the time of contract activation
    - Contract stages are automatically created based on stage_number
    - Technician becomes unavailable for new contracts
  - Contract activation requires both client and technician acceptance
  - All payments are in IQD (Iraqi Dinar)
  - The system stores both IQD amounts and equivalent USD values based on the exchange rate at contract creation time
- **Frontend Notes**:
  - For technicians: 
    - Provide form to complete contract details (amount, stages, duration)
    - Include explanation of stage system and payment breakdown
    - Add "Accept Contract" button after completing details
    - Display amount fields with IQD currency symbol and current exchange rate
  - For clients: 
    - Show updated contract with technician's additions
    - Display payment breakdown by stages in IQD with USD equivalents in parentheses
    - Show confirmation dialog before accepting contract
    - Warn about wallet balance requirement before accepting
    - Explain consequences of acceptance (money held in escrow, etc.)
  - Update UI immediately after successful operation
  - Disable edit controls after contract is accepted by both parties
  - Show current acceptance status (who has/hasn't accepted)
  - Add wallet balance indicator when client is about to accept a contract
  - Provide quick recharge button if wallet balance is insufficient

## Contract Stages

### List Contract Stages
- **URL**: `/api/contract/contracts/<uuid:contract_id>/stages/`
- **Method**: `GET`
- **Description**: Get all stages for a specific contract
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "integer",
        "contract": "uuid",
        "stage_number": "integer",
        "stage_description": "string",
        "amount": "decimal",
        "currency": "IQD",
        "deadline": "date",
        "is_approved_by_client": "boolean",
        "completed_at": "datetime|null"
    }
]
```
- **Frontend Notes**:
  - Display stages in sequential order with stage number
  - Show status indicators for each stage (pending, in progress, completed)
  - Highlight the current active stage
  - Present deadlines with countdown or color indicators for approaching deadlines
  - For technicians: Add "Edit" button on stages that can be updated
  - For clients: Add "Approve & Release Payment" button for completed but unapproved stages
  - Show payment amount for each stage clearly in IQD

### Get Stage Detail
- **URL**: `/api/contract/stages/<int:id>/`
- **Method**: `GET`
- **Description**: Get details of a specific contract stage
- **Authentication**: Required
- **Response**:
  - Success (200): 
```json
{
    "id": "integer",
    "contract": "uuid",
    "stage_number": "integer",
    "stage_description": "string",
    "amount": "decimal",
    "currency": "IQD",
    "deadline": "date",
    "is_approved_by_client": "boolean",
    "completed_at": "datetime|null"
}
```
- **Frontend Notes**:
  - Display detailed view of stage with all information
  - Include history of changes if available
  - Show deadline with calendar view or remaining time
  - Display stage-specific deliverables or requirements
  - Add buttons for actions based on user role and stage status
  - Provide navigation to next/previous stages
  - Display the amount in IQD

### Update Stage
- **URL**: `/api/contract/stages/<int:id>/`
- **Method**: `PUT`/`PATCH`
- **Description**: 
  - For technicians: Update stage details (description and deadline)
  - For clients: Approve stage and trigger payment release
- **Authentication**: Required
- **Request Body (Technician)**:
```json
{
    "stage_description": "string",
    "deadline": "date"
}
```
- **Request Body (Client)**:
```json
{} // Empty body is sufficient, the approval is determined by user role
```
- **Response**:
  - Success (200): 
    - Technician: Updated stage object
    - Client: {"detail": "Stage approved and payment released."}
  - Error (400):
    - "Cannot modify stages unless the contract is in progress."
    - "Stage is already approved."
  - Error (403): "You do not have permission to update this stage."
- **Notes**:
  - When a client approves a stage, the payment is released to technician after deducting platform fee (default 10%)
  - Platform fee percentage is configurable by administrators
  - When a client approves the final stage, the contract is automatically marked as completed and the technician becomes available again
  - Platform fees are tracked in the system for revenue analytics
  - Exchange rate used is the one recorded at contract creation time
- **Frontend Notes**:
  - For technicians: Provide form to edit description and deadline with validation
  - For clients: Show confirmation dialog before approving stage
  - Include information about payment amount to be released and platform fee to be deducted
  - Display success animation/notification when payment is released
  - Update contract progress indicators automatically after stage approval
  - For final stage approval: Show special messaging about contract completion

## Time Extension Requests

### List Extension Requests
- **URL**: `/api/contract/extension-requests/`
- **Method**: `GET`
- **Description**: Get all extension requests (technicians see their sent requests, clients see requests for their contracts)
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "integer",
        "contract": "uuid",
        "contract_reference": "string",
        "requested_days": "integer",
        "reason": "string",
        "status": "pending|approved|rejected",
        "requested_by": "uuid",
        "requested_by_name": "string",
        "client_response": "string|null",
        "created_at": "datetime",
        "updated_at": "datetime"
    }
]
```
- **Frontend Notes**:
  - Display extension requests in a separate section of the contract management dashboard
  - For clients: Highlight pending requests that need response
  - For technicians: Show approval status of their requests
  - Sort by created_at with newest first
  - Show contract reference for easy identification

### Create Extension Request
- **URL**: `/api/contract/extension-requests/`
- **Method**: `POST`
- **Description**: Create a new extension request (technician only)
- **Authentication**: Required
- **Request Body**:
```json
{
    "contract": "uuid",
    "requested_days": "integer",
    "reason": "string"
}
```
- **Notes**:
  - `requested_days` must be between 1 and 30
  - Contract must be in "in_progress" status
  - Only the assigned technician can request extensions
  - Technicians can only have one pending extension request at a time (across all contracts)
  - **Model Validation**: The system automatically validates these constraints at the model level to prevent invalid requests
- **Response**:
  - Success (201): Extension request object
  - Error (400): 
    - {"detail": "Extension requests cannot exceed 30 days."}
    - {"detail": "Extensions can only be requested for in-progress contracts"}
    - {"detail": "You already have a pending extension request. Please wait for it to be processed."}
  - Error (403): {"detail": "You can only request extensions for your own contracts"}
- **Frontend Notes**:
  - Create a form with days input (1-30) and reason textarea
  - Add validation for the days limit
  - Show a confirmation dialog before submitting
  - Display a success notification on creation
  - Explain that the client must approve the request

### Respond to Extension Request
- **URL**: `/api/contract/extension-requests/<int:id>/respond/`
- **Method**: `POST`
- **Description**: Client responds to an extension request (approve/reject)
- **Authentication**: Required
- **Request Body**:
```json
{
    "approve": true,
    "client_response": "string" // Optional additional comments from client
}
```
- **Response**:
  - Success (200): {"detail": "Extension request has been approved/rejected."}
  - Error (400): {"detail": "This extension request has already been processed."}
  - Error (403): {"detail": "Only the contract client can respond to extension requests."}
- **Frontend Notes**:
  - Provide approve/reject buttons for each pending request
  - Include a text area for client to explain their decision (optional)
  - Show the requested days and reason clearly
  - Remind client that approving will allow technician to distribute days among stages
  - Update the UI immediately after response

### Distribute Extension Days
- **URL**: `/api/contract/extension-requests/<int:id>/distribute_days/`
- **Method**: `POST`
- **Description**: Technician distributes approved extension days to specific stages
- **Authentication**: Required
- **Request Body**:
```json
{
    "distribution": {
        "stage_id_1": "days_1",
        "stage_id_2": "days_2"
    }
}
```
- **Notes**:
  - Only approved extension requests can have days distributed
  - Sum of distributed days must match the requested days
  - Only uncompleted stages can receive extra days
  - Stage IDs must be integers, days must be positive integers
- **Response**:
  - Success (200): 
    ```json
    {
        "detail": "Extension days distributed successfully.",
        "contract_duration": "updated_date"
    }
    ```
  - Error (400):
    - {"detail": "Only approved extension requests can have days distributed."}
    - {"detail": "Sum of distributed days (X) does not match approved days (Y)."}
    - {"detail": "Stage X does not exist or is already completed"}
    - {"detail": "No uncompleted stages to extend"}
  - Error (403): {"detail": "Only the requesting technician can distribute extension days."}
- **Frontend Notes**:
  - Create a form showing all uncompleted stages with editable day inputs
  - Display the total days remaining to allocate
  - Validate that total allocated days match the approved request
  - Show updated deadlines as days are allocated
  - Provide a submit button once all days are allocated
  - Show current stage deadlines and new proposed deadlines
  - Include stage descriptions to help technician make decisions

## Contract Workflow

1. **Contract Initiation**:
   - Client clicks "Hire Me" button on technician's profile page
   - Client fills initial work details (description and duration)
   - The contract is created with "draft" status
   - Technician receives notification about the new contract request

2. **Technician Completion**:
   - Technician reviews the initial contract details
   - Technician completes the contract by adding:
     - Agreed amount for the work
     - Number of stages (2-5)
     - Any adjustments to work description or duration
   - **Automatic Status Change**: When technician adds all required fields (amount, stages, description, duration), contract status automatically changes to "pending_acceptance"
   - Technician accepts the contract from their side (sets technician_accepted=true)
   - Client receives notification about updated contract details

3. **Client Review and Acceptance**:
   - Client reviews the complete contract details including:
     - Agreed amount
     - Number of stages and payment schedule
     - Updated work description and duration
   - Client must have sufficient wallet balance equal to at least the agreed_amount
   - Client accepts the contract from their side (sets client_accepted=true)
   - Contract system checks if both parties have accepted

4. **Contract Activation**:
   - When both client and technician have accepted the contract:
     - **Automatic Status Change**: Contract status automatically changes to "in_progress" when both parties have accepted
     - System verifies client has sufficient wallet balance for the agreed amount
     - If insufficient funds, client receives an error and notification to recharge wallet; status reverts to "pending_acceptance"
     - If sufficient funds, the agreed amount is transferred from client's wallet to escrow
     - Contract stages are automatically created based on stage_number
     - Technician becomes unavailable for new contracts
     - Both parties receive confirmation notification

5. **Stage Management**:
   - Technician updates stage details (description and deadline)
   - Technician marks stages as completed when work is done
   - Technician can request time extensions (1-30 days) if needed
   - Client reviews and approves completed stages
   - When a stage is approved:
     - Payment for that stage is released to the technician
     - Stage is marked as approved
     - Transaction record is created

6. **Contract Completion**:
   - When all stages are approved, the contract status changes to "completed"
   - Technician becomes available for new contracts again
   - Both parties receive notification of contract completion

7. **Money Flow**:
   - When contract is activated, the full amount is placed in escrow
   - As stages are completed and approved, payments are released to the technician
   - The escrow_amount and total_paid fields track these values

## Frontend Implementation Guide

### Contract Management

1. **Contract Initiation**
   - Add "Hire Me" button on technician profile page
   - Create simple initial form with work description and duration fields
   - Show clear indication that this is step 1 of the contract process
   - Provide information about next steps (technician will complete details)

2. **Contracts Dashboard**
   - Implement tabs for different contract statuses (Drafts, In Progress, Completed)
   - For draft contracts, show clear indicators of pending actions:
     - "Waiting for technician input" (for client)
     - "Complete contract details" (for technician)
     - "Review and accept" (for client after technician completes details)
   - Use cards to display contract summaries with key information
   - Include search and filter capabilities
   - Show notifications for pending actions

3. **Contract Creation**
   - Implement a guided, step-by-step form with clear instructions
   - Use a technician selection interface with ratings and specialties
   - Provide helpful tooltips explaining contract terms and stages
   - Include a summary review step before submission
   - Display client's current wallet balance during the review step
   - Add a warning if the wallet balance is insufficient for the contract amount
   - Provide a quick "Add Funds" button if needed

4. **Contract Detail View**
   - Create a comprehensive view with all contract information
   - Include a prominent status indicator and action buttons
   - Display payment summary with visual breakdown of stages
   - Add communication options between parties
   - Show wallet balance prominently when client is about to accept a contract
   - Display informative error messages if wallet balance is insufficient
   - Include recharge instructions when funds are insufficient

### Stage Management

1. **Stage Visualization**
   - Implement a timeline or stepper component to show progress
   - Use color coding for stage status (pending, active, completed)
   - Display deadlines with calendar integration
   - Show payment amounts for each stage

2. **Stage Actions**
   - For technicians: "Update Details" button with form
   - For clients: "Approve & Release Payment" button with confirmation
   - Include progress tracking for work within each stage
   - Add file upload capability for deliverables if relevant

3. **Payment Visualization**
   - Display payment status for each stage
   - Show overall contract financial summary
   - Implement animated indicators when payments are processed
   - Include transaction history if available

### UI Components

1. **Status Indicators**
   - Contract status badges: color-coded with text
   - Progress bars: showing completion percentage
   - Countdown timers: for approaching deadlines
   - Notification badges: for pending actions

2. **Action Buttons**
   - Primary actions: Approve Contract, Release Payment
   - Secondary actions: Edit Details, Cancel Contract
   - Tertiary actions: Contact Other Party, Download Contract

3. **Forms and Modals**
   - Contract creation/editing forms
   - Stage update forms
   - Confirmation dialogs for important actions
   - Success/failure notifications

4. **Data Visualization**
   - Payment breakdown charts
   - Timeline visualizations for stages
   - Calendar views for deadlines 