# Frontend Handoff Guide — tiqani_v3

## Backend Base URL

Development: `http://127.0.0.1:8000`
Production: `https://your-domain.com`

All API paths are prefixed with `/api/`.

---

## Auth Flow

### 1. Register
```
POST /api/auth/register/
Body: { "username", "email", "password", "password2", "role": "client|technician" }
Response: 201 { "user": {...}, "tokens": { "access": "...", "refresh": "..." } }
```

### 2. Verify email / OTP
```
POST /api/auth/verify-otp/
Body: { "otp_code": "123456", "verification_id": "..." }
Response: 200 { "status": "ok" }
```

### 3. Login
```
POST /api/auth/login/
Body: { "username": "...", "password": "..." }
Response: 200 { "access": "...", "refresh": "...", "user": {...} }
```

### 4. Refresh token
```
POST /api/auth/token/refresh/
Body: { "refresh": "..." }
Response: 200 { "access": "...", "refresh": "..." }
```

### 5. Send Bearer token
All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Role Model

| Role | Description | Guard |
|---|---|---|
| `client` | End user who posts jobs | `request.user.role == 'client'` |
| `technician` | Service provider | `request.user.role == 'technician'` |
| `admin` | Platform staff with sub-roles | `request.user.role == 'admin'` |

## Admin Role Model

| Admin Role | Permissions |
|---|---|
| `system_admin` | Full access — users, technicians, contracts, reviews, finance |
| `finance_admin` | Finance only — earnings, withdrawals, payment intents |
| `content_moderator` | Reviews only — hide/publish/verify/unverify |
| `account_manager` | Users & technicians only — list, detail, activate/deactivate |

---

## Required Frontend Route Guards

| Guard | Criteria |
|---|---|
| Public | No auth required (health, categories, public reviews) |
| Auth Required | Valid JWT token in header |
| Client Only | `user.role == 'client'` |
| Technician Only | `user.role == 'technician'` |
| Admin Only | `user.role == 'admin'` or `is_staff` |
| Finance Admin Only | Admin + `admin_profile.role == 'finance_admin'` |
| Content Moderator Only | Admin + `admin_profile.role == 'content_moderator'` |
| Account Manager Only | Admin + `admin_profile.role == 'account_manager'` |

---

## API Response Patterns

### Paginated List Response
```json
{
  "count": 100,
  "next": "http://.../?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Validation Error Response
```json
{
  "field_name": ["This field is required."],
  "non_field_errors": ["..."]
}
```

### Error Status Codes
| Code | Meaning | Handling |
|---|---|---|
| 200 | Success | Process response data |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Show validation errors to user |
| 401 | Unauthorized | Redirect to login (token expired/missing) |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Wait and retry |

---

## Demo Accounts

Run `python manage.py seed_demo_data` first.

| Username | Password | Role | Notes |
|---|---|---|---|
| `admin_demo` | `AdminDemo123!` | system_admin | Full admin access |
| `finance_demo` | `FinanceDemo123!` | finance_admin | Finance only |
| `moderator_demo` | `ModeratorDemo123!` | content_moderator | Review moderation |
| `account_manager_demo` | `AccountManagerDemo123!` | account_manager | User/technician mgmt |
| `client_demo` | `ClientDemo123!` | client | Has wallet with balance |
| `tech_demo` | `TechDemo123!` | technician | Approved, has reviews |
| `tech_pending_demo` | `TechPendingDemo123!` | technician | Pending approval |

---

## Recommended Frontend Screens

1. **Login / Register** — `/api/auth/login/`, `/api/auth/register/`
2. **Dashboard Home** — Technician list, user stats
3. **Technician Listing / Detail** — `/api/technicians/`, `/api/technicians/:id/`
4. **Client Profile** — `/api/accounts/me/`, `/api/clients/me/`
5. **Technician Profile** — `/api/accounts/me/`, `/api/technicians/:id/`
6. **Contract List / Detail** — `/api/contracts/`, `/api/contracts/:id/`
7. **Contract Stages** — `/api/contracts/:id/stages/`
8. **Wallet** — `/api/wallet/me/`, `/api/wallet/transactions/`
9. **Reviews** — `/api/reviews/technician/:id/`
10. **Notifications** — `/api/notifications/`, `/api/notifications/unread-count/`
11. **Admin Dashboard** — `/api/admin/dashboard/summary/`

---

## Environment Variables (Frontend)

```env
# React / Vite
VITE_API_BASE_URL=http://localhost:8000

# Next.js
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## CORS / CSRF Notes

- CORS is configured server-side via `CORS_ALLOWED_ORIGINS` env variable
- For local development, `http://localhost:3000` and `http://127.0.0.1:3000` are allowed
- CSRF is disabled for API endpoints (JWT-based auth)
- For production, update `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` in deployment environment

---

## Postman Collection

Located at: `postman/Tiqani_v3_Complete_Backend.postman_collection.json`

1. Import into Postman
2. Set `base_url` to your server URL
3. Run `seed_demo_data` on the backend
4. Login with demo users to get tokens
5. Execute requests by folder

See `docs/POSTMAN.md` for detailed instructions.

---

## Known Limitations

- **No real payment gateway yet** — Wallet uses payment intents and manual admin approval. No Stripe/MyFatoorah integration.
- **No chat system** — Real-time messaging between clients and technicians not implemented.
- **No dispute workflow** — Contract disputes require manual admin intervention.
- **No WebSockets** — Notifications are pull-based (polling). No real-time push.
- **No file CDN** — Media files are stored locally. For production, configure external storage (S3, etc.).
- **ASGI not fully utilized** — ASGI is configured but app uses WSGI via Gunicorn. WebSocket support not implemented.
