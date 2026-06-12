# Frontend/Mobile Quickstart — tiqani_v3

A concise reference for frontend and mobile developers integrating with the Tiqani backend.

---

## Base API URL

| Environment | URL |
|---|---|
| Development | `http://127.0.0.1:8000` |
| Production | `https://your-domain.com` |

All API paths are prefixed with `/api/`.

---

## Auth Flow Summary

1. **Register** — `POST /api/auth/register/` → OTP sent to email
2. **Verify Email** — `POST /api/auth/verify-email/` with OTP code + verification_id
3. **Login** — `POST /api/auth/login/` → returns `access` + `refresh` tokens + `userdata`
4. **Use Token** — Include `Authorization: Bearer <access_token>` in all authenticated requests
5. **Refresh** — `POST /api/auth/refresh/` with `refresh` token when access expires
6. **Logout** — `POST /api/auth/logout/` (blacklists refresh token)

**Token Lifetimes:** Access = 120 min, Refresh = 7 days.

---

## OpenAPI Docs URLs

| Resource | URL |
|---|---|
| **Schema (JSON)** | `GET /api/schema/` |
| **Swagger UI** | `GET /api/docs/` |
| **Redoc** | `GET /api/redoc/` |

In production, these are only accessible to authenticated admin users unless `API_DOCS_PUBLIC=True`.

---

## WebSocket URL

```
ws://<host>:8000/ws/notifications/?token=<access_token>
```

- Only access tokens (not refresh) are accepted
- Invalid/expired tokens return code `4401`
- On connection, server sends: `{"type": "connection.accepted", "unread_count": N}`
- Events: notification created, notification read, unread count updated

---

## Request Headers

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | For authenticated endpoints |
| `Content-Type` | `application/json` | For POST/PATCH/PUT with body |
| `X-Request-ID` | Any UUID (optional, for tracing) | Recommended for debugging |

Every response includes `X-Request-ID` header for end-to-end tracing.

---

## JWT Token Usage

After login, store both tokens:

```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi...",
  "userdata": {
    "id": "uuid",
    "username": "john_doe",
    "role": "client",
    ...
  }
}
```

- Use `access` token for API calls
- When access expires (401 response), call `/api/auth/refresh/` with the `refresh` token
- On logout, blacklist the `refresh` token

---

## Demo Accounts Reference

| Username | Role | Password |
|---|---|---|
| `admin_demo` | system_admin | `DemoPass123!` |
| `finance_demo` | finance_admin | `DemoPass123!` |
| `moderator_demo` | content_moderator | `DemoPass123!` |
| `acc_mgr_demo` | account_manager | `DemoPass123!` |
| `client_demo` | client | `DemoPass123!` |
| `tech_demo` | technician | `DemoPass123!` |
| `dealership_demo` | dealership | `DemoPass123!` |

Seed with: `python manage.py seed_demo_data`

---

## Key Endpoint Groups

| Group | Base Path | Key Endpoints |
|---|---|---|
| Health | `/api/health/` | `live/`, `ready/`, `deep/` |
| Auth | `/api/auth/` | register, login, refresh, logout, verify-email, resend-otp, forgot-password, password-reset-confirm |
| Accounts | `/api/accounts/me/` | GET/PATCH/PUT current user |
| Categories | `/api/categories/` | List, detail with skills; `/skills/`, `/sub-skills/` |
| Technicians | `/api/technicians/` | List (filterable), detail, me, skills, images, availability, ratings |
| Clients | `/api/clients/me/` | GET/PATCH client profile |
| Contracts | `/api/contracts/` | CRUD, accept, cancel, stages (list/detail/submit/approve), extensions |
| Wallet | `/api/wallet/` | me, transactions, withdrawals, payment-intents, fee-config, contract-breakdown |
| Reviews | `/api/reviews/` | List (by technician), create, detail, respond, helpful, report, moderate/* |
| Notifications | `/api/notifications/` | List, detail, unread-count, mark-read, mark-unread, mark-all-read, activity |
| Dealership | `/api/dealership/` | Summary, recharge, cashout, confirm, settlements, guarantees |
| Admin | `/api/admin/` | Dashboard summary, users, technicians, contracts, reviews, finance |

Full route list: See `docs/API_ROUTES_GENERATED.md` (102 routes).

---

## Upload / Media Rules

| Mode | Storage | URL Type |
|---|---|---|
| Development | Local `media/` directory | Direct `http://.../media/...` |
| Production | S3-compatible bucket | Presigned URLs (signed, expiring) |

- **Max upload size:** 20 MB (configurable via Nginx/client_max_body_size)
- **Supported types:** Images (JPEG, PNG, WebP), documents (PDF)
- **Profile images:** Stored at `media/users/avatars/`
- **Portfolio images:** Stored at `media/technician_images/`
- **S3 mode:** Set `USE_S3_MEDIA=True` with bucket credentials
- **Signed URL expiry:** 15 minutes (configurable via `S3_QUERYSTRING_EXPIRE`)

---

## Dealership Mobile Workflow Summary

1. **Dealership Summary** — `GET /api/dealership/summary/` — balance, limits, exposure
2. **Lookup Client** — `GET /api/dealership/clients/lookup/?phone=<phone>` — find client by phone
3. **Preview Recharge** — `POST /api/dealership/recharge/preview/` — calculate fees
4. **Create Recharge** — `POST /api/dealership/recharge/` — fund client wallet
5. **Preview Cash-Out** — `POST /api/dealership/cashout/preview/` — calculate cash-out amount
6. **Create Cash-Out** — `POST /api/dealership/cashout/` — generates confirmation code
7. **Confirm Cash-Out** — `POST /api/dealership/cashout/<id>/confirm/` — confirm with code
8. **View Settlements** — `GET /api/dealership/settlements/` — settlement history

---

## Notification / WebSocket Workflow

1. Connect to `ws://<host>:8000/ws/notifications/?token=<access_token>`
2. Receive initial payload with `unread_count`
3. Listen for events:
   - `notification.created` — new notification
   - `notification.read` — notification was read
   - `unread_count.updated` — badge count changed
4. Poll `GET /api/notifications/unread-count/` as fallback
5. Mark read via `POST /api/notifications/<id>/mark-read/`
6. Mark all read via `POST /api/notifications/mark-all-read/`

---

## Rate-Limit Notes

| Scope | Rate Limit |
|---|---|
| Auth login | 5/min (per IP) |
| Auth registration | 3/min (per IP) |
| Wallet finance | 30/min |
| Dealership finance | 30/min |
| Reviews | 60/min |
| Notifications | 120/min |
| Schema/docs | 20/min |
| Default (other) | 120/min |

Rate limits use `DEFAULT_THROTTLE_RATES` in settings. Exceeding returns `429 Too Many Requests`.

---

## Known Limitations

- **No real payment gateway** — Dealerships handle financial flows. No Stripe/PayPal integration.
- **No chat system** — Communication uses contract stages and notifications.
- **S3 migration** — Switching from local to S3 storage requires manual file transfer.
- **WebSocket event loss** — If client disconnects, real-time events are lost (notification still in DB).
- **Schema warnings** — OpenAPI schema has cosmetic warnings/errors from views without declared serializers.
- **Django admin** — `/admin/` is accessible (not hardened beyond Django defaults).

---

## Recommended Frontend Implementation Order

| Step | Feature | Reason |
|---|---|---|
| 1 | Auth (login, register, OTP, token refresh) | Required for everything else |
| 2 | Public categories and technicians list | Core browsing experience |
| 3 | Client profile (view, edit) | First user-facing experience |
| 4 | Technician profile (view, edit, skills, images, availability) | Service provider onboarding |
| 5 | Contracts (create, list, stages, extensions) | Core transaction flow |
| 6 | Wallet (balance, transactions, withdrawals) | Financial operations |
| 7 | Dealership (recharge, cash-out, confirm, settlements) | Financial agent flow |
| 8 | Notifications + WebSocket | Real-time engagement |
| 9 | Admin dashboard (users, technicians, contracts, reviews, finance) | Platform operations |
| 10 | Reviews (create, respond, report) | Trust after contract completion |
| 11 | Media uploads (profile images, portfolio) | Polish and completeness |

---

## Quick Reference

```bash
# Health check (no auth)
curl http://127.0.0.1:8000/api/health/

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "client_demo", "password": "DemoPass123!"}'

# Authenticated request
curl http://127.0.0.1:8000/api/accounts/me/ \
  -H "Authorization: Bearer <access_token>"
```
