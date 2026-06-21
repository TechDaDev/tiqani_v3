# Phase 9 Backend Findings — Escrow Release & Financial Settlement

## 1. Current Financial Models

### Wallet (`wallet.models.Wallet`)
- **Table:** `accounts_wallet`
- **Ownership:** Created by `accounts/migrations/0006`, state removed by `accounts/migrations/0008` (SeparateDatabaseAndState), re-created as unmanaged proxy in `wallet/migrations/0002`
- **Managed:** `False`
- **Fields:** `user` (FK), `balance` (Decimal), `transaction_id`, `updated_at`
- **Note:** Cannot add new fields via standard Django migrations. Must use RunSQL or add to accounts migration.

### WalletTransaction (`wallet.models.WalletTransaction`)
- **Table:** `accounts_wallettransaction`
- **Managed:** `False` — same ownership pattern as Wallet
- **Types:** `deposit`, `withdrawal`, `payment`, `refund`, `escrow`, `release`, `platform_fee`
- **Fields:** `wallet`, `contract`, `transaction_type`, `amount`, `amount_usd`, `exchange_rate`, `description`
- **Missing:** `balance_after` field
- **Description is free-text** — no structured reference fields

### PlatformWallet (`wallet.models.PlatformWallet`)
- **Table:** `accounts_platformwallet`
- **Managed:** `False`
- **Fields:** `key`, `currency`, `balance`, `total_fees_collected`, `total_client_fees`, `total_technician_fees`

### PlatformWalletTransaction (`wallet.models.PlatformWalletTransaction`)
- **Table:** `accounts_platformwallettransaction`
- **Managed:** `False`
- **Fields:** `platform_wallet`, `contract`, `source_user`, `source_wallet`, `source_type`, `amount`, `balance_after`, `description`

### PlatformFeeConfig (`wallet.models.PlatformFeeConfig`)
- **Managed:** `True` — own table
- **Fields:** `name`, `technician_commission_rate`, `client_service_fee_rate`, `is_active`

### ContractPaymentBreakdown (`wallet.models.ContractPaymentBreakdown`)
- **Managed:** `True`
- **Fields:** `contract` (OTO), `contract_amount`, `technician_commission_amount`, `client_service_fee_amount`, `total_platform_fee`, `client_total_amount`, `technician_net_amount`
- **Note:** Snapshot taken at contract acceptance/offer acceptance time

### PlatformEarning (`wallet.models.PlatformEarning`)
- **Managed:** `True`
- **Fields:** `contract`, `stage` (nullable), `earning_type`, `amount`, `status`, `wallet_transaction`
- **Types:** `technician_commission`, `client_service_fee`, `adjustment`
- **Statuses:** `pending`, `earned`, `reversed`
- **Currently created by:** `record_platform_earnings_for_contract()` and `record_stage_release_with_fees()`

### PaymentIntent (`wallet.models.PaymentIntent`)
- **Managed:** `True`
- **Fields:** `contract`, `user`, `amount`, `currency`, `purpose`, `provider`, `status`, `metadata`, `paid_at`
- **Purpose:** `contract_funding`, `wallet_deposit`, `withdrawal`
- **Status:** `pending`, `requires_action`, `paid`, `failed`, `canceled`

### WithdrawalRequest (`wallet.models.WithdrawalRequest`)
- **Managed:** `True`
- **Fields:** `user`, `wallet`, `amount`, `currency`, `status`, `requested_method`, `notes`, `admin_note`, `reviewed_at`, `paid_at`
- **Statuses:** `pending`, `approved`, `rejected`, `paid`, `canceled`

### Contract (`contract.models.Contract`) — Financial Fields
- `escrow_amount`: Amount held in escrow (set to `agreed_amount` on funding)
- `total_paid`: Total paid to technician so far (incremented by stage approval)
- `client_platform_fee`: Client fee (set at activation)
- `technician_platform_fee`: Technician fee (set at activation)

## 2. Table Ownership Summary

| Table | Created By | Current Model | Managed |
|-------|-----------|--------------|---------|
| `accounts_wallet` | accounts/0006 | wallet.Wallet | False |
| `accounts_wallettransaction` | accounts/0006 | wallet.WalletTransaction | False |
| `accounts_platformwallet` | accounts/0006 | wallet.PlatformWallet | False |
| `accounts_platformwallettransaction` | accounts/0006 | wallet.PlatformWalletTransaction | False |
| `wallet_platformfeeconfig` | wallet/0003 | wallet.PlatformFeeConfig | True |
| `wallet_contractpaymentbreakdown` | wallet/0003 | wallet.ContractPaymentBreakdown | True |
| `wallet_platformearning` | wallet/0003 | wallet.PlatformEarning | True |
| `wallet_paymentintent` | wallet/0003 | wallet.PaymentIntent | True |
| `wallet_withdrawalrequest` | wallet/0003 | wallet.WithdrawalRequest | True |

## 3. Existing Release & Fee Behavior

### `record_platform_earnings_for_contract()` (wallet/services.py)
- Creates TWO PlatformEarning records per contract: `technician_commission` + `client_service_fee`
- Called at stage approval time (milestone approval)
- Is idempotent — checks existence before creating

### `record_stage_release_with_fees()` (wallet/services.py)
- Approves a stage, calculates proportional fees, creates per-stage earnings
- Currently used by legacy `ContractStage` (not `ExecutionMilestone`)
- **Not called** by Phase 8 execution services

### Phase 8 `confirm_completion()` in Contract model
- Sets `status='completed'`, `completed_at=now`
- Sets `technician.is_available = True`
- **Does NOT release escrow, does NOT credit technician, does NOT record platform earnings**
- Comment says: "Escrow remains held. No payout."

### Phase 8 milestone approval (`approve_milestone()`)
- Only changes milestone status, **no financial release**

## 4. Existing Withdrawal Behavior

### `create_withdrawal_request()` (wallet/services.py)
- Checks wallet.balance >= amount
- Creates WithdrawalRequest with PENDING status
- **No available balance reservation — multiple pending requests can overcommit**

### `approve_withdrawal_request()` (wallet/services.py)
- **Deducts wallet balance immediately on approval** (before payout)
- Creates WITHDRAWAL transaction
- Sets status to APPROVED

### `reject_withdrawal_request()` (wallet/services.py)
- Only changes status to REJECTED
- **No balance restoration needed** since approval didn't deduct (but if it did, there's no restoration on rejection)

### Risks:
1. Multiple pending requests can overcommit balance (no reservation)
2. Balance deducted on approval, not on payout — risk of deducting before actual payout
3. No PROCESSING or FAILED states
4. No idempotency
5. No payout retry

## 5. Financial Key Relationships

```
client funded total (PaymentIntent.amount = client_total_amount)
 = contract_amount + client_service_fee_amount

contract_amount (principal)
 = technician_net_amount + technician_commission_amount

total_platform_fee
 = technician_commission_amount + client_service_fee_amount
```

At the current Phase 8 state after completion:
- `Contract.escrow_amount` = `agreed_amount` (= `contract_amount` = principal)
- `Contract.total_paid` = 0 (no stage-based payments released yet)
- `PaymentIntent.amount` = `client_total_amount` (principal + client fee)
- Escrow has NOT been reduced

## 6. Recommended Phase 9 Design

### Strategy: Full-contract settlement at once

Since Phase 8 milestone approval does NOT release proportional funds and `total_paid` is 0, Phase 9 should release the full principal at settlement.

### New Model: `ContractSettlement` (managed, wallet app)
- `contract` (OTO with unique constraint on completed settlements)
- `payment_breakdown` (FK to ContractPaymentBreakdown)
- `released_principal`, `technician_net_amount`, `technician_commission_amount`, `client_service_fee_amount`, `total_platform_fee`
- `currency`, `status` (pending/processing/completed/failed/reversed)
- `initiated_by`, `initiated_at`, `completed_at`, `failed_at`, `failure_code`
- `idempotency_key`

### Settlement Flow:
1. Client initiates release on completed contract
2. Service validates eligibility
3. Within transaction.atomic:
   a. Lock contract (select_for_update), breakdown, technician wallet, platform wallet
   b. Create ContractSettlement (PENDING)
   c. Credit technician wallet: balance += technician_net_amount
   d. Create WalletTransaction (RELEASE, positive, linked to contract)
   e. Create PlatformEarning records (technician_commission + client_service_fee, EARNED)
   f. Credit platform wallet: balance += total_platform_fee
   g. Create PlatformWalletTransaction entries
   h. Reduce Contract.escrow_amount to 0
   i. Set ContractSettlement to COMPLETED
   j. Create audit events
   k. Send notifications

### Withdrawal Changes:
- Add `PROCESSING`, `FAILED` statuses to WithdrawalRequest
- Add available-balance rule: available = wallet.balance - SUM(pending + approved withdrawal amounts)
- Deduct balance at PROCESSING (not APPROVED)
- Add payout retry
- Require minimum withdrawal amount

### New Models to Add (managed, wallet app):
1. `ContractSettlement` — settlement record
2. None else needed — reuse existing models

### Services to Add:
1. `wallet/settlement_services.py` — settlement logic
2. `wallet/sandbox_payout_gateway.py` — sandbox payout (already exists for funding)

### Views/Endpoints to Add:
- Settlement eligibility, creation, retrieval
- Available balance
- Enhanced withdrawal with new statuses
- Staff payout processing

## 7. Migration Plan
- Create `wallet/migrations/0004_contractsettlement.py` (managed model)
- Modify `WithdrawalRequest` status choices (add Processing, Failed)
- No changes to unmanaged Wallet/WalletTransaction models needed for Phase 9
