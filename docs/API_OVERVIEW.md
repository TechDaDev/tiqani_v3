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
| POST | `/api/auth/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Logout (blacklist refresh token) |
| POST | `/api/auth/verify-email/` | Verify email / OTP code |
| POST | `/api/auth/resend-otp/` | Resend OTP code |
| POST | `/api/auth/forgot-password/` | Request password reset |
| POST | `/api/auth/password-reset-confirm/` | Confirm password reset |

### Accounts (`/api/accounts/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/accounts/me/` | Any | Get current user profile |
| PATCH | `/api/accounts/me/` | Any | Update current user profile |
| PUT | `/api/accounts/me/` | Any | Full update current user profile |

### Clients (`/api/clients/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/clients/me/` | Client | Get client profile |
| PATCH | `/api/clients/me/` | Client | Update client profile fields (phone, address, etc.) |

### Categories (`/api/categories/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/categories/` | Public | List all categories |
| POST | `/api/categories/` | Admin | Create category |
| GET | `/api/categories/<id>/` | Public | Category detail with skills and sub-skills |
| PUT | `/api/categories/<id>/` | Admin | Update category |
| PATCH | `/api/categories/<id>/` | Admin | Partial update category |
| DELETE | `/api/categories/<id>/` | Admin | Delete category |
| GET | `/api/categories/skills/` | Public | List all skills |
| GET | `/api/categories/sub-skills/` | Public | List all sub-skills |

### Technicians (`/api/technicians/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/technicians/` | Public | List public technicians (filterable) |
| GET | `/api/technicians/<id>/` | Public | Technician detail with skills and reviews |
| GET | `/api/technicians/me/` | Technician | Get own technician profile |
| PATCH | `/api/technicians/me/` | Technician | Update own technician profile |
| GET | `/api/technicians/me/skills/` | Technician | Get own skills |
| PUT | `/api/technicians/me/skills/` | Technician | Update own skills |
| GET | `/api/technicians/me/images/` | Technician | List own portfolio images |
| POST | `/api/technicians/me/images/` | Technician | Upload portfolio image |
| GET | `/api/technicians/me/images/<id>/` | Technician | Portfolio image detail |
| DELETE | `/api/technicians/me/images/<id>/` | Technician | Delete portfolio image |
| GET | `/api/technicians/me/availability/` | Technician | Get availability status |
| POST | `/api/technicians/me/availability/` | Technician | Toggle availability |
| GET | `/api/technicians/me/ratings/` | Technician | Get own rating stats |

### Contracts (`/api/contracts/`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/contracts/` | List user's contracts |
| POST | `/api/contracts/` | Create draft contract (client only) |
| GET | `/api/contracts/<id>/` | Contract detail |
| POST | `/api/contracts/<id>/accept/` | Accept contract |
| POST | `/api/contracts/<id>/cancel/` | Cancel contract |
| GET | `/api/contracts/<id>/stages/` | List contract stages |
| GET | `/api/contracts/<id>/stages/<sid>/` | Stage detail |
| POST | `/api/contracts/<id>/stages/<sid>/submit/` | Submit stage (technician) |
| POST | `/api/contracts/<id>/stages/<sid>/approve/` | Approve stage (client) |
| GET | `/api/contracts/<id>/extension-requests/` | List extension requests |
| POST | `/api/contracts/<id>/extension-requests/create/` | Create extension request |
| POST | `/api/contracts/<id>/extension-requests/<rid>/approve/` | Approve extension |
| POST | `/api/contracts/<id>/extension-requests/<rid>/reject/` | Reject extension |

### Wallet (`/api/wallet/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/wallet/me/` | Any | Get own wallet + recent transactions |
| GET | `/api/wallet/transactions/` | Any | List own transactions |
| GET | `/api/wallet/withdrawals/` | Any | List withdrawal requests |
| POST | `/api/wallet/withdrawals/` | Any | Create withdrawal request |
| GET | `/api/wallet/withdrawals/<id>/` | Any | Withdrawal detail |
| POST | `/api/wallet/withdrawals/<id>/approve/` | Admin | Approve withdrawal |
| POST | `/api/wallet/withdrawals/<id>/reject/` | Admin | Reject withdrawal |
| GET | `/api/wallet/payment-intents/` | Any | List payment intents |
| GET | `/api/wallet/payment-intents/<id>/` | Any | Payment intent detail |
| POST | `/api/wallet/payment-intents/<id>/mark-paid/` | Admin | Mark payment intent paid |
| GET | `/api/wallet/fee-config/` | Any | List platform fee configs |
| GET | `/api/wallet/contracts/<id>/breakdown/` | Any | Get contract payment breakdown |

### Reviews (`/api/reviews/`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/reviews/technician/<id>/` | Public | Public reviews for a technician |
| POST | `/api/reviews/` | Client | Create review |
| GET | `/api/reviews/<id>/` | Public | Public review detail |
| PATCH | `/api/reviews/<id>/` | Reviewer | Update own review |
| POST | `/api/reviews/<id>/respond/` | Technician | Technician responds to review |
| POST | `/api/reviews/<id>/helpful/` | Any | Mark review as helpful |
| POST | `/api/reviews/<id>/report/` | Any | Report review |
| POST | `/api/reviews/<id>/moderate/publish/` | Moderator | Publish a hidden review |
| POST | `/api/reviews/<id>/moderate/hide/` | Moderator | Hide a review |
| POST | `/api/reviews/<id>/moderate/verify/` | Moderator | Verify a review |
| POST | `/api/reviews/<id>/moderate/unverify/` | Moderator | Unverify a review |

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
