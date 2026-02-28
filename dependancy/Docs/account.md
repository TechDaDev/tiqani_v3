# Accounts App Documentation

Last updated: 2026-02-26

This document reflects the current implementation in `accounts/` and mounted routes in `tiqani_v3/urls.py`.

## Table of Contents

- [Base Route](#base-route)
- [Features](#features)
- [Authentication & Account Lifecycle](#authentication--account-lifecycle)
- [Technician Endpoints](#technician-endpoints)
- [Client Endpoints](#client-endpoints)
- [Core Data Model (Accounts)](#core-data-model-accounts)
- [Frontend Notes](#frontend-notes)
- [Frontend Implementation Guideline](#frontend-implementation-guideline)

## Base Route

All accounts endpoints are mounted under:

- `/api/auth/`

---

## Features

- JWT authentication flow (register, verify, login, refresh, logout)
- OTP verification and resend with rate limits
- Role-based profiles (`client`, `technician`, `admin`)
- Profile completion tracking by role
- Technician-specific APIs (skills, portfolio images, availability, ratings summary)
- Client-specific profile management APIs
- User wallet auto-created during registration (managed by the `wallet` app — see [wallet.md](wallet.md))

---

## Authentication & Account Lifecycle

### 1) Register
- **URL**: `POST /api/auth/register/`
- **Auth**: Not required
- **Behavior**:
  - Creates user with `is_active=False`
  - Auto-creates a `Wallet` (see [wallet.md](wallet.md))
  - Creates role profile (`ClientProfile` or `TechnicianProfile`)
  - Generates OTP and sends verification email

**Request body**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "role": "client|technician",

  "phone_number": "string (optional)",
  "governorate": "string (optional)",
  "address": "string (optional)",
  "gender": "male|female (optional)",
  "date_of_birth": "YYYY-MM-DD (optional)",
  "profile_image": "file (optional)",

  "job_title": "string (required if role=technician)",
  "about": "string (optional)",
  "years_of_expertise": "integer >= 0 (optional)",
  "identification_documents": "file (optional)",
  "github": "url (optional)",
  "linkedin": "url (optional)"
}
```

**Success (201)**
```json
{
  "detail": "Verification code sent to email.",
  "email": "user@example.com"
}
```

---

### 2) Verify Email (OTP)
- **URL**: `POST /api/auth/verify-email/`
- **Auth**: Not required
- **Behavior**:
  - Validates email + OTP
  - Marks OTP as used
  - Activates account (`is_active=True`)

**Request body**
```json
{
  "email": "string",
  "otp_code": "6-digit string"
}
```

**Success (200)**
```json
{
  "detail": "Account activated successfully.",
  "username": "string"
}
```

---

### 3) Resend OTP
- **URL**: `POST /api/auth/resend-otp/`
- **Auth**: Not required
- **Rate limiting (implemented)**:
  - Cooldown: 5 minutes between requests per email
  - Daily limit: 5 resends per 24h per email

**Request body**
```json
{
  "email": "string"
}
```

**Success (200)**
```json
{
  "detail": "A new verification code has been sent to your email.",
  "email": "user@example.com",
  "resends_remaining": 4
}
```

---

### 4) Login
- **URL**: `POST /api/auth/login/`
- **Auth**: Not required
- **Rate limiting (implemented)**:
  - 5 failed attempts per IP per 5 minutes

**Request body**
```json
{
  "username": "string",
  "password": "string"
}
```

**Success (200)**
```json
{
  "refresh": "jwt_refresh",
  "access": "jwt_access",
  "userdata": {
    "id": "uuid",
    "username": "string",
    "role": "client|technician|admin",
    "full_name": "string",
    "profile_image": "url|null",
    "job_title": "string (technician only)",
    "is_available": true,
    "rating": 0.0,
    "total_reviews": 0
  }
}
```

**Typical errors**
- `401`: invalid credentials (+ `attempts_remaining`)
- `403`: inactive account
- `429`: too many attempts (+ `remaining_timeout`)

---

### 5) Refresh Token
- **URL**: `POST /api/auth/refresh/`
- **Auth**: Not required

**Request body**
```json
{
  "refresh": "jwt_refresh"
}
```

**Success (200)**
```json
{
  "access": "jwt_access"
}
```

---

### 6) Logout
- **URL**: `POST /api/auth/logout/`
- **Auth**: Not required by permission class (token blacklisting still expects a valid refresh token)

**Request body**
```json
{
  "refresh": "jwt_refresh"
}
```

**Success (205)**: empty body

---

### 7) Password Reset Request
- **URL**: `POST /api/auth/password-reset/`
- **Auth**: Not required
- **Behavior**: always returns generic success message to avoid account enumeration

**Request body**
```json
{
  "email": "string"
}
```

**Success (200)**
```json
{
  "detail": "If an account exists, a reset code has been sent."
}
```

---

### 8) Password Reset Confirm
- **URL**: `POST /api/auth/password-reset-confirm/`
- **Auth**: Not required

**Request body**
```json
{
  "email": "string",
  "otp_code": "6-digit string",
  "new_password": "string"
}
```

**Success (200)**
```json
{
  "detail": "Password has been reset successfully."
}
```

---

## Technician Endpoints

All endpoints below require authenticated user role = `technician`.

### 1) Public Technician List
- **URL**: `GET /api/auth/technician/list/`
- **Auth**: Not required
- **Access behavior**:
  - Anonymous/client: only approved + complete profiles
  - Staff/admin: all technician profiles
- **Query params**:
  - `governorate`
  - `is_available` (`true/false`, `1/0`, `yes/no`)
  - `skill_id`
  - `order_by` (default `-rate`)
  - pagination: `page`, `page_size`

### 2) Technician Profile
- **URL**: `GET /api/auth/technician/profile/`
- **URL**: `PATCH /api/auth/technician/profile/`
- **Writable fields via serializer**: technician profile fields such as `job_title`, `about`, `years_of_expertise`, etc.

### 3) Technician Skills
- **URL**: `GET /api/auth/technician/skills/`
- **URL**: `PATCH /api/auth/technician/skills/`
- **Payload keys**: `categories`, `skills`, `sub_skills` (arrays of IDs)

### 4) Technician Images
- **URL**: `GET /api/auth/technician/images/`
- **URL**: `POST /api/auth/technician/images/`
- **POST payload**: `image` (file), `description` (optional)

### 5) Technician Image Detail
- **URL**: `PATCH /api/auth/technician/images/<uuid:image_id>/`
- **URL**: `DELETE /api/auth/technician/images/<uuid:image_id>/`

### 6) Availability
- **URL**: `GET /api/auth/technician/availability/`
- **URL**: `PATCH /api/auth/technician/availability/`
- **PATCH payload**: `{ "is_available": true|false }`

### 7) Ratings Summary
- **URL**: `GET /api/auth/technician/ratings/`
- **Current behavior**: returns average rating + placeholder review breakdown fields

---

## Client Endpoints

All endpoints below require authenticated user role = `client`.

### 1) Client Profile
- **URL**: `GET /api/auth/client/profile/`
- **URL**: `PATCH /api/auth/client/profile/`
- **PATCH updatable fields**:
  - `phone_number`
  - `address`
  - `governorate`
  - `gender`
  - `date_of_birth`
  - `profile_image`

### 2) Incomplete Fields (All Authenticated Roles)
- **URL**: `GET /api/auth/profile/incomplete-fields/`
- **Roles**: client + technician
- **Response shape**
```json
{
  "is_complete": false,
  "incomplete_fields": ["field_name"],
  "total_required": 0,
  "completed_count": 0,
  "completion_percentage": 0.0
}
```

---

## Core Data Model (Accounts)

### CustomUser
- Extends `AbstractUser`
- Role choices: `client`, `technician`, `admin`
- Profile fields include: `phone_number`, `governorate`, `address`, `gender`, `date_of_birth`, `profile_image`

### Profiles
- `ClientProfile` (one-to-one with user)
- `TechnicianProfile` (one-to-one with user)
- `AdminProfile` (one-to-one with user)

> Wallet models live in the `wallet` app. See [wallet.md](wallet.md) for the full financial domain model.

### OTPVerification
- 6-digit OTP
- Single-use (`is_used`)
- Validity window: 10 minutes

---

## Frontend Notes

- Use `multipart/form-data` when uploading files (`profile_image`, `identification_documents`, technician images).
- Use `Authorization: Bearer <access_token>` for protected endpoints.
- Do not use `/api/accounts/...` paths for this project version; use `/api/auth/...`.
- Role field is `role` (not `user_type`) in registration and user payload.

---

## Frontend Implementation Guideline

- Build auth as a staged flow: register → verify OTP → login.
- Handle rate-limit responses (`429`) explicitly for login and resend OTP UX.
- Use role-aware routing (`client` vs `technician` vs `admin`) after login.
- Use `multipart/form-data` only when file fields are present; otherwise send JSON.
- For profile completion UX, consume `/api/auth/profile/incomplete-fields/` and prompt only missing fields.
- Keep a single API base prefix for this app: `/api/auth/`.
