# Refund Architecture

## Overview
Refunds are financial mutations triggered by dispute resolution. They must be idempotent, auditable, and preserve financial invariants.

## Source Types
- `ESCROW` — Pre-settlement refund from contract escrow
- `TECHNICIAN_WALLET_REVERSAL` — Post-settlement wallet debit
- `PLATFORM_FEE_REVERSAL` — Compensating platform credit
- `SPLIT_SOURCES` — Combination of multiple source types
- `MANUAL_RECOVERY` — Off-platform recovery
- `SANDBOX_PROVIDER` — Simulated provider refund

## Execution Flow
1. Staff proposes resolution → `RESOLUTION_PROPOSED`
2. Staff resolves → `resolve_dispute()` with financial params
3. Service validates amounts against escrow/wallet holdings
4. Creates compensating ledger entries
5. Creates `RefundRecord`
6. Updates dispute to `RESOLVED`
7. Creates audit events and notifications

## Idempotency
- All refund operations support `idempotency_key`
- Duplicate keys return existing result
- Prevents double refund, double reversal, double liability

## Safety
- Wallet balance cannot go negative (model constraint)
- Escrow cannot exceed original amount
- Platform fee reversal capped at current platform wallet balance
- Original settlement records never modified
