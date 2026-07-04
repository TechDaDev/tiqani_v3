# Admin Financial Discovery

## Existing Backend Models

- `wallet.PaymentIntent`: contract funding / wallet deposit / withdrawal payment intent. Stores amount, currency, purpose, provider, masked provider reference candidate, status, timestamps, and internal metadata.
- `wallet.Wallet`: one wallet per user, current balance, transaction id, updated timestamp.
- `wallet.WalletTransaction`: immutable user wallet ledger rows for deposit, withdrawal, payment, refund, escrow, release, and platform fee movement.
- `wallet.PlatformWallet`: global platform wallet totals for collected fees and platform balance.
- `wallet.PlatformWalletTransaction`: platform fee ledger rows tied to source user/wallet and optional contract.
- `wallet.WithdrawalRequest`: technician/admin withdrawal lifecycle with pending, approved, processing, rejected, paid, failed, and canceled statuses.
- `wallet.ContractSettlement`: escrow settlement record for completed contract release, technician net amount, platform fees, status, and idempotency key.
- `wallet.ContractPaymentBreakdown`: accepted contract fee snapshot.
- `wallet.PlatformEarning`: platform revenue records with pending, earned, and reversed status.
- `dispute.RefundRecord`: dispute-driven refund record with source type, status, method, masked provider reference candidate, and linked wallet transaction.
- `dispute.ChargebackEvent`: sandbox/admin chargeback event with amount, reason code, status, and outcome.
- `dispute.UserFinancialLiability`: outstanding recoverability/liability records after disputes or reversals.
- `notification.ActivityLog`: admin/system audit feed used for financial write visibility.

## Existing Financial Transaction Types

- Wallet transaction types: `deposit`, `withdrawal`, `payment`, `refund`, `escrow`, `release`, `platform_fee`.
- Payment intent purposes: `contract_funding`, `wallet_deposit`, `withdrawal`.
- Refund source types: `escrow`, `technician_wallet_reversal`, `platform_fee_reversal`, `split_sources`, `manual_recovery`, `sandbox_provider`.
- Contract settlement statuses: `pending`, `processing`, `completed`, `failed`, `reversed`.
- Withdrawal statuses: `pending`, `approved`, `processing`, `rejected`, `paid`, `failed`, `canceled`.

## Existing Admin Financial Endpoints

- `GET /api/admin/finance/summary/`
- `GET /api/admin/finance/platform-earnings/`
- `GET /api/admin/finance/payment-intents/`
- `GET /api/admin/payments/`
- `GET /api/admin/finance/withdrawals/`
- `POST /api/admin/finance/withdrawals/<id>/approve/`
- `POST /api/admin/finance/withdrawals/<id>/reject/`
- `POST /api/admin/finance/payment-intents/<id>/mark-paid/`
- `GET /api/admin/activity/`
- `GET /api/admin/audit-events/`

## Added Admin Financial Endpoints

- `GET /api/admin/financial/overview/`
- `GET /api/admin/financial/payments/`
- `GET /api/admin/financial/refunds/`
- `GET /api/admin/financial/withdrawals/`
- `GET /api/admin/financial/ledger/`
- `GET /api/admin/financial/escrow/`
- `GET /api/admin/financial/audit/`
- `GET /api/admin/financial/users/<user_id>/wallet/`

## Permission Rules

- All admin financial endpoints require authenticated finance-admin access through `IsFinanceAdmin`.
- `IsFinanceAdmin` allows superusers, system admins, and finance admins.
- Participant users receive `403`.
- Ledger, escrow, refunds, payments, wallet, and audit views are read-only.
- Existing withdrawal approve/reject actions remain controlled writes and now require reason/note.

## Safe Admin Actions

- Inspect payment, refund, withdrawal, ledger, escrow, wallet, and audit records.
- Filter/paginate/search financial records.
- Review withdrawals only through existing wallet services.
- Record reason/audit metadata for financial write actions.

## Unsafe Admin Actions

- Delete ledger/history records.
- Edit wallet balances directly.
- Recalculate historical ledger rows.
- Bypass wallet/payment/refund/dispute services.
- Expose or replay raw provider payloads.
- Expose card data, payment tokens, provider secrets, or unmasked private provider references.

## Data Never Exposed

- Payment tokens.
- Card numbers, CVV, expiry, cardholder raw data.
- API keys, provider secrets, raw provider webhook payloads.
- Raw storage paths.
- Arbitrary metadata values when not explicitly mapped.

## Known Gaps

- Provider integration is currently sandbox/manual; no real provider reconciliation feed exists.
- Current admin financial audit uses `ActivityLog`; not every historical financial model mutation has rich before/after metadata.
- Richer refund category reporting depends on dispute/refund source records already present.
- There is no arbitrary balance adjustment service, intentionally.
