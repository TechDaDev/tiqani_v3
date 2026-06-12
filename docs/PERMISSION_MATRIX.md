# Permission Matrix

## Roles

| Role | Description |
|---|---|
| `anonymous` | Unauthenticated visitor |
| `client` | Registered client user |
| `technician` | Registered technician/service provider |
| `dealership` | Dealership financial agent |
| `system_admin` | Full system administrator |
| `finance_admin` | Financial operations administrator |
| `account_manager` | Account management staff |
| `content_moderator` | Content moderation staff |

## Endpoint Access

| Endpoint | anonymous | client | technician | dealership | system_admin | finance_admin | account_manager | content_moderator |
|---|---|---|---|---|---|---|---|---|
| **Health** | | | | | | | | |
| `GET /api/health/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/health/live/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/health/ready/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/health/deep/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Auth** | | | | | | | | |
| `POST /api/auth/register/` | ✓ | – | – | – | – | – | – | – |
| `POST /api/auth/login/` | ✓ | – | – | – | – | – | – | – |
| `POST /api/auth/otp/request/` | ✓ | – | – | – | – | – | – | – |
| `POST /api/auth/otp/verify/` | ✓ | – | – | – | – | – | – | – |
| `POST /api/auth/password/reset/` | ✓ | – | – | – | – | – | – | – |
| `POST /api/auth/token/refresh/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/auth/logout/` | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Account** | | | | | | | | |
| `GET/PUT /api/accounts/me/` | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/technicians/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/technicians/:id/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Categories** | | | | | | | | |
| `GET /api/categories/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/categories/:id/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Contracts** | | | | | | | | |
| `POST /api/contracts/` | – | ✓ | ✓ | – | ✓ | – | – | – |
| `GET /api/contracts/` | – | ✓ | ✓ | – | ✓ | – | – | – |
| `GET /api/contracts/:id/` | – | own | own | – | ✓ | – | – | – |
| `PATCH /api/contracts/:id/accept/` | – | – | ✓ | – | – | – | – | – |
| `PATCH /api/contracts/:id/cancel/` | – | ✓ | ✓ | – | – | – | – | – |
| `POST /api/contracts/:id/stages/` | – | – | ✓ | – | – | – | – | – |
| `POST /api/contracts/:id/extensions/` | – | – | ✓ | – | – | – | – | – |
| **Reviews** | | | | | | | | |
| `POST /api/reviews/` | – | ✓ | – | – | – | – | – | – |
| `GET /api/reviews/` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/reviews/:id/report/` | – | ✓ | ✓ | ✓ | ✓ | – | – | ✓ |
| `POST /api/reviews/:id/helpful/` | – | ✓ | ✓ | ✓ | ✓ | – | – | ✓ |
| **Wallet** | | | | | | | | |
| `GET /api/wallet/summary/` | – | ✓ | ✓ | – | ✓ | ✓ | – | – |
| `GET /api/wallet/transactions/` | – | ✓ | ✓ | – | ✓ | ✓ | – | – |
| `POST /api/wallet/withdraw/` | – | ✓ | ✓ | – | – | – | – | – |
| `POST /api/wallet/payment-intent/` | – | ✓ | ✓ | – | – | – | – | – |
| **Dealership** | | | | | | | | |
| `GET /api/dealership/summary/` | – | – | – | ✓ | ✓ | ✓ | – | – |
| `POST /api/dealership/recharge/` | – | – | – | ✓ | ✓ | – | – | – |
| `POST /api/dealership/cashout/` | – | – | – | ✓ | ✓ | – | – | – |
| `POST /api/dealership/cashout/confirm/` | – | – | – | ✓ | ✓ | – | – | – |
| `GET /api/dealership/settlements/` | – | – | – | ✓ | ✓ | ✓ | – | – |
| **Notifications** | | | | | | | | |
| `GET /api/notifications/` | – | own | own | own | ✓ | ✓ | ✓ | ✓ |
| `PATCH /api/notifications/:id/read/` | – | own | own | own | ✓ | ✓ | ✓ | ✓ |
| `POST /api/notifications/mark-all-read/` | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Admin Dashboard** | | | | | | | | |
| `GET /api/admin/summary/` | – | – | – | – | ✓ | ✓ | – | – |
| `GET /api/admin/users/` | – | – | – | – | ✓ | – | ✓ | – |
| `GET /api/admin/contracts/` | – | – | – | – | ✓ | – | – | – |
| `GET /api/admin/finance/` | – | – | – | – | ✓ | ✓ | – | – |
| `GET /api/admin/audit-export/` | – | – | – | – | ✓ | ✓ | – | – |
| **Schema / Docs** | | | | | | | | |
| `GET /api/schema/` | dev | dev | dev | dev | ✓ | ✓ | ✓ | ✓ |
| `GET /api/docs/` | dev | dev | dev | dev | ✓ | ✓ | ✓ | ✓ |
| `GET /api/redoc/` | dev | dev | dev | dev | ✓ | ✓ | ✓ | ✓ |

**Legend:** ✓ = Allowed | – = Denied | own = Own records only | dev = Public in development only

## Media Access

| Resource | Type | Access |
|---|---|---|
| Profile images | Public (S3) | Any authenticated user |
| Category icons | Public (S3) | Any user |
| Contract documents | Private (S3) | Contract participants + admin |
| Identification documents | Private (S3) | Owner + admin |
| Guarantee documents | Private (S3) | Dealership owner + finance_admin |
| Recharge proofs | Private (S3) | Dealership owner + finance_admin |
