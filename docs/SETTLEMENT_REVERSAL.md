# Settlement Reversal

## Policy
Settlement reversal is only performed when funds are recoverable:
- **Pre-settlement**: Escrow still held → refund directly from escrow
- **Post-settlement recoverable**: Technician wallet has sufficient balance
- **Post-settlement partially recoverable**: Partial recovery + liability
- **Post-settlement non-recoverable**: Manual recovery required, no hidden negatives

## Rules
- Never delete or modify original settlement records
- Never edit historical transaction amounts
- Create compensating ledger entries (new transactions)
- Platform fee reversal capped at current platform wallet balance
- Original earnings preserved, status changed to `REVERSED`
- Reconciliation must reflect final state after reversal

## Service
`reverse_settlement_for_dispute()` is integrated into `resolve_dispute()` 
via `_execute_refund()` — no separate endpoint needed.
