# Wallet App Documentation

Last updated: 2026-02-28

This document reflects the current implementation of the `wallet/` Django app, which owns the financial domain for Tiqani V3.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture Notes](#architecture-notes)
- [Data Models](#data-models)
  - [Wallet](#wallet-model)
  - [WalletTransaction](#wallettransaction-model)
  - [PlatformWallet](#platformwallet-model)
  - [PlatformWalletTransaction](#platformwallettransaction-model)
- [Transaction Types Reference](#transaction-types-reference)
- [Platform Fee Policy](#platform-fee-policy)
- [Cross-App Usage](#cross-app-usage)
- [Admin Panel](#admin-panel)
- [Frontend Notes](#frontend-notes)
- [Frontend Implementation Guideline](#frontend-implementation-guideline)

---

## Overview

The `wallet` app is the dedicated financial domain for the platform. It manages:

- Per-user wallets holding balances in IQD (Iraqi Dinar)
- Full transaction logs per wallet
- A singleton global platform wallet that collects platform fees
- A platform-level transaction ledger for fee tracking and financial auditing

The app has no exposed API endpoints. All wallet operations are triggered internally by other apps (primarily `contract`).

---

## Features

- User wallet with balance tracking (IQD)
- Full immutable transaction log per user wallet
- 7 transaction types covering deposit, withdrawal, payment, refund, escrow, release, and platform fee
- Global singleton platform wallet to receive and track all platform fee income
- Per-fee transaction ledger on the platform wallet (source user, source wallet, contract, amount, running balance)
- Non-refundable bilateral fee on contract activation (10% from client, 10% from technician)
- Escrow hold and release flow per contract stage

---

## Architecture Notes

- The `wallet` app owns the financial models logically, but the database tables are named with the `accounts_` prefix (`accounts_wallet`, `accounts_wallettransaction`, `accounts_platformwallet`, `accounts_platformwallettransaction`) due to the historical migration path.
- All wallet models use `managed = False` — Django does not manage table creation/deletion for these models. The tables were created by `accounts` app migrations and remain there.
- Migration state for these models is explicitly tracked via `SeparateDatabaseAndState` in `accounts/migrations/0008_*` and concrete model creation in `wallet/migrations/0002_*`.
- The `wallet` app is added to `INSTALLED_APPS` in `tiqani_v3/settings.py`.

---

## Data Models

### Wallet Model

One wallet per user. Created automatically at registration via the `accounts` app registration logic.

| Field | Type | Description |
|---|---|---|
| `id` | `BigAutoField` | Auto-incrementing integer PK |
| `user` | `OneToOneField → accounts.CustomUser` | Wallet owner |
| `balance` | `DecimalField(15,2)` | Current IQD balance (always ≥ 0) |
| `transaction_id` | `CharField(32)` | Unique UUID hex identifier, auto-generated on save |
| `updated_at` | `DateTimeField` | Last modification time |

**Business rules**
- Balance cannot go negative — `save()` raises `ValueError` if attempted.
- `transaction_id` is assigned once on first save and never changes.

---

### WalletTransaction Model

Immutable log of all financial events on a user wallet.

| Field | Type | Description |
|---|---|---|
| `id` | `UUIDField` | UUID primary key |
| `wallet` | `ForeignKey → Wallet` | Owner wallet (protected from deletion) |
| `contract` | `ForeignKey → contract.Contract` | Associated contract (nullable) |
| `transaction_type` | `CharField(20)` | One of the 7 types — see [Transaction Types Reference](#transaction-types-reference) |
| `amount` | `DecimalField(15,2)` | Transaction amount in IQD |
| `amount_usd` | `DecimalField(10,2)` | USD equivalent (optional, for reference) |
| `exchange_rate` | `DecimalField(10,2)` | Exchange rate used (optional) |
| `description` | `TextField` | Human-readable transaction note |
| `is_delete` | `BooleanField` | Soft-delete flag |
| `created_at` | `DateTimeField` | Creation timestamp |
| `updated_at` | `DateTimeField` | Last update timestamp |

**Business rules**
- Records are created, never mutated after creation.
- Related wallet is protected from deletion (`PROTECT`).
- Ordered by `-created_at` by default.

---

### PlatformWallet Model

Singleton global wallet holding accumulated platform fee income.

| Field | Type | Description |
|---|---|---|
| `id` | `BigAutoField` | Auto-incrementing integer PK |
| `key` | `CharField(64)` | Unique key, always `"global_platform_wallet"` — enforces singleton |
| `currency` | `CharField(3)` | Always `"IQD"` |
| `balance` | `DecimalField(15,2)` | Total accumulated balance of platform fees collected |
| `total_fees_collected` | `DecimalField(15,2)` | Lifetime sum of all fees (client + technician) |
| `total_client_fees` | `DecimalField(15,2)` | Lifetime sum of client-side fees only |
| `total_technician_fees` | `DecimalField(15,2)` | Lifetime sum of technician-side fees only |
| `created_at` | `DateTimeField` | Creation timestamp |
| `updated_at` | `DateTimeField` | Last modification time |

**Business rules**
- Use `PlatformWallet.get_global_wallet()` to retrieve (or auto-create) the singleton instance.
- Balance cannot go negative — `save()` raises `ValueError` if attempted.
- All fee aggregate fields are updated together atomically when a contract activates.

---

### PlatformWalletTransaction Model

Transaction-level ledger for every fee credit into the platform wallet.

| Field | Type | Description |
|---|---|---|
| `id` | `UUIDField` | UUID primary key |
| `platform_wallet` | `ForeignKey → PlatformWallet` | Target platform wallet (protected) |
| `contract` | `ForeignKey → contract.Contract` | Contract that generated the fee (nullable) |
| `source_user` | `ForeignKey → accounts.CustomUser` | User who paid the fee (nullable) |
| `source_wallet` | `ForeignKey → Wallet` | User wallet the fee was debited from (nullable) |
| `source_type` | `CharField(20)` | `client`, `technician`, or `system` |
| `amount` | `DecimalField(15,2)` | Fee amount collected |
| `balance_after` | `DecimalField(15,2)` | Platform wallet balance after this credit |
| `description` | `TextField` | Human-readable note |
| `is_delete` | `BooleanField` | Soft-delete flag |
| `created_at` | `DateTimeField` | Creation timestamp |
| `updated_at` | `DateTimeField` | Last update timestamp |

**Business rules**
- One record is created per party (client + technician) per contract activation.
- `balance_after` is a snapshot recorded at time of creation — not recalculated later.
- Ordered by `-created_at` by default.

---

## Transaction Types Reference

| Type | Value | Direction | Trigger |
|---|---|---|---|
| `deposit` | `deposit` | Credit (+) | External fund deposit into user wallet |
| `withdrawal` | `withdrawal` | Debit (−) | User withdrawal from wallet |
| `payment` | `payment` | Debit (−) | General payment event |
| `refund` | `refund` | Credit (+) | Escrow refund on contract cancellation |
| `escrow` | `escrow` | Debit (−) | Funds locked when contract activates (from client) |
| `release` | `release` | Credit (+) | Stage payment released to technician on client approval |
| `platform_fee` | `platform_fee` | Debit (−) | Non-refundable fee at contract activation (from client and technician) |

---

## Platform Fee Policy

Upon contract activation (transition from `pending_acceptance` → `in_progress`):

1. **Client** is charged `agreed_amount × 10%` as a non-refundable platform fee.
2. **Client** is also charged `agreed_amount` as escrow (held against stage releases).
3. **Technician** is charged `agreed_amount × 10%` as a non-refundable platform fee.
4. Both fees are credited to the global `PlatformWallet` and logged as individual `PlatformWalletTransaction` records.
5. The escrow amount is held internally (tracked in `Contract.escrow_amount`) and released stage-by-stage as the client approves stages.

**On cancellation**: the `escrow_amount` is refunded to the client via a `refund` transaction. Platform fees are **never refunded**.

**On stage approval**: the stage `amount` is transferred to the technician wallet via a `release` transaction.

---

## Cross-App Usage

The wallet app is used internally by:

### `accounts` app
- Creates a `Wallet` instance for each new user during registration.

### `contract` app
- Reads client and technician wallet balances before contract activation.
- Validates client balance covers `agreed_amount + client_platform_fee` before acceptance.
- Calls `_setup_contract_escrow()` on activation which:
  - Debits client wallet (escrow + platform fee)
  - Debits technician wallet (platform fee)
  - Credits `PlatformWallet`
  - Creates `WalletTransaction` records (escrow, platform_fee × 2)
  - Creates `PlatformWalletTransaction` records (client fee, technician fee)
- Calls `approve_by_client()` on stage approval which creates a `release` transaction for the technician.
- Calls `cancel()` on contract cancellation which creates a `refund` transaction for the client.
- `ContractStage.transaction` is a `OneToOneField → wallet.WalletTransaction` linking the release transaction.

---

## Admin Panel

Wallet models are registered in `accounts/admin.py`:

| Model | Features |
|---|---|
| `Wallet` | List by user + balance, transaction count link |
| `WalletTransaction` | List by type/date, contract link |
| `PlatformWallet` | Full summary; all fields read-only; add permission restricted to one record |
| `PlatformWalletTransaction` | Full ledger view, filter by source type, contract link |

The `wallet/admin.py` file exists but contains no registrations — models are administered via the `accounts` admin module to keep the admin panel consolidated.

---

## Frontend Notes

- No direct wallet API endpoints are exposed at this time.
- Wallet balance and transaction history are expected to be surfaced through a future dedicated wallet API (to be built on top of this app).
- Contract acceptance errors referencing insufficient balance originate from wallet balance checks inside the contract activation flow (see `contract.md` for endpoint-level errors).
- Platform fee amounts are derived as `agreed_amount × 0.10` — frontend can calculate and display these in the contract acceptance confirmation UI.

---

## Frontend Implementation Guideline

- Display wallet balance prominently before clients accept contracts — they need `agreed_amount + 10%` available.
- Show technicians their wallet balance before accepting contracts — they need `agreed_amount × 10%` available for the activation fee.
- Build wallet transaction list from future `/api/wallet/transactions/` endpoint (not yet implemented).
- For the platform fee, show both amounts (client fee + technician fee) in the contract confirmation screen so users are aware of the non-refundable deductions before accepting.
- On contract cancellation confirmation, surface the escrow refund amount so users know what they will receive back.
