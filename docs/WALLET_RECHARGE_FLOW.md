# Wallet Recharge Flow

Tiqani now supports an RMP-inspired manual wallet recharge flow without replacing the existing wallet, payment intent, escrow, settlement, withdrawal, refund, dispute, or admin financial systems.

## Flow

1. A user submits a wallet recharge request with an amount, optional note, and transfer receipt.
2. The request remains `pending_review`.
3. Finance/admin reviews the receipt.
4. Approval credits the user's wallet once and creates one `WalletTransaction` with `transaction_type=deposit`.
5. Rejection records the review note and does not change wallet balance.
6. Users may cancel only their own pending requests.

## Safety Rules

- Only one `pending_review` request is allowed per user.
- Receipt files are validated by extension, content type, and size.
- Receipt download endpoints require the request owner or finance/admin access.
- Serializers expose receipt download URLs and metadata, not raw storage paths.
- Approval is atomic and idempotent: repeat approval on an already-approved request returns the approved request and does not create a second credit.
- Approval and rejection create admin activity records and best-effort notifications.

## Upload Policy

Default receipt constraints:

- Extensions: `pdf`, `jpg`, `jpeg`, `png`, `webp`
- Content types: `application/pdf`, `image/jpeg`, `image/png`, `image/webp`
- Size: `MAX_WALLET_RECHARGE_RECEIPT_UPLOAD_MB`, default `5`
- Storage path: `wallet/recharge_receipts/<user_id>/<uuid>.<ext>`

## Endpoints

User:

- `GET /api/wallet/recharge-requests/`
- `POST /api/wallet/recharge-requests/`
- `GET /api/wallet/recharge-requests/<id>/`
- `POST /api/wallet/recharge-requests/<id>/cancel/`
- `GET /api/wallet/recharge-requests/<id>/receipt/`

Finance/admin:

- `GET /api/admin/financial/recharge-requests/`
- `GET /api/admin/financial/recharge-requests/<id>/`
- `POST /api/admin/financial/recharge-requests/<id>/approve/`
- `POST /api/admin/financial/recharge-requests/<id>/reject/`
- `GET /api/admin/financial/recharge-requests/<id>/receipt/`

## Known Limits

This is a manual receipt review flow. It does not integrate a bank/payment provider webhook yet. Future provider integration should create or reconcile requests through this same review/audit model instead of editing wallet balances directly.
