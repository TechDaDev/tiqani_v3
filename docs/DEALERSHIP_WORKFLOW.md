# Dealership Financial Agent Workflow

This document defines the planned dealership workflow for Tiqani wallet funding, client cash-out, guarantee management, mobile usage, fee calculation, locking rules, and settlement logic.

The goal is to support the first production stage before integrating a real online payment gateway. In this stage, approved dealerships act as controlled financial agents for the platform.

---

## 1. Core idea

Dealerships are not normal users. After approval, a dealership becomes a controlled financial agent.

A dealership can help clients move money in two directions:

1. **Dealership to client wallet** — wallet recharge.
2. **Client wallet to dealership** — client cash-out / withdrawal through dealership.

Both directions must be audited, limited, and visible to finance admins.

The dealership is allowed to operate only after the platform receives and verifies guarantees such as:

- Cash guarantee.
- Legal document guarantee.
- Bank check guarantee.

These guarantees create the dealership's financial capacity.

---

## 2. Important terminology

### Guarantee pool

The total value of verified guarantees given by the dealership to the platform.

```text
total_guarantee = cash_guarantee + bank_check_guarantee + legal_document_guarantee
```

Example:

```text
Cash guarantee:          20,000,000 IQD
Bank check guarantee:    20,000,000 IQD
Legal document value:    10,000,000 IQD
Total guarantee:         50,000,000 IQD
```

### Usable credit limit

The maximum dealership exposure allowed by the platform.

Default recommendation:

```text
usable_credit_limit = total_guarantee * 80%
```

Example:

```text
Total guarantee:      50,000,000 IQD
Usage percent:        80%
Usable credit limit:  40,000,000 IQD
Safety reserve:       10,000,000 IQD
```

The 80% value should not be hardcoded. It should be configurable globally and overrideable per dealership.

### Net exposure

The amount of money the dealership effectively owes the platform after considering both recharge and cash-out flows.

```text
net_exposure =
    total_client_wallet_recharges
  - total_client_cashouts_paid_by_dealership
  - dealership_settlements_paid_to_platform
  + platform_settlements_paid_to_dealership
```

### Financial lock

When a dealership reaches the allowed exposure limit, the system automatically locks financial operations that increase platform risk.

```text
if net_exposure >= usable_credit_limit:
    dealership.status = financially_locked
```

When financially locked, the dealership cannot make more wallet recharges until the exposure is reduced or the guarantee is increased.

---

## 3. Dealership guarantee limits

Recommended first-stage limits:

```text
Minimum verified dealership guarantee: 15,000,000 IQD
Maximum verified dealership guarantee: 50,000,000 IQD
Default usable percentage:             80%
```

These values should be configurable by finance/system admins.

A dealership with 15,000,000 IQD guarantee has:

```text
Usable credit limit: 12,000,000 IQD
Safety reserve:      3,000,000 IQD
```

A dealership with 50,000,000 IQD guarantee has:

```text
Usable credit limit: 40,000,000 IQD
Safety reserve:      10,000,000 IQD
```

---

## 4. Dealership statuses

Recommended statuses:

```text
pending_review
active
financially_locked
suspended
blocked
```

Meaning:

| Status | Meaning |
|---|---|
| `pending_review` | Dealership submitted documents/guarantees, but finance admin has not approved yet. |
| `active` | Dealership can perform permitted financial operations. |
| `financially_locked` | Dealership reached the usable guarantee threshold and cannot perform risk-increasing operations. |
| `suspended` | Temporarily disabled by finance/system admin. |
| `blocked` | Permanently blocked or high-risk. |

---

## 5. Flow A — Dealership recharges client wallet

This is the main first-stage funding flow.

The client gives money to the dealership outside the system. The dealership then credits the client wallet inside the platform.

### Flow

```text
1. Client visits dealership or uses mobile flow to request recharge.
2. Dealership selects/searches client.
3. Dealership enters recharge details.
4. Backend calculates fee preview.
5. Dealership confirms recharge.
6. Backend checks dealership status and available credit.
7. Backend credits client wallet.
8. Backend creates WalletTransaction.
9. Backend creates DealershipRecharge record.
10. Backend updates dealership net exposure.
11. Backend creates ActivityLog.
12. Backend sends notification to client and dealership.
13. Finance/admin dashboard shows the operation.
```

### Rules

- Dealership must be `active`.
- Dealership must have enough available credit.
- Recharge must not exceed allowed limits.
- Client wallet must receive exactly the calculated wallet credit amount.
- Dealership exposure is calculated from the wallet credit amount only.
- Dealership fee does not increase exposure.
- All operations must be auditable.

---

## 6. Dealership recharge fee

The dealership fee should be percentage-based.

Initial recommendation:

```text
Default dealership recharge fee: 1%
```

The fee applies only to client wallet recharge.

No dealership fee should apply to:

- Client cash-out.
- Settlement.
- Reversal.
- Internal admin adjustment.

The fee should be configurable globally and optionally per dealership.

---

## 7. Fee payment modes

The system should support both fee modes.

### Mode A — Fee deducted from deposited cash

Used when the client says:

```text
I only have this amount. Deposit what remains after the fee.
```

Input:

```text
cash_received_amount
```

Calculation:

```text
dealership_fee_amount = cash_received_amount * fee_percent / 100
wallet_credit_amount = cash_received_amount - dealership_fee_amount
```

Example:

```text
Client gives dealership:     1,000,000 IQD
Fee percent:                 1%
Dealership fee:              10,000 IQD
Client wallet receives:      990,000 IQD
Dealership exposure:         990,000 IQD
```

### Mode B — Fee added on top

Used when the client says:

```text
I want exactly this amount in my wallet.
```

Input:

```text
wallet_credit_amount
```

Calculation:

```text
dealership_fee_amount = wallet_credit_amount * fee_percent / 100
cash_received_amount = wallet_credit_amount + dealership_fee_amount
```

Example:

```text
Client wants wallet credit:  1,000,000 IQD
Fee percent:                 1%
Dealership fee:              10,000 IQD
Client pays dealership:      1,010,000 IQD
Client wallet receives:      1,000,000 IQD
Dealership exposure:         1,000,000 IQD
```

### Recommended default

Use `added_on_top` as the default because it is clearer: the client wallet receives exactly the requested amount.

Still support `deducted_from_deposit` for clients who want to deposit a fixed cash amount.

---

## 8. Fee preview response

Before confirming a recharge, mobile and web clients should call a preview endpoint.

Example for `added_on_top`:

```json
{
  "fee_mode": "added_on_top",
  "fee_percent": "1.00",
  "wallet_credit_amount": "1000000",
  "dealership_fee_amount": "10000",
  "cash_received_amount": "1010000",
  "dealership_exposure_amount": "1000000",
  "message": "Client pays 1,010,000 IQD and receives 1,000,000 IQD in wallet."
}
```

Example for `deducted_from_deposit`:

```json
{
  "fee_mode": "deducted_from_deposit",
  "fee_percent": "1.00",
  "cash_received_amount": "1000000",
  "dealership_fee_amount": "10000",
  "wallet_credit_amount": "990000",
  "dealership_exposure_amount": "990000",
  "message": "Client pays 1,000,000 IQD and receives 990,000 IQD in wallet after fee."
}
```

---

## 9. Flow B — Client cash-out through dealership

This is the reverse direction.

The client has money inside the platform wallet and wants to receive physical cash from the dealership.

This is more sensitive than recharge and requires stricter confirmation.

### Recommended name

Use one of these names in code/API:

```text
Dealership-assisted withdrawal
Client cash-out via dealership
DealershipClientCashout
```

### Safe flow

```text
1. Client opens mobile app.
2. Client selects dealership.
3. Client enters cash-out amount.
4. Backend checks client wallet balance.
5. Backend checks dealership cash-out status and limits.
6. Backend creates pending cash-out request.
7. Backend generates OTP/confirmation code.
8. Client goes to dealership.
9. Dealership gives physical cash to client.
10. Client gives OTP/code to dealership after receiving cash.
11. Dealership submits OTP/code.
12. Backend verifies code.
13. Backend deducts client wallet.
14. Backend records dealership cash-out ledger entry.
15. Backend creates WalletTransaction.
16. Backend updates net settlement/exposure.
17. Backend creates ActivityLog.
18. Backend sends notifications.
```

### Rules

- Cash-out must be client-initiated.
- Dealership should not be able to complete cash-out without client confirmation.
- Use OTP/confirmation code.
- Code must expire.
- Large cash-outs may require finance admin approval.
- Cash-out should not charge the 1% dealership recharge fee.
- Cash-out should reduce dealership net exposure.
- Cash-out must be disputable.

---

## 10. Cash-out limits

Cash-out needs its own limits because it depends on physical cash/liquidity at the dealership.

Recommended fields:

```text
single_cashout_limit
daily_cashout_limit
monthly_cashout_limit
requires_admin_approval_above
cashout_enabled
```

Example:

```text
Single cash-out max:                2,000,000 IQD
Daily cash-out max:                 10,000,000 IQD
Admin approval required above:      5,000,000 IQD
```

Even if cash-out reduces exposure, it should be blocked if the dealership is suspended, blocked, or cash-out disabled.

---

## 11. Net settlement example

Dealership guarantee:

```text
Total guarantee:       50,000,000 IQD
Usable limit:          40,000,000 IQD
```

Recharge activity:

```text
Client wallet recharges: 30,000,000 IQD
```

Cash-out activity:

```text
Client cash-outs paid by dealership: 5,000,000 IQD
```

Net exposure:

```text
30,000,000 - 5,000,000 = 25,000,000 IQD
```

Meaning:

```text
Dealership still owes platform: 25,000,000 IQD
Available recharge capacity:   15,000,000 IQD
```

If later the dealership pays 10,000,000 IQD settlement to platform:

```text
Net exposure = 25,000,000 - 10,000,000 = 15,000,000 IQD
Available recharge capacity = 40,000,000 - 15,000,000 = 25,000,000 IQD
```

---

## 12. Locking rules

### Recharge locking

Recharge should be blocked when:

```text
net_exposure + new_wallet_credit_amount > usable_credit_limit
```

Example:

```text
Usable credit limit:          40,000,000 IQD
Current net exposure:         37,000,000 IQD
Available recharge capacity:  3,000,000 IQD
Requested recharge:           5,000,000 IQD
Result:                       reject
```

Allowed example:

```text
Requested recharge: 3,000,000 IQD
Result: approved
New net exposure: 40,000,000 IQD
New status: financially_locked
```

### Cash-out behavior while financially locked

A financially locked dealership may still be allowed to process cash-outs because cash-outs reduce exposure.

However, cash-out must still obey:

- Cash-out enabled flag.
- Daily/single/monthly limits.
- OTP confirmation.
- Suspension/block rules.
- Admin approval rules for large amounts.

---

## 13. Recommended models

### DealershipProfile

```text
user
business_name
owner_name
phone
governorate
address
status
usage_limit_percent
min_required_guarantee
max_allowed_guarantee
single_cashout_limit
daily_cashout_limit
monthly_cashout_limit
cashout_enabled
recharge_enabled
approved_by
approved_at
```

### DealershipGuarantee

```text
dealership
cash_amount
bank_check_amount
legal_document_amount
total_guarantee_amount
document_file
status
verified_by
verified_at
expires_at
notes
```

### DealershipRechargeFeeConfig

```text
fee_percent
minimum_fee_amount
maximum_fee_amount
default_fee_mode
is_active
created_by
created_at
```

Recommended default:

```text
fee_percent = 1.00
default_fee_mode = added_on_top
```

### DealershipClientRecharge

```text
dealership
client
fee_mode
fee_percent
cash_received_amount
wallet_credit_amount
dealership_fee_amount
dealership_exposure_amount
status
receipt_number
proof_file
wallet_transaction
created_by
approved_at
reversed_at
reversal_reason
```

### DealershipClientCashout

```text
dealership
client
amount
status
confirmation_code_hash
code_expires_at
confirmed_at
wallet_transaction
dealership_ledger_entry
created_at
completed_at
cancelled_at
dispute_reason
```

### DealershipCreditLedger

```text
dealership
transaction_type:
  guarantee_added
  client_recharge
  recharge_reversal
  client_cashout
  cashout_reversal
  settlement_paid_to_platform
  settlement_paid_by_platform
  manual_adjustment
amount
balance_after
reference_id
created_by
created_at
notes
```

### DealershipSettlement

```text
dealership
period_start
period_end
total_recharges
total_cashouts
net_amount
direction:
  dealership_owes_platform
  platform_owes_dealership
status
settled_by
settled_at
notes
```

---

## 14. Mobile-first considerations

Some dealership features will be used by mobile apps. The backend must be designed with mobile usability and safety in mind.

### Mobile users

The mobile app may be used by:

- Client.
- Dealership employee/agent.
- Dealership owner/manager.
- Finance/admin user.

### Mobile requirements

The API should support:

- Fast client lookup by phone/email/QR code.
- Recharge preview before confirmation.
- Cash-out request preview before confirmation.
- OTP-based cash-out confirmation.
- Offline-safe receipt number generation or server-generated receipt numbers.
- Clear transaction status.
- Idempotency keys for mobile retry safety.
- Push-ready notification events later.
- Simple daily summary for dealership agent.
- Deposit/cash-out history filtering by date/status/client.
- Safe proof upload for receipts/documents.

### Idempotency

Mobile networks can fail or retry requests. Any money-moving endpoint should support an idempotency key.

Example header:

```text
Idempotency-Key: 5f59b7d1-7c90-43dc-a85f-6fdb67d7031b
```

The backend should reject duplicate processing while returning the previous result safely.

### Mobile preview endpoints

Recommended endpoints:

```text
POST /api/dealership/recharges/preview/
POST /api/dealership/recharges/
POST /api/dealership/cashouts/preview/
POST /api/dealership/cashouts/
POST /api/dealership/cashouts/{id}/confirm-code/
GET  /api/dealership/me/summary/
GET  /api/dealership/recharges/
GET  /api/dealership/cashouts/
GET  /api/dealership/settlements/
```

### Mobile response clarity

Money responses should always include all important values as strings to avoid floating point issues.

Example:

```json
{
  "currency": "IQD",
  "fee_mode": "added_on_top",
  "fee_percent": "1.00",
  "cash_received_amount": "1010000",
  "wallet_credit_amount": "1000000",
  "dealership_fee_amount": "10000",
  "available_recharge_capacity_before": "15000000",
  "available_recharge_capacity_after": "14000000",
  "status": "completed"
}
```

---

## 15. Security and audit rules

All dealership financial actions must create audit/activity records.

Must audit:

- Dealership approval.
- Guarantee verification.
- Recharge preview if needed.
- Recharge completion.
- Recharge reversal.
- Cash-out request creation.
- Cash-out confirmation.
- Cash-out dispute.
- Settlement creation.
- Settlement approval/completion.
- Financial lock/unlock.
- Manual admin adjustment.

Security requirements:

- No direct wallet balance editing from dealership APIs.
- All wallet changes must go through service layer.
- Use database transactions.
- Lock relevant rows during money movement.
- Store money as Decimal, not float.
- Store IQD amounts as whole numbers or Decimal with zero fractional digits.
- Never trust client-submitted fee amount.
- Backend calculates all fees.
- Backend calculates all exposure values.
- Backend calculates all settlement values.
- All status changes must be controlled by explicit actions.

---

## 16. Notifications

Recommended notifications:

### Client

- Wallet recharge completed.
- Cash-out request created.
- Cash-out completed.
- Cash-out expired/cancelled/disputed.

### Dealership

- Recharge completed.
- Cash-out request received.
- Cash-out completed.
- Financial lock warning.
- Financial lock activated.
- Settlement created/completed.

### Finance/admin

- Dealership near 80% threshold.
- Dealership financially locked.
- Large cash-out request created.
- Guarantee expiring.
- Settlement due.

---

## 17. Dashboard requirements

Finance/system admin dashboard should show:

- Total dealership guarantees.
- Total dealership net exposure.
- Total client recharges.
- Total client cash-outs.
- Available credit per dealership.
- Dealerships near threshold.
- Financially locked dealerships.
- Pending guarantees.
- Pending settlements.
- Large or suspicious operations.
- Daily recharge/cash-out volume.
- Client wallet funding history.
- Cash-out history.
- Reversal/dispute history.

---

## 18. Recommended implementation phase

Recommended phase name:

```text
Phase 11 — Dealership Financial Agent and Wallet Recharge System
```

Scope should include:

- Dealership profile and approval.
- Guarantee management.
- Recharge fee configuration.
- Dealership to client wallet recharge.
- Two fee modes.
- Client to dealership cash-out.
- OTP/code confirmation for cash-out.
- Net exposure calculation.
- Financial locking at threshold.
- Settlement tracking.
- Mobile-ready APIs.
- Audit/activity logs.
- Notifications.
- Admin/finance dashboard endpoints.
- Tests and Postman collection.

---

## 19. Deferred items

These should not block the first implementation:

- Real payment gateway.
- Automatic banking reconciliation.
- Full fraud scoring engine.
- WebSocket real-time events.
- Advanced analytics dashboard.
- Multi-branch dealership hierarchy.
- QR code receipt scanning.

These can be added later.

---

## 20. Final business rule summary

Dealerships can recharge client wallets and process client cash-outs only after verified guarantees are approved. The platform calculates a usable credit limit from the dealership guarantee, normally 80%. Dealership wallet recharges increase net exposure, while client cash-outs reduce net exposure. When net exposure reaches the usable limit, the dealership is financially locked from new recharge operations. Recharge fees are percentage-based, configurable, and apply only to client wallet recharges. The system supports both fee-added-on-top and fee-deducted-from-deposit modes. All money-moving actions must be mobile-ready, audited, transactional, and visible to finance/admin users.
