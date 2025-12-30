# Contract Models - Quick Reference Guide

## Model Overview

```
Contract (Main model)
├── ContractStage (1:M relationship)
│   └── WalletTransaction (O2O for payment)
├── TimeExtensionRequest (1:M relationship)
└── WalletTransaction (escrow & refunds)
```

---

## Contract Model Quick Reference

### Creating a Contract
```python
from contract.models import Contract

contract = Contract.objects.create(
    client=client_profile,
    technician=tech_profile,
    work_description="Work details..."
)
# Status: draft (auto-generated contract_reference: #ABC123DEF456)
```

### Status Progression
```
draft → pending_acceptance → in_progress → completed
            ↓
        canceled (at any time)
```

### Key Fields at a Glance

| Field | Type | Required? | Notes |
|-------|------|-----------|-------|
| client | FK | ✅ | ClientProfile |
| technician | FK | ✅ | TechnicianProfile |
| work_description | TextField | ✅ | Work to perform |
| agreed_amount | Decimal | ✅ for acceptance | Total in IQD |
| stage_number | Choice(2-5) | ✅ for acceptance | Payment stages |
| contract_duration | DateField | ✅ for acceptance | Completion date |
| contract_reference | CharField | Auto | Unique reference |
| amount_usd | Decimal | Optional | For reference |
| exchange_rate | Decimal | Optional | At contract creation |
| escrow_amount | Decimal | Auto | Set when in_progress |
| total_paid | Decimal | Auto | Updated by stage approvals |
| status | Choice | Auto | Current status |
| client_accepted | Boolean | False | Client acceptance flag |
| technician_accepted | Boolean | False | Technician acceptance flag |

### Common Operations

#### Check if Ready for Acceptance
```python
if contract.can_be_accepted():
    print("Ready for acceptance")
else:
    incomplete = contract.get_incomplete_fields()
    print(f"Missing: {incomplete}")
```

#### Move to In Progress (Both accept)
```python
contract.client_accepted = True
contract.technician_accepted = True
contract.save()
# Auto-transitions to in_progress
# Auto-creates stages
# Auto-creates escrow transaction
```

#### Mark Completed
```python
contract.mark_completed()
# Status → completed
# Technician available again
```

#### Cancel Contract
```python
contract.cancel(reason="Client request")
# Status → canceled
# Escrow refunded
# Technician available again
```

---

## ContractStage Quick Reference

### Create Stages (Auto)
```python
# Stages auto-created when contract moves to in_progress
# Stage count = contract.stage_number
# Each stage amount = agreed_amount / stage_number

for stage in contract.stages.all():
    print(f"Stage {stage.stage_number}: {stage.amount} IQD")
```

### Mark Work Complete
```python
stage = contract.stages.get(stage_number=1)
stage.stage_description = "Foundation prep completed"
stage.deadline = date.today() + timedelta(days=7)
stage.mark_complete()
# completed_at = now()
```

### Approve & Release Payment
```python
stage.approve_by_client()
# Creates WalletTransaction (type='release')
# Transfers stage.amount to technician wallet
# Updates contract.total_paid
```

### Stage Query Examples
```python
# All stages
all_stages = contract.stages.all()

# Pending approval
pending = contract.stages.filter(is_approved_by_client=False)

# Completed
completed = contract.stages.filter(completed_at__isnull=False)

# Approved
approved = contract.stages.filter(is_approved_by_client=True)
```

---

## TimeExtensionRequest Quick Reference

### Create Extension Request
```python
extension = TimeExtensionRequest.objects.create(
    contract=contract,
    requested_by=contract.technician,
    requested_days=5,
    reason="Waiting for parts"
)
# Status: pending
```

### Client Actions

#### Approve Extension
```python
extension.approve(client_response="Approved - thanks for update")
# status = 'approved'
# contract.contract_duration += timedelta(days=requested_days)
# responded_at = now()
```

#### Reject Extension
```python
extension.reject(rejection_reason="Must stick to original timeline")
# status = 'rejected'
# client_response = rejection_reason
# responded_at = now()
```

### Query Examples
```python
# Get all pending for a contract
pending = contract.extension_requests.filter(status='pending')

# Get all technician's pending requests
my_pending = TimeExtensionRequest.objects.filter(
    requested_by=technician,
    status='pending'
)

# Get approved extensions
approved = contract.extension_requests.filter(status='approved')
```

---

## Database Queries

### Get Client Contracts
```python
client_contracts = Contract.objects.filter(
    client=client_profile
).select_related('technician__user')
```

### Get Technician Active Contracts
```python
active_contracts = Contract.objects.filter(
    technician=tech_profile,
    status='in_progress'
).select_related('client__user')
```

### Get Pending Acceptance
```python
pending = Contract.objects.filter(
    status='pending_acceptance'
).select_related('client__user', 'technician__user')
```

### Get Stages Awaiting Approval
```python
stages_pending = ContractStage.objects.filter(
    is_approved_by_client=False,
    completed_at__isnull=False
).select_related('contract')
```

### Get Technician Pending Extensions
```python
extensions = TimeExtensionRequest.objects.filter(
    requested_by=technician,
    status='pending'
).select_related('contract')
```

---

## Field Descriptions (help_text)

### Contract
- **client**: Client initiating the contract
- **technician**: Technician performing the work
- **contract_reference**: Auto-generated unique contract reference
- **work_description**: Detailed description of work to be performed
- **agreed_amount**: Total agreed amount in IQD (required before acceptance)
- **amount_usd**: USD equivalent for reference only
- **exchange_rate**: Exchange rate (IQD to USD) at contract creation
- **escrow_amount**: Amount held in escrow in IQD
- **total_paid**: Total amount paid so far in IQD
- **contract_duration**: Expected completion date
- **status**: Current contract status
- **stage_number**: Number of payment stages for this contract
- **client_accepted**: Client has accepted the contract
- **technician_accepted**: Technician has accepted the contract
- **is_deleted**: Soft delete flag
- **created_at**: Contract creation timestamp
- **updated_at**: Last modification timestamp

### ContractStage
- **contract**: Parent contract
- **stage_number**: Sequential stage number (1, 2, 3, etc.)
- **stage_description**: Description of work for this stage
- **amount**: Payment amount for this stage in IQD
- **deadline**: Target completion date for this stage
- **is_approved_by_client**: Client has approved completion of this stage
- **completed_at**: When technician marked this stage as complete
- **transaction**: Associated payment transaction for this stage

### TimeExtensionRequest
- **contract**: Contract being extended
- **requested_by**: Technician requesting the extension
- **requested_days**: Number of days requested (1-30)
- **reason**: Reason for requesting the extension
- **status**: Current status of the extension request
- **client_response**: Client's response or rejection reason
- **created_at**: Request creation timestamp
- **responded_at**: When client responded to the request

---

## Status Choices Reference

### Contract Status
```python
CONTRACT_STATUS = [
    ('draft', 'Draft'),                    # Initial state
    ('pending_acceptance', 'Pending Acceptance'),  # Waiting for acceptance
    ('in_progress', 'In Progress'),        # Active contract
    ('completed', 'Completed'),            # Finished successfully
    ('canceled', 'Canceled'),              # Terminated
]
```

### TimeExtensionRequest Status
```python
STATUS_CHOICES = [
    ('pending', 'Pending'),      # Awaiting client response
    ('approved', 'Approved'),    # Client approved
    ('rejected', 'Rejected'),    # Client rejected
]
```

### Contract Stage Choices
```python
STAGE_CHOICES = [
    (2, '2 Stages'),
    (3, '3 Stages'),
    (4, '4 Stages'),
    (5, '5 Stages'),
]
```

---

## Common Workflows

### Workflow 1: Simple Contract Lifecycle

**Step 1: Create Contract (Technician)**
```python
contract = Contract.objects.create(
    client=client_profile,
    technician=tech_profile,
    work_description="AC installation"
)
# Status: draft
```

**Step 2: Add Details (Technician)**
```python
contract.agreed_amount = Decimal('25000.00')
contract.stage_number = 2
contract.contract_duration = date.today() + timedelta(days=14)
contract.save()
# Auto-transitions to: pending_acceptance
```

**Step 3: Accept (Both)**
```python
contract.client_accepted = True
contract.technician_accepted = True
contract.save()
# Auto-transitions to: in_progress
# Auto-creates 2 stages of 12,500 IQD each
# Auto-creates escrow transaction
```

**Step 4: Complete Stage 1**
```python
stage1 = contract.stages.get(stage_number=1)
stage1.stage_description = "Installation complete"
stage1.mark_complete()

stage1.approve_by_client()
# Releases 12,500 IQD to technician wallet
```

**Step 5: Complete Stage 2**
```python
stage2 = contract.stages.get(stage_number=2)
stage2.stage_description = "Testing and handover"
stage2.mark_complete()

stage2.approve_by_client()
# Releases remaining 12,500 IQD to technician wallet
```

**Step 6: Mark Completed**
```python
contract.mark_completed()
# Status: completed
# Technician available for new contracts
```

### Workflow 2: Extension Request

**Step 1: Request Extension**
```python
extension = TimeExtensionRequest.objects.create(
    contract=contract,
    requested_by=contract.technician,
    requested_days=3,
    reason="Supplier delayed parts shipment"
)
```

**Step 2: Client Approves**
```python
extension.approve("Approved - we understand")
# Deadline extended by 3 days
# responded_at = now()
```

**Or: Client Rejects**
```python
extension.reject("Need completion by original date")
# status = rejected
# responded_at = now()
```

### Workflow 3: Contract Cancellation

```python
contract.cancel(reason="Client changed mind - no longer needs service")
# Status: canceled
# Escrow amount refunded
# Technician marked available
# Refund transaction created
```

---

## Performance Tips

### 1. Use select_related for FK
```python
contracts = Contract.objects.select_related(
    'client__user',
    'technician__user'
)
```

### 2. Use prefetch_related for Reverse FK
```python
contracts = Contract.objects.prefetch_related('stages', 'extension_requests')
```

### 3. Use filter before ordering
```python
active = Contract.objects.filter(status='in_progress').order_by('-created_at')
```

### 4. Bulk operations
```python
ContractStage.objects.filter(is_approved_by_client=False).update(...)
```

---

## Common Issues & Solutions

### Issue: Cannot mark contract as accepted
**Solution**: Check `contract.can_be_accepted()` first
```python
if not contract.can_be_accepted():
    print(contract.get_incomplete_fields())
```

### Issue: Stages not created when moving to in_progress
**Solution**: Ensure both `client_accepted` and `technician_accepted` are True before saving

### Issue: Extension request validation failed
**Solution**: Ensure:
- Contract is in_progress status
- Requested days between 1-30
- Technician is assigned to the contract
- No other pending request exists

### Issue: Cannot release payment for stage
**Solution**: Must have:
- Stage marked as complete (`stage.completed_at` set)
- `is_approved_by_client` not already True

---

## Admin Interface Usage

```python
# In admin.py (if registered)
from django.contrib import admin
from contract.models import Contract, ContractStage, TimeExtensionRequest

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_filter = ['status', 'created_at']
    search_fields = ['contract_reference', 'client__user__username']
    readonly_fields = ['contract_reference', 'created_at', 'updated_at']

@admin.register(ContractStage)
class ContractStageAdmin(admin.ModelAdmin):
    list_filter = ['is_approved_by_client', 'contract']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(TimeExtensionRequest)
class TimeExtensionRequestAdmin(admin.ModelAdmin):
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'responded_at']
```

---

**Last Updated**: December 28, 2024  
**Status**: ✅ Ready for Production  
**Migration**: 0002 applied

