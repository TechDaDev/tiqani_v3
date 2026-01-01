# Accounts Authentication Documentation

**Last Updated:** December 31, 2025

This document outlines all authentication and account-related API endpoints, request/response formats, admin panel configuration, and features implemented in the `accounts` app.

---

## Table of Contents

1. [Registration](#registration)
2. [Email Verification](#email-verification)
3. [Login](#login)
4. [Refresh Token](#refresh-token)
5. [Logout](#logout)
6. [Forgot Password](#forgot-password)
7. [Password Reset Confirm](#password-reset-confirm)
8. [Public Technician List](#public-technician-list)
9. [Technician-Specific Endpoints](#technician-specific-endpoints)
10. [Client-Specific Endpoints](#client-specific-endpoints)
11. [Profile Completion Tracking](#profile-completion-tracking)
12. [Admin Panel](#admin-panel)
13. [Error Handling](#error-handling)
14. [Rate Limiting](#rate-limiting)
15. [Authentication](#authentication)
16. [Future Features](#future-features)

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
  "userdata": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "role": "technician",
    "full_name": "John Doe",
    "profile_image": "/media/Profile/a1b2c3d4.jpg",
    "job_title": "Senior HVAC Technician",
    "is_available": true,
    "rating": 4.85,
    "total_reviews": 0
  }
}
```

### Error Responses

**Invalid Credentials (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials.",
  "attempts_remaining": 3
}
```

**Too Many Attempts (429 Too Many Requests):**
```json
{
  "detail": "Too many login attempts. Please try again later.",
  "remaining_timeout": 298
}
```

**Inactive Account (403 Forbidden):**
```json
{
  "detail": "Account is inactive. Please verify your email."
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

---

---

## Public Technician List

### Endpoint
```
GET /api/auth/technician/list/
```

**Authentication:** Optional (behavior changes based on user role)

### Access Control & Filtering

| User Type | Can Access | Sees Approved? | Sees Complete? | Can See Incomplete? | Can See Unapproved? |
|-----------|-----------|---|---|---|---|
| **Anonymous** | ✅ Yes | ✅ Only approved | ✅ Only complete | ❌ No | ❌ No |
| **Client** | ✅ Yes | ✅ Only approved | ✅ Only complete | ❌ No | ❌ No |
| **Admin** | ✅ Yes | ✅ All | ✅ All | ✅ **Yes** | ✅ **Yes** |
| **Technician** | ✅ Yes | ✅ Only approved | ✅ Only complete | ❌ No | ❌ No |

**Summary:**
- **Non-admin (Anonymous/Client/Technician):** See only approved (`approved=true`) and complete (`is_complete=true`) technicians
- **Admin:** See all technicians regardless of approval or completion status (no restrictions)

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `governorate` | string | Filter by governorate | Baghdad |
| `is_available` | boolean | Filter by availability status | true |
| `skill_id` | UUID | Filter by skill ID | 021621b2-0569-405e-9733-b050eced63e9 |
| `order_by` | string | Sort results | -rate (default), rate, -created_at |
| `page_size` | integer | Results per page | 20 (default) |
| `page` | integer | Page number | 1 |

### Success Response (200 OK)
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/auth/technician/list/?page=2",
  "previous": null,
  "results": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john_doe",
      "full_name": "John Doe",
      "governorate": "Baghdad",
      "profile_image": "http://localhost:8000/media/Profile/a1b2c3d4.jpg",
      "job_title": "Senior Web Developer",
      "about": "Experienced web developer specializing in full-stack...",
      "years_of_expertise": 5,
      "is_available": true,
      "rate": 4.85
    },
    {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "username": "jane_smith",
      "full_name": "Jane Smith",
      "governorate": "Baghdad",
      "profile_image": "http://localhost:8000/media/Profile/xyz.jpg",
      "job_title": "Data Scientist",
      "about": "Specialist in machine learning and data analysis...",
      "years_of_expertise": 7,
      "is_available": true,
      "rate": 4.92
    }
  ]
}
```

### Usage Examples

**List all approved technicians:**
```
GET /api/auth/technician/list/
```

**Filter by governorate:**
```
GET /api/auth/technician/list/?governorate=Baghdad
```

**Filter by availability and sort by rating:**
```
GET /api/auth/technician/list/?is_available=true&order_by=-rate
```

**Filter by skill and paginate:**
```
GET /api/auth/technician/list/?skill_id=021621b2-0569-405e-9733-b050eced63e9&page=1&page_size=10
```

### Filters Applied

**For Non-Admin Users (Anonymous/Client/Technician):**
- Only approved technicians (`approved=true`)
- Only complete profiles (`is_complete=true`)
- Inactive/incomplete/unapproved profiles are excluded

**For Admin Users:**
- All technicians are shown (no approval/completion restrictions)
- All filters still apply (governorate, is_available, skill_id, sorting)

---

## Technician-Specific Endpoints

### Overview
All technician endpoints require authentication and `role='technician'`. Base path: `/api/auth/technician/`.

### Quick Reference
- Profile: `GET|PATCH /api/auth/technician/profile/`
- Skills: `GET|PATCH /api/auth/technician/skills/`
- Images: `GET|POST /api/auth/technician/images/`, `PATCH|DELETE /api/auth/technician/images/{id}/`
- Availability: `GET|PATCH /api/auth/technician/availability/`
- Ratings: `GET /api/auth/technician/ratings/`

### Profile
- **GET /api/auth/technician/profile/** — returns technician profile. Example success:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "07812345678",
  "profile_image": "http://localhost:8000/media/Profile/a1b2c3d4.jpg",
  "job_title": "Web Developer",
  "about": "Experienced web developer...",
  "years_of_expertise": 5,
  "is_available": true,
  "approved": true,
  "is_complete": true,
  "rate": 4.85,
  "last_active": "2025-12-31T20:30:00Z",
  "skill_sets": {
    "id": "skill-set-uuid",
    "categories": ["category-uuid"],
    "categories_detail": [{"id": "category-uuid", "name": "Data"}],
    "skills": ["skill-uuid"],
    "skills_detail": [{"id": "skill-uuid", "name": "Databases"}],
    "sub_skills": ["sub-skill-uuid"],
    "sub_skills_detail": [{"id": "sub-skill-uuid", "name": "Database Administration (DBA)"}],
    "created_at": "2025-12-31T12:00:00Z"
  },
  "images": [
    {
      "id": "image-uuid-1",
      "image": "/media/technicians/uploads/img1.jpg",
      "description": "Portfolio website design"
    }
  ]
}
```
- **Field notes**: `job_title` is a short professional title shown to clients (e.g., "HVAC Specialist", "Full-Stack Developer").
- **PATCH /api/auth/technician/profile/** — JSON body (e.g. `job_title`, `about`, `years_of_expertise`). Example success:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "full_name": "John Doe",
  "job_title": "Senior Web Developer",
  "about": "Updated description...",
  "years_of_expertise": 6,
  "is_available": true,
  "rate": 4.85
}
```

### Skills
- **GET /api/auth/technician/skills/** — returns assigned categories/skills/sub_skills; if none, returns empty arrays with `detail` message.
- **PATCH /api/auth/technician/skills/** — JSON body:
```json
{
  "categories": ["category-uuid"],
  "skills": ["skill-uuid"],
  "sub_skills": ["sub-skill-uuid"]
}
```

### Images (Portfolio)
- **GET /api/auth/technician/images/** — list images with URLs and descriptions.
- **POST /api/auth/technician/images/** — multipart/form-data with `image` (required) and optional `description`.
- **PATCH /api/auth/technician/images/{id}/** — JSON body `{ "description": "..." }`.
- **DELETE /api/auth/technician/images/{id}/** — 204 No Content.

### Availability
- **GET /api/auth/technician/availability/** — returns `is_available`, `last_active`, `is_online`.
- **PATCH /api/auth/technician/availability/** — JSON body `{ "is_available": true|false }`.

### Ratings
- **GET /api/auth/technician/ratings/** — returns averages, totals, and optional recent reviews.

---

## Client-Specific Endpoints

### Overview
All client endpoints require authentication and `role='client'`. Base path: `/api/auth/client/`.

### Quick Reference
- Profile: `GET|PATCH /api/auth/client/profile/`

### Profile
- **GET /api/auth/client/profile/** — returns client profile with sensitive field masking. Example success:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jane_doe",
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone_number": "07812345678",
  "address": "Baghdad, Al-Mansour",
  "date_of_birth": "1995-03-15",
  "governorate": "Baghdad",
  "gender": "female",
  "profile_image": "http://localhost:8000/media/Profile/xyz.jpg",
  "age": 30,
  "is_complete": true,
  "wallet_id": "abc123xyz789",
  "balance": "150.00",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Sensitive Field Masking:**
- Fields visible **only to owner or admin**: `email`, `phone_number`, `address`, `date_of_birth`, `balance`
- Others viewing the profile will see `null` for these fields
- `governorate`, `gender`, `wallet_id` are visible to all

- **PATCH /api/auth/client/profile/** — Update user fields. Editable fields:
```json
{
  "phone_number": "07812345678",
  "address": "New address",
  "governorate": "Baghdad",
  "gender": "female",
  "date_of_birth": "1995-03-15",
  "profile_image": "<file_upload>"
}
```

**Notes:**
- Profile completion auto-updates after edit
- Age must be 18+ for completion status
- All edits update the CustomUser model

---

## Profile Completion Tracking

### Endpoint
```
GET /api/auth/profile/incomplete-fields/
```

**Authentication Required:** Yes (works for both client and technician roles)

### Success Response (200 OK)
```json
{
  "is_complete": false,
  "incomplete_fields": [
    "phone_number",
    "address",
    "profile_image"
  ],
  "total_required": 8,
  "completed_count": 5,
  "completion_percentage": 62.5
}
```

**Use Case:**
- Frontend can fetch this to show profile completion progress
- Display a progress bar or checklist of missing fields
- Works for both client and technician profiles

**Admin Panel:**
- Both ClientProfile and TechnicianProfile admins show incomplete fields count in list view
- Detail view shows bullet list of missing required fields
- Color-coded: green if complete, orange/red if incomplete

---

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
Rate limiting on login endpoint to prevent brute force attacks: **5 failed attempts per IP address per 5 minutes**.

### Implementation Details
- **Tracking Method:** IP-based using Django cache
- **Cache Key Format:** `login_attempts_{client_ip}`
- **IP Detection:** Supports `X-Forwarded-For` header for proxy/load balancer scenarios
- **Fallback:** Uses `REMOTE_ADDR` if `X-Forwarded-For` is not present

### Configuration
```python
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 5 * 60  # 300 seconds
```

### Behavior

#### Failed Login Response
When credentials are invalid, the response includes `attempts_remaining`:
```json
{
  "detail": "Invalid credentials.",
  "attempts_remaining": 4
}
```

#### Rate Limited Response
After 5 failed attempts, further requests are blocked with HTTP 429:
```json
{
  "detail": "Too many login attempts. Please try again later.",
  "remaining_timeout": 298
}
```

#### Successful Login
- Rate limit counter is **cleared** upon successful authentication
- User can attempt login again immediately after successful login

### Flow Example
```
Attempt 1 (failed) → HTTP 401, attempts_remaining: 4
Attempt 2 (failed) → HTTP 401, attempts_remaining: 3
Attempt 3 (failed) → HTTP 401, attempts_remaining: 2
Attempt 4 (failed) → HTTP 401, attempts_remaining: 1
Attempt 5 (failed) → HTTP 401, attempts_remaining: 0
Attempt 6 (failed) → HTTP 429, remaining_timeout: ~300
Attempt 7 (within 5 min) → HTTP 429, remaining_timeout: ~298
...
[After 5 minutes pass]
Attempt N (failed) → HTTP 401, attempts_remaining: 4 (counter reset)
```

**Note:** The counter tracks failed attempts per IP address, not per username. This means:
- Multiple users from the same IP share the same limit
- VPN/proxy users may be affected if others from same IP fail login attempts

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

## Admin Panel

### Overview
Comprehensive Django admin interface for managing users, profiles, wallets, OTP codes, and technician-related data.

### Registered Models

#### CustomUser
**Features:**
- Dynamic inline display based on user role (Technician/Client/Admin profiles)
- Profile completion status indicator
- Wallet and OTP verification history
- Advanced filtering by role, status, governorate, gender, creation date
- Search by username, email, name, phone number

**Display Columns:**
- Username, Email, Role, Full Name
- Phone Number, Governorate
- Account Status (Active/Inactive)
- Profile Status (Complete/Incomplete)
- Created Date

**Inlines:**
- Role-specific profile (TechnicianProfile/ClientProfile/AdminProfile)
- Wallet information
- OTP verification history

---

#### TechnicianProfile
**Features:**
- Approval/rejection actions (bulk operations)
- Availability status management
- Online/offline status indicator
- Profile completion tracking
- Rating display (auto-calculated from reviews)

**Display Columns:**
- User (Full Name & Username)
- Job Title, Availability, Approval Status
- Profile Completion, Rating, Years of Expertise
- Online Status, Created Date

**Bulk Actions:**
- Approve selected technicians
- Reject selected technicians
- Mark as available
- Mark as unavailable

**Inlines:**
- Technician Images (portfolio/work samples)

---

#### ClientProfile
**Features:**
- Profile completion status
- Age calculation and display (18+ validation indicator)
- User information quick access

**Display Columns:**
- User (Full Name & Username)
- Email, Phone
- Profile Completion Status
- Age (color-coded: green if 18+, red if under 18)
- Created Date

---

#### AdminProfile
**Features:**
- Admin role management (System Admin, Moderator, Finance)
- Staff status indicator
- Last login IP tracking

**Display Columns:**
- User (Full Name & Username)
- Admin Role
- Staff Status
- Last Login IP
- Created Date

---

#### Wallet
**Features:**
- Balance tracking
- Transaction count with direct link to transactions
- Transaction ID display

**Display Columns:**
- User (Full Name & Username)
- Balance
- Transaction ID
- Transaction Count (clickable)

---

#### WalletTransaction
**Features:**
- Transaction type filtering
- Multi-currency support (IQD and USD)
- Contract linkage
- Exchange rate tracking

**Display Columns:**
- Wallet (User & Transaction ID)
- Transaction Type
- Amount (IQD)
- Amount (USD)
- Related Contract (clickable link)
- Created Date

---

#### OTPVerification
**Features:**
- Validity status indicator (valid/expired/used)
- OTP code and verification ID display
- User linkage

**Display Columns:**
- User (Username & Email)
- OTP Code
- Used Status
- Valid Status (✓ Valid / ✗ Expired/Used)
- Created Date

---

#### TechnicianSkillSet
**Features:**
- Many-to-many relationship management for categories, skills, and sub-skills
- Filter horizontal widget for easy selection
- Count displays for each skill type

**Display Columns:**
- ID (truncated UUID)
- Technician (Full Name & Username)
- Category Count
- Skill Count
- Sub-Skill Count
- Created Date
2.0 (2025-12-31)
- ✅ Implemented IP-based rate limiting on login endpoint
- ✅ Added `attempts_remaining` counter to failed login responses
- ✅ Added `remaining_timeout` to rate limit (HTTP 429) responses
- ✅ Rate limit counter clears on successful authentication
- ✅ Support for `X-Forwarded-For` header (proxy/load balancer scenarios)

### v3.
---

#### TechnicianImage
**Features:**
- Image preview in list view
- Description management
- Linked to technician profile

**Display Columns:**
- ID (truncated UUID)
- Technician (Username)
- Image Preview (thumbnail)
- Description
- Created Date

---

### Admin Access
- Superusers have full access to all models
- AdminProfile users are automatically promoted to `is_staff=True`
- Access URL: `/admin/`

---

## Future Features

### Technician-Specific Endpoints (In Progress)
- [x] GET /api/technician/profile/ - Retrieve technician profile
- [x] PATCH /api/technician/profile/ - Update technician profile
- [x] GET /api/technician/skills/ - List assigned skills and categories
- [x] PATCH /api/technician/skills/ - Update skills and categories
- [x] GET /api/technician/images/ - List portfolio images
- [x] POST /api/technician/images/ - Upload portfolio image
- [x] DELETE /api/technician/images/{id}/ - Delete portfolio image
- [x] PATCH /api/technician/images/{id}/ - Update image description
- [x] GET /api/technician/availability/ - Get availability status
- [x] PATCH /api/technician/availability/ - Update availability status
- [x] GET /api/technician/ratings/ - Get ratings and reviews

### Other Future Features
- [x] Client Profile endpoints (GET/PATCH)
- [x] Profile Completion API endpoint
- [ ] OTP Resend endpoint
- [ ] User Profile endpoints (GET/PATCH)
- [ ] Social Authentication (Google, Facebook)
- [ ] CAPTCHA Integration
- [ ] Role-Based Access Control (RBAC) for API endpoints
- [ ] Admin dashboard analytics
- [ ] Email notification preferences

---

<!-- Changelog removed per request -->
