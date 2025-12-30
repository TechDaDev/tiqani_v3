# Accounts Authentication Documentation

**Last Updated:** December 30, 2025

This document outlines all authentication and account-related API endpoints, request/response formats, and features implemented in the `accounts` app.

---

## Table of Contents

1. [Registration](#registration)
2. [Email Verification](#email-verification)
3. [Login](#login)
4. [Refresh Token](#refresh-token)
5. [Logout](#logout)
6. [Forgot Password](#forgot-password)
7. [Password Reset Confirm](#password-reset-confirm)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Authentication](#authentication)
11. [Future Features](#future-features)

---

## Registration

### Endpoint
```
POST /api/auth/register/
```

### Request Body
```json
{
  "username": "string (required, unique)",
  "email": "string (required, unique, valid email)",
  "password": "string (required, min 8 chars, must contain uppercase, number, special char)",
  "password_confirm": "string (required, must match password)",
  "first_name": "string (required)",
  "last_name": "string (required)",
  "role": "string (required, one of: client, technician)"
}
```

### Success Response (201 Created)
```json
{
  "detail": "Registration successful. Please check your email for verification code.",
  "email": "john@example.com",
  "message": "An OTP has been sent to your email. Verify your email to activate your account."
}
```

---

## Email Verification

### Endpoint
```
POST /api/auth/verify-email/
```

### Request Body
```json
{
  "email": "string (required)",
  "otp_code": "string (required, 6 digits)"
}
```

### Success Response (200 OK)
```json
{
  "detail": "Email verified successfully. Your account is now active.",
  "username": "john_doe",
  "message": "You can now login with your credentials."
}
```

---

## Login

### Endpoint
```
POST /api/auth/login/
```

### Request Body
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

### Success Response (200 OK)
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "first_name": "John",
    "last_name": "Doe",
    "role": "technician",
    "profile_image": "/media/Profile/john_doe_a1b2c3d4.jpg"
  }
}
```

---

## Refresh Token

### Endpoint
```
POST /api/auth/refresh/
```

### Request Body
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Success Response (200 OK)
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Logout

### Endpoint
```
POST /api/auth/logout/
```

### Request Body
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Success Response (205 Reset Content)
```
(No body)
```

---

## Forgot Password

### Endpoint
```
POST /api/auth/password-reset/
```

### Request Body
```json
{
  "email": "string (required, registered email)"
}
```

### Success Response (200 OK)
```json
{
  "detail": "If an account exists with this email, you will receive a password reset code.",
  "email": "john@example.com",
  "message": "Check your email for the password reset code."
}
```

**Post-Request:**
- OTP code (6 digits) generated and sent to email
- OTP valid for 10 minutes
- Response is generic for security (doesn't reveal if email exists)

---

## Password Reset Confirm

### Endpoint
```
POST /api/auth/password-reset-confirm/
```

### Request Body
```json
{
  "email": "string (required)",
  "otp_code": "string (required, 6-digit code)",
  "new_password": "string (required, min 8 chars, uppercase, number, special char)",
  "new_password_confirm": "string (required, must match new_password)"
}
```

### Success Response (200 OK)
```json
{
  "detail": "Password reset successfully. You can now login with your new password.",
  "username": "john_doe",
  "message": "Your password has been updated."
}
```

**Post-Confirmation:**
- OTP marked as used and cannot be reused
- Password updated securely (hashed)
- User can immediately login with new password

---

## Error Handling

### Common HTTP Status Codes
| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created (new resource) |
| 205 | Success (No Content) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid credentials) |
| 403 | Forbidden (account disabled) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Error Response Format
```json
{
  "detail": "Error message",
  "field_name": ["Error detail 1", "Error detail 2"]
}
```

---

## Rate Limiting

### Overview
Rate limiting on login: max 5 failed attempts per IP per 5 minutes.

### Configuration
```python
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 5 * 60  # 300 seconds
```

**Example:**
```
Request 1-4 (failed) → attempts_remaining: 4, 3, 2, 1
Request 5 (failed) → BLOCKED for 5 minutes (429 Too Many Requests)
Request 6 (within 5 min) → remaining_timeout: ~298 seconds
```

---

## Authentication

### JWT Configuration
- **Access Token Lifetime:** 30 minutes
- **Refresh Token Lifetime:** 7 days
- **Token Blacklist:** Enabled for logout
- **Email Backend:** Console (dev), SMTP (production)
- **OTP Validity:** 10 minutes

### Using Tokens
```
Authorization: Bearer <access_token>
```

---

## Future Features

- [ ] OTP Resend endpoint
- [ ] User Profile endpoints
- [ ] Technician Profile endpoints
- [ ] Social Authentication (Google, Facebook)
- [ ] CAPTCHA Integration
- [ ] Role-Based Access Control (RBAC)

---

## Changelog

### v3.0.0 (2025-12-30)
- ✅ Password reset request endpoint
- ✅ Password reset confirmation endpoint
- ✅ OTP reuse for password reset
- ✅ Secure password hashing and validation

### v2.0.0 (2025-12-29)
- ✅ Registration with email verification
- ✅ OTP-based email verification
- ✅ Role-specific profile creation
- ✅ Account activation workflow

### v1.0.0 (2025-12-29)
- ✅ Login with rate limiting
- ✅ Refresh token endpoint
- ✅ Logout with token blacklist
- ✅ JWT authentication
