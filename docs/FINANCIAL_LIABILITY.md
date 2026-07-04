# Financial Liability

## Model
`UserFinancialLiability` — tracks outstanding debt when full recovery is impossible.

## When Created
- Post-settlement dispute where technician wallet has insufficient balance
- Approved refund exceeds recoverable wallet funds
- Remaining amount marked as outstanding liability

## Policy
- Wallet balance must remain non-negative (model-enforced)
- No hidden negative balances
- `MANUAL_RECOVERY_REQUIRED` resolution type
- Liability status: `OPEN` → `PARTIALLY_RECOVERED` → `FULLY_RECOVERED` | `WRITTEN_OFF`

## Fields
- `original_amount` — Total liability
- `recovered_amount` — Amount already recovered
- `remaining_amount` — Outstanding balance
- `status` — Current liability status
