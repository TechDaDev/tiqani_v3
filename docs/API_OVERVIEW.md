# API Overview — tiqani_v3

Base URL (development): `http://127.0.0.1:8000`

Authentication: JWT Bearer token (`Authorization: Bearer <token>`)

---

## Route Groups

| Group | Base Path | Description | Auth Required |
|---|---|---|---|
| Health | `GET /api/health/` | Health check | No |
| Auth | `/api/auth/` | Login, register, OTP, password reset, token refresh | Mixed |
| Accounts | `/api/accounts/` | Current user profile management | Yes |
| Categories | `/api/categories/` | Service categories, skills, sub-skills | Mixed |
| Technicians | `/api/technicians/` | Public technician listings, profiles | Mixed |
| Clients | `/api/clients/` | Client profile management | Yes |
| Contracts | `/api/contracts/` | Contract lifecycle (CRUD, stages, extensions) | Yes |
| Wallet | `/api/wallet/` | Wallet balance, transactions, withdrawals, payment intents | Yes |
| Reviews | `/api/reviews/` | Public reviews, creation, moderation | Mixed |
| Notifications | `/api/notifications/` | User notifications, activity feed | Yes |
| Admin | `/api/admin/` | Admin dashboard, user/technician/contract/review/finance management | Admin |

---

## Detailed Routes

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/api/health/` | Returns service status, database health, and debug flag |

### Auth (`/api/auth/`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | JWT login (returns access + refresh tokens) |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| POST | `/api/auth/verify-otp/` | Verify OTP code |
| POST | `/api/auth/resend-otp/` | Resend OTP code |
| POST | `/api/auth/forgot-password/` | Request password reset |
| POST | `/api/auth/reset-password/` | Confirm password reset |

### Accounts (`/api/accounts/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/accounts/me/` | Get current user profile |
| PATCH | `/api/accounts/me/` | Update current user profile |
| PUT | `/api/accounts/me/` | Full update current user profile |

### Categories (`/api/categories/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/categories/` | List all categories (public) |
| GET | `/api/categories/<id>/` | Category detail with skills and sub-skills |

### Technicians (`/api/technicians/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/technicians/` | List public technicians (filterable) |
| GET | `/api/technicians/<id>/` | Technician detail with skills and reviews |

### Contracts (`/api/contracts/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/contracts/` | List user's contracts |
| POST | `/api/contracts/` | Create draft contract (client only) |
| GET | `/api/contracts/<id>/` | Contract detail |
| POST | `/api/contracts/<id>/accept/` | Accept contract |
| POST | `/api/contracts/<id>/cancel/` | Cancel contract |
| GET | `/api/contracts/<id>/stages/` | List contract stages |
| POST | `/api/contracts/<id>/stages/<sid>/submit/` | Submit stage (technician) |
| POST | `/api/contracts/<id>/stages/<sid>/approve/` | Approve stage (client) |
| GET/POST | `/api/contracts/<id>/extension-requests/` | Extension requests |

### Wallet (`/api/wallet/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/wallet/me/` | Get own wallet + recent transactions |
| GET | `/api/wallet/transactions/` | List own transactions |
| GET | `/api/wallet/withdrawals/` | List withdrawal requests |
| POST | `/api/wallet/withdrawals/` | Create withdrawal request |
| GET | `/api/wallet/withdrawals/<id>/` | Withdrawal detail |
| GET | `/api/wallet/payment-intents/` | List payment intents |
| GET | `/api/wallet/payment-intents/<id>/` | Payment intent detail |

### Reviews (`/api/reviews/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/reviews/technician/<id>/` | Public reviews for a technician |
| POST | `/api/reviews/` | Create review |
| GET | `/api/reviews/<id>/` | Public review detail |
| PATCH | `/api/reviews/<id>/` | Update own review |
| POST | `/api/reviews/<id>/respond/` | Technician responds to review |
| POST | `/api/reviews/<id>/helpful/` | Mark review as helpful |
| POST | `/api/reviews/<id>/report/` | Report review |

### Notifications (`/api/notifications/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/notifications/` | List own notifications |
| GET | `/api/notifications/<id>/` | Notification detail |
| GET | `/api/notifications/unread-count/` | Unread notification count |
| POST | `/api/notifications/<id>/mark-read/` | Mark notification read |
| POST | `/api/notifications/<id>/mark-unread/` | Mark notification unread |
| POST | `/api/notifications/mark-all-read/` | Mark all notifications read |
| GET | `/api/notifications/activity/` | Admin activity feed |

### Admin (`/api/admin/`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/api/admin/dashboard/summary/` | PlatformAdmin | Aggregated platform stats |
| GET | `/api/admin/users/` | AccountManager | List users (searchable, filterable) |
| GET | `/api/admin/users/<id>/` | AccountManager | User detail |
| PATCH | `/api/admin/users/<id>/` | SystemAdmin | Update user (safe fields) |
| POST | `/api/admin/users/<id>/activate/` | SystemAdmin | Activate user |
| POST | `/api/admin/users/<id>/deactivate/` | SystemAdmin | Deactivate user |
| GET | `/api/admin/technicians/` | AccountManager | List technicians |
| GET | `/api/admin/technicians/pending/` | AccountManager | Pending approvals |
| GET | `/api/admin/technicians/<id>/` | AccountManager | Technician detail |
| POST | `/api/admin/technicians/<id>/approve/` | SystemAdmin | Approve technician |
| POST | `/api/admin/technicians/<id>/reject/` | SystemAdmin | Reject technician |
| GET | `/api/admin/contracts/` | PlatformAdmin | List all contracts |
| GET | `/api/admin/contracts/<id>/` | PlatformAdmin | Contract detail |
| POST | `/api/admin/contracts/<id>/force-cancel/` | SystemAdmin | Force cancel contract |
| GET | `/api/admin/reviews/` | ContentModerator | List all reviews |
| GET | `/api/admin/reviews/flagged/` | ContentModerator | Flagged reviews |
| GET | `/api/admin/reviews/<id>/` | ContentModerator | Review detail with reports |
| POST | `/api/admin/reviews/<id>/hide/` | ContentModerator | Hide review |
| POST | `/api/admin/reviews/<id>/publish/` | ContentModerator | Publish review |
| POST | `/api/admin/reviews/<id>/verify/` | ContentModerator | Verify review |
| POST | `/api/admin/reviews/<id>/unverify/` | ContentModerator | Unverify review |
| GET | `/api/admin/finance/summary/` | FinanceAdmin | Financial summary |
| GET | `/api/admin/finance/platform-earnings/` | FinanceAdmin | Platform earnings |
| GET | `/api/admin/finance/payment-intents/` | FinanceAdmin | Payment intents |
| GET | `/api/admin/finance/withdrawals/` | FinanceAdmin | Withdrawal requests |
| POST | `/api/admin/finance/withdrawals/<id>/approve/` | FinanceAdmin | Approve withdrawal |
| POST | `/api/admin/finance/withdrawals/<id>/reject/` | FinanceAdmin | Reject withdrawal |
| POST | `/api/admin/finance/payment-intents/<id>/mark-paid/` | FinanceAdmin | Mark payment intent paid |
| GET | `/api/admin/activity/` | PlatformAdmin | Activity feed |

## Admin Roles

| Role | Permissions |
|---|---|
| `system_admin` | Full access to all admin APIs |
| `account_manager` | User & technician management, no finance |
| `finance_admin` | Finance & withdrawal management, no technician approval |
| `content_moderator` | Review moderation only, no finance |

---

## Frontend Integration Order

Recommended order for integrating frontend screens with the backend:

1. **Health** — Verify the API is reachable
2. **Auth** — Login, register, token management
3. **Categories** — Load service categories for registration/forms
4. **Current User (Accounts)** — Profile management
5. **Technician List/Detail** — Public browsing of technicians
6. **Client/Technician Profile** — Profile completion and editing
7. **Contract Lifecycle** — Create, view, manage contracts and stages
8. **Wallet / Payment Preparation** — Balance, transactions, withdrawals
9. **Reviews** — View and create reviews
10. **Notifications** — View and manage notifications
11. **Admin Dashboard** — Platform management (admin users only)

See `docs/FRONTEND_HANDOFF.md` for detailed frontend integration guide including auth flow, role model, route guards, and demo accounts.
