# Frontend Handoff Guide — tiqani_v3

## Backend Base URL

Development: `http://127.0.0.1:8000`
Production: `https://your-domain.com`

All API paths are prefixed with `/api/`.

---

## Auth Flow

### 1. Register
Creates a new user account and sends an OTP verification email.

```
POST /api/auth/register/
Content-Type: application/json

Request:
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "StrongPass1!",
  "password2": "StrongPass1!",
  "role": "client",              # "client" | "technician"
  "phone_number": "07701234567", # optional, 11 digits starting 075/077/078
  "governorate": "Baghdad",      # optional
  "address": "Address text",     # optional
  "gender": "male",              # optional, "male" | "female"
  "date_of_birth": "1995-01-15"  # optional, YYYY-MM-DD
}

Response 201:
{
  "detail": "Verification code sent to email.",
  "email": "john@example.com"
}
```

### 2. Verify email (OTP)
Activates the account using the OTP code sent via email. The `verification_id` is returned in the OTP email.

```
POST /api/auth/verify-email/
Content-Type: application/json

Request:
{
  "otp_code": "483921",
  "verification_id": "a1b2c3d4e5f6..."
}

Response 200:
{
  "detail": "Account activated successfully.",
  "username": "john_doe"
}

Response 400 (invalid/expired code):
{
  "otp_code": ["Invalid or expired verification code."]
}
```

### 3. Login
Returns JWT tokens plus user data. Rate limited to 5 failed attempts per IP per 5 minutes.

```
POST /api/auth/login/
Content-Type: application/json

Request:
{
  "username": "john_doe",
  "password": "StrongPass1!"
}

Response 200:
{
  "refresh": "eyJ0eXAiOiJKV1Qi...",
  "access": "eyJ0eXAiOiJKV1Qi...",
  "userdata": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "role": "client",
    "full_name": "",
    "profile_image": null
  }
}

# Technician userdata also includes:
#   "job_title": "Electrician",
#   "is_available": true,
#   "rating": 4.5,
#   "total_reviews": 12

Response 401 (invalid credentials):
{
  "detail": "Invalid credentials.",
  "attempts_remaining": 4
}

Response 403 (inactive account):
{
  "detail": "Account is inactive. Please verify your email."
}

Response 429 (rate limited):
{
  "detail": "Too many login attempts. Please try again later.",
  "remaining_timeout": 180
}
```

### 4. Refresh token
Issues a new access token using a valid refresh token.

```
POST /api/auth/refresh/
Content-Type: application/json

Request:
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}

Response 200:
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

### 5. Logout
Blacklists the refresh token so it cannot be reused.

```
POST /api/auth/logout/
Content-Type: application/json
Authorization: Bearer <access_token>    # optional

Request:
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}

Response 205: (no body)

Response 400:
{
  "detail": "Invalid token."
}
```

### 6. Resend OTP
Requests a new verification code. Rate limited: 5-minute cooldown, max 5 resends per 24 hours.

```
POST /api/auth/resend-otp/
Content-Type: application/json

Request:
{
  "email": "john@example.com"
}

Response 200:
{
  "detail": "A new verification code has been sent to your email.",
  "email": "john@example.com",
  "resends_remaining": 4
}

Response 429 (cooldown):
{
  "detail": "Please wait before requesting another code.",
  "remaining_seconds": 240,
  "retry_after": "4 minutes"
}
```

### 7. Forgot password
Sends a password reset OTP to the user's email.

```
POST /api/auth/password-reset/
Content-Type: application/json

Request:
{
  "email": "john@example.com"
}

Response 200:
{
  "detail": "If an account exists with this email, a password reset link will be sent."
}
```

### 8. Reset password
Confirms the password reset with a new password and OTP.

```
POST /api/auth/password-reset-confirm/
Content-Type: application/json

Request:
{
  "email": "john@example.com",
  "otp_code": "483921",
  "verification_id": "a1b2c3d4e5f6...",
  "password": "NewStrongPass1!",
  "password2": "NewStrongPass1!"
}

Response 200:
{
  "detail": "Password has been reset successfully."
}
```

### 9. Send Bearer token
All authenticated endpoints require the following header:

```
Authorization: Bearer <access_token>
```

Include this header in every request after login. The access token expires after 120 minutes. Use the refresh endpoint to obtain a new one without re-authenticating.

---

## API Endpoints by Group

### Accounts (`/api/accounts/`)

**GET /api/accounts/me/** — Get current user profile
```
Authorization: Bearer <access_token>

Response 200:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "role": "client",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone_number": "07701234567",
  "governorate": "Baghdad",
  "address": "123 Main St",
  "gender": "male",
  "date_of_birth": "1995-01-15",
  "age": 31,
  "profile_image": "http://127.0.0.1:8000/media/users/avatars/abc123.jpg",
  "is_profile_complete": true,
  "date_joined": "2026-01-10T12:00:00+03:00"
}
```

**PATCH /api/accounts/me/** — Update current user profile
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "first_name": "John",
  "last_name": "Updated",
  "phone_number": "07701234567",
  "governorate": "Basra",
  "address": "456 New St",
  "gender": "male",
  "date_of_birth": "1995-01-15"
}

Response 200: (same shape as GET)
```

---

### Clients (`/api/clients/`)

**GET /api/clients/me/** — Get client profile with wallet data
```
Authorization: Bearer <access_token>

Response 200:
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "full_name": "John Doe",
  "email": "jo***@example.com",
  "phone_number": "077****4567",
  "governorate": "Baghdad",
  "gender": "male",
  "profile_image": "http://127.0.0.1:8000/media/users/avatars/abc123.jpg",
  "age": 31,
  "is_complete": true,
  "wallet_id": "660e8400-e29b-41d4-a716-446655441111",
  "balance": "500000.00",
  "created_at": "2026-01-10T12:00:00+03:00"
}
```

**PATCH /api/clients/me/** — Update client profile (same editable fields as accounts/me)

---

### Technicians (`/api/technicians/`)

**GET /api/technicians/** — List public technicians (paginated)
```
Response 200:
{
  "count": 25,
  "next": "http://127.0.0.1:8000/api/technicians/?page=2",
  "previous": null,
  "results": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440001",
      "username": "tech_demo",
      "full_name": "Ahmed Ali",
      "governorate": "Baghdad",
      "profile_image": "http://127.0.0.1:8000/media/users/avatars/tech.jpg",
      "job_title": "Electrician",
      "about": "Expert electrician with 8+ years...",
      "years_of_expertise": 8,
      "is_available": true,
      "rate": "4.50"
    }
  ]
}

Filters: ?governorate=Baghdad&is_available=true&skill_id=<uuid>&order_by=-rate
```

**GET /api/technicians/<id>/** — Technician detail with skills and reviews
```
Response 200:
{
  "user_id": "550e8400-...",
  "username": "tech_demo",
  "full_name": "Ahmed Ali",
  "email": "te***@example.com",
  "phone_number": "077****4567",
  "governorate": "Baghdad",
  "profile_image": "...",
  "job_title": "Electrician",
  "about": "Expert electrician...",
  "years_of_expertise": 8,
  "is_available": true,
  "rate": "4.50",
  "skills": {
    "categories": [{"id": "...", "name": "Electrical"}],
    "skills": [{"id": "...", "name": "Wiring"}],
    "sub_skills": []
  },
  "portfolio_images": [
    {"id": "...", "image": "...", "description": "Work sample"}
  ],
  "is_online": true,
  "last_active": "2026-06-11T10:00:00+03:00"
}
```

**GET /api/technicians/me/** — Get own technician profile (technician only)
```
Authorization: Bearer <access_token>

Response 200: (same shape as detail above, plus private fields)
```

**PATCH /api/technicians/me/** — Update own technician profile
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "job_title": "Senior Electrician",
  "about": "Updated bio text",
  "years_of_expertise": 9
}

Response 200: (updated profile)
```

**GET|PUT /api/technicians/me/skills/** — Get/update own skill set
```
Authorization: Bearer <access_token>
Content-Type: application/json

Response 200:
{
  "categories": ["<category_uuid>"],
  "skills": ["<skill_uuid>"],
  "sub_skills": []
}

PUT Request:
{
  "categories": ["<category_uuid>"],
  "skills": ["<skill_uuid>"],
  "sub_skills": []
}
```

**POST /api/technicians/me/availability/** — Toggle availability
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "is_available": false
}

Response 200:
{
  "is_available": false
}
```

---

### Categories (`/api/categories/`)

**GET /api/categories/** — List all categories
```
Response 200:
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-...",
      "name": "Electrical",
      "description": "Electrical services",
      "image": null,
      "skills": [
        {"id": "...", "name": "Wiring"},
        {"id": "...", "name": "AC Repair"}
      ]
    }
  ]
}
```

**GET /api/categories/skills/** — List all skills
**GET /api/categories/sub-skills/** — List all sub-skills

---

### Contracts (`/api/contracts/`)

**GET /api/contracts/** — List user's contracts
```
Authorization: Bearer <access_token>

Response 200:
[
  {
    "id": "770e8400-...",
    "contract_reference": "#A1B2C3D4E5F6",
    "status": "in_progress",
    "client": {"id": "...", "username": "client_demo"},
    "technician": {"id": "...", "username": "tech_demo"},
    "work_description": "Fix electrical wiring",
    "agreed_amount": "75000.00",
    "stage_number": 2,
    "client_accepted": true,
    "technician_accepted": true,
    "created_at": "2026-06-01T10:00:00+03:00"
  }
]
```

**POST /api/contracts/** — Create draft contract (client only)
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "technician_id": "<technician_uuid>",
  "work_description": "Fix electrical wiring in kitchen",
  "agreed_amount": "75000.00",
  "stage_number": 2,
  "start_date": "2026-06-15",
  "duration_days": 7
}

Response 201: (contract detail)
```

**POST /api/contracts/<id>/accept/** — Accept contract (client or technician)
```
Authorization: Bearer <access_token>

Response 200:
{
  "status": "pending_acceptance",
  "client_accepted": true,
  "technician_accepted": false
}
```

**POST /api/contracts/<id>/cancel/** — Cancel contract
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "reason": "Changed requirements"
}

Response 200:
{
  "status": "canceled",
  "canceled_at": "..."
}
```

**GET /api/contracts/<id>/stages/** — List stages
```
Response 200:
[
  {
    "id": "880e8400-...",
    "stage_number": 1,
    "title": "Initial assessment",
    "amount": "37500.00",
    "status": "completed",
    "is_approved_by_client": true,
    "completed_at": "2026-06-08T15:00:00+03:00",
    "created_at": "2026-06-01T10:00:00+03:00"
  }
]
```

**POST /api/contracts/<id>/stages/<sid>/submit/** — Submit stage (technician only)
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "description": "Work completed for this stage",
  "attachment": null
}

Response 200: (updated stage)
```

**POST /api/contracts/<id>/stages/<sid>/approve/** — Approve stage (client only)
```
Authorization: Bearer <access_token>

Response 200:
{
  "is_approved_by_client": true
}
```

---

### Wallet (`/api/wallet/`)

**GET /api/wallet/me/** — Get own wallet + recent transactions
```
Authorization: Bearer <access_token>

Response 200:
{
  "balance": "500000.00",
  "transaction_id": "abc123...",
  "recent_transactions": [
    {
      "id": "990e8400-...",
      "transaction_type": "deposit",
      "amount": "100000.00",
      "description": "Wallet top-up",
      "created_at": "2026-06-10T12:00:00+03:00"
    }
  ]
}
```

**GET /api/wallet/transactions/** — List own transactions
```
Authorization: Bearer <access_token>

Filters: ?transaction_type=deposit&created_after=2026-01-01

Response 200: (array of transactions)
```

**GET /api/wallet/withdrawals/** — List withdrawal requests
**POST /api/wallet/withdrawals/** — Create withdrawal request
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "amount": "50000.00",
  "requested_method": "bank",
  "notes": "Monthly withdrawal"
}

Response 201:
{
  "id": "...",
  "amount": "50000.00",
  "status": "pending",
  "requested_method": "bank",
  "created_at": "..."
}
```

**GET /api/wallet/payment-intents/** — List payment intents
```
Authorization: Bearer <access_token>

Response 200: (array of payment intents)
```

---

### Reviews (`/api/reviews/`)

**GET /api/reviews/technician/<id>/** — Public reviews for a technician
```
Response 200:
{
  "count": 5,
  "results": [
    {
      "id": "aa0e8400-...",
      "reviewer": {"id": "...", "username": "client_demo"},
      "rating": 5,
      "title": "Excellent work!",
      "comment": "The technician completed all work on time.",
      "technician_response": "Thank you!",
      "is_verified": true,
      "created_at": "2026-06-05T12:00:00+03:00"
    }
  ]
}
```

**POST /api/reviews/** — Create review
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "contract_id": "<contract_uuid>",
  "technician_id": "<technician_uuid>",
  "rating": 5,
  "title": "Great service",
  "comment": "Very professional and on time."
}

Response 201: (created review)
```

**POST /api/reviews/<id>/helpful/** — Mark review as helpful
```
Authorization: Bearer <access_token>

Response 200:
{
  "helpful_count": 3
}
```

**POST /api/reviews/<id>/report/** — Report a review
```
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
  "reason": "Inappropriate content"
}

Response 201:
{
  "detail": "Review reported."
}
```

---

### Notifications (`/api/notifications/`)

**GET /api/notifications/** — List own notifications
```
Authorization: Bearer <access_token>

Response 200:
{
  "count": 10,
  "results": [
    {
      "id": "bb0e8400-...",
      "notification_type": "contract_completed",
      "title": "Contract Completed",
      "message": "Contract #A1B2C3 has been completed.",
      "is_read": false,
      "created_at": "2026-06-10T14:00:00+03:00"
    }
  ]
}

Filters: ?is_read=false&notification_type=contract_completed
```

**GET /api/notifications/unread-count/** — Unread count
```
Authorization: Bearer <access_token>

Response 200:
{
  "unread_count": 3
}
```

**POST /api/notifications/<id>/mark-read/** — Mark one as read
```
Authorization: Bearer <access_token>

Response 200:
{
  "status": "ok",
  "is_read": true
}
```

**POST /api/notifications/mark-all-read/** — Mark all as read
```
Authorization: Bearer <access_token>

Response 200:
{
  "status": "ok",
  "updated": 3
}
```

---

### Admin Dashboard (`/api/admin/`)

All admin endpoints require an admin role token and return 403 for non-admin users.

**GET /api/admin/dashboard/summary/** — Aggregated platform stats
```
Authorization: Bearer <admin_token>

Response 200:
{
  "users": {"total": 100, "clients": 60, "technicians": 35, "admins": 5, "active": 90, "inactive": 10},
  "technicians": {"total": 35, "approved": 30, "pending": 3, "available": 25},
  "contracts": {"total": 50, "draft": 5, "pending_acceptance": 3, "in_progress": 20, "completed": 18, "canceled": 4},
  "finance": {"total_contract_value": "...", "platform_earnings_pending": "...", "platform_earnings_earned": "...", "payment_intents_pending": 5, "withdrawals_pending": 2},
  "reviews": {"total": 40, "public": 35, "hidden": 5, "verified": 30, "flagged": 2},
  "notifications": {"total": 200, "unread": 45, "activity_logs": 150}
}
```

**GET /api/admin/users/** — List users (AccountManager+)
```
Authorization: Bearer <admin_token>

Search: ?search=john
Filters: ?role=client&is_active=true&governorate=Baghdad
```

**POST /api/admin/users/<id>/activate/** — Activate user (SystemAdmin)
**POST /api/admin/users/<id>/deactivate/** — Deactivate user (SystemAdmin)

**GET /api/admin/technicians/pending/** — Pending approvals (AccountManager+)
**POST /api/admin/technicians/<id>/approve/** — Approve technician (SystemAdmin)
**POST /api/admin/technicians/<id>/reject/** — Reject technician (SystemAdmin)

**GET /api/admin/finance/summary/** — Finance summary (FinanceAdmin+)
```
Authorization: Bearer <finance_token>

Response 200:
{
  "total_platform_earnings": "1500000.00",
  "pending_platform_earnings": "500000.00",
  "earned_platform_earnings": "1000000.00",
  "payment_intents_pending": 5,
  "payment_intents_paid": 10,
  "withdrawals_pending": 2,
  "withdrawals_approved": 8,
  "withdrawals_paid": 6,
  "total_wallet_balances": "5000000.00"
}
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
