# Accounts API (Auth & Profiles)

Reference for frontend engineers. All endpoints are under the `/` prefix.

## Auth Flow Overview
1. Register → user created inactive, OTP emailed.
2. Verify email → activates account, issues no token (login after verify).
3. Login → returns JWT pair (access/refresh) and user payload.
4. Refresh → exchange refresh for new access.
5. Logout → blacklist refresh token.
6. Password reset → request reset OTP → confirm with OTP and new password.

## Rate Limits
- Login: 5 failed attempts per IP per 5 minutes. Error: `429` with `remaining_timeout`.
- OTP resend: 5-minute cooldown and max 5 resends per 24h.
- Throttling (global DRF): 10/minute for anon and authenticated (configurable via env `THROTTLE_ANON`, `THROTTLE_USER`).

## Endpoints

### POST /api/auth/login/
- Body: `{ "username": str, "password": str }`
- Success 200: `{ "refresh": str, "access": str, "userdata": { id, username, role, full_name, profile_image, job_title?, is_available?, rating?, total_reviews? } }`
- Errors: `401 Invalid credentials` (includes attempts_remaining), `403 Account is inactive`, `429 Too many login attempts`.

### POST /api/auth/refresh/
- Body: `{ "refresh": str }`
- Success 200: `{ "access": str, "refresh": str }` (DRF simplejwt default shape).

### POST /api/auth/logout/
- Body: `{ "refresh": str }`
- Success 205 (empty body). Invalid token → `400` with `detail`.

### POST /api/auth/register/
- Body (role is required, technician requires `job_title`):
```
{
  "username": str,
  "email": str,
  "password": str,
  "first_name": str,
  "last_name": str,
  "role": "client" | "technician",
  "phone_number"?: str,
  "governorate"?: str,
  "address"?: str,
  "gender"?: "male"|"female",
  "date_of_birth"?: "YYYY-MM-DD",
  "profile_image"?: file,
  "job_title"?: str,                // technician only (required if role=technician)
  "about"?: str,
  "years_of_expertise"?: int >= 0,
  "identification_documents"?: file,
  "github"?: url,
  "linkedin"?: url
}
```
- Success 201: `{ "detail": "Verification code sent to email.", "email": str }`
- Validation errors: password mismatch, duplicate email/phone, missing `job_title` for technicians.

### POST /api/auth/verify-email/
- Body: `{ "email": str, "otp_code": str }`
- Success 200: `{ "detail": "Account activated successfully.", "username": str }`
- Errors: invalid/expired OTP, wrong email/OTP pairing.

### POST /api/auth/resend-otp/
- Body: `{ "email": str }`
- Success 200: `{ "detail": "A new verification code has been sent to your email.", "email": str, "resends_remaining": int }`
- Errors: `400` already verified, `429` cooldown or daily limit reached.

### POST /api/auth/password-reset/
- Body: `{ "email": str }`
- Success 200 always (does not leak existence). If user active, sends OTP.

### POST /api/auth/password-reset-confirm/
- Body: `{ "email": str, "otp_code": str, "new_password": str, "new_password_confirm": str }`
- Success 200: `{ "detail": "Password has been reset successfully." }`
- Errors: password mismatch, invalid/expired OTP, account must be active.

## Technician Endpoints (require JWT)
- GET /api/auth/technician/list/
- GET/PUT /api/auth/technician/profile/
- GET/PUT /api/auth/technician/skills/
- GET/POST /api/auth/technician/images/
- DELETE/PUT /api/auth/technician/images/<uuid:image_id>/
- POST /api/auth/technician/availability/
- GET /api/auth/technician/ratings/

## Client Endpoints (require JWT)
- GET/PUT /api/auth/client/profile/

## Profile Completion Helper
- GET /api/auth/profile/incomplete-fields/ → returns required-but-missing fields for the current user role.

## Validation Highlights
- Password strength enforced by Django validators.
- Unique: `email`, `phone_number` (when provided), `username`.
- Technicians must provide `job_title`; other tech fields optional but influence completeness.
- OTPs: 6-digit numeric, 10-minute validity, single-use.

## Business Rules
- New users are created inactive; OTP verification activates the account.
- Wallet auto-created for every new user.
- Technicians track `last_active` on login; rating fields are placeholders until reviews wire up.
- Login blocks inactive accounts until email verification succeeds.

## Payload Tips for Frontend
- Use `multipart/form-data` for registration when sending files (`profile_image`, `identification_documents`).
- Otherwise use `application/json`.
- Include `Authorization: Bearer <access>` for all authenticated endpoints.
