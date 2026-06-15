# Backend Team Instructions (Tiqani API — Monolith Django, Multi-App)

These instructions are the baseline for the backend team to start implementation as a **single Django project** with **multiple Django apps**, aligned with the existing project README scope (excluding chat). fileciteturn0file0

---

## 0) Ground Rules
- **No chat system** (no `/api/chat/`, no WebSocket chat features, no chat models/consumers/routes).
- Keep the backend **REST-first** (clean DRF APIs).
- Keep apps **modular** with clear boundaries, but within one Django project (monolith).
- Do not hardcode secrets. Use env vars.
- Ship working endpoints early, then iterate.

---

## 1) Expected Output from the Team
By the end of the first implementation cycle, you should have:
1. A working Django REST API with:
   - Accounts/auth + profiles
   - Categories
   - Contracts
   - Payments (Stripe)
   - Ratings/Reviews
   - Dealership
   - Notifications
2. Postman/Insomnia collection OR OpenAPI/Swagger working.
3. Automated tests for core flows.
4. Minimal production readiness: settings split, env-based config, logging.

---

## 2) Project Structure (Recommended)
Monorepo layout:

- `config/` (or `tiqani/`)  
  - `settings/`
    - `base.py`
    - `dev.py`
    - `prod.py`
  - `urls.py`
  - `asgi.py` (only if needed for non-chat async features)
  - `wsgi.py`
- `apps/`
  - `accounts/`
  - `category/`
  - `contract/`
  - `payment/`
  - `ratereview/`
  - `dealership/`
  - `notification/`
- `common/`
  - `permissions.py`, `pagination.py`, `mixins.py`, `exceptions.py`, `utils.py`
- `requirements/`
  - `base.txt`, `dev.txt`, `prod.txt` (optional but preferred)

If the repo already exists with another structure, do not fight it—apply the same principles in-place.

---

## 3) Environment & Dependencies

### 3.1 Python / Django
- Python 3.10+ (3.11 preferred)
- Django 4.x / DRF latest stable compatible

### 3.2 Required packages
- `djangorestframework`
- `djangorestframework-simplejwt`
- `python-decouple` (or `django-environ`)
- `drf-spectacular` (or `drf-yasg`) for API docs
- `stripe`
- `django-filter`
- `pytest` + `pytest-django` (or Django TestCase, but pytest preferred)

### 3.3 .env variables (minimum)
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` (if using Postgres in prod)
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `JWT_ACCESS_LIFETIME_MIN` (optional)
- `JWT_REFRESH_LIFETIME_DAYS` (optional)
- `DEFAULT_FROM_EMAIL` (if email later)

---

## 4) Data Model Plan (High-Level)

### 4.1 Accounts app
**Goal:** authentication + profiles + roles.

**Models**
- `User` (use Django default User unless you must extend; prefer Profile approach)
- `UserProfile`
  - `user` (OneToOne)
  - `role` (choices: client, freelancer, admin, dealership, etc.)
  - `phone`, `avatar`, `bio`, `location` (only what you need now)
  - `is_active` (if needed)

**Auth**
- JWT (SimpleJWT):
  - `POST /api/accounts/register/`
  - `POST /api/accounts/login/`
  - `POST /api/accounts/token/refresh/`
  - `GET /api/accounts/me/`
  - `PATCH /api/accounts/me/`

**Permissions**
- Default: authenticated required for user-owned resources
- Admin-only endpoints gated by `IsAdminUser` or custom role permission.

---

### 4.2 Category app
**Goal:** organize services.

**Models**
- `Category`
  - `name`, `slug`, `description`
  - `parent` (nullable FK to self) for hierarchy

**Endpoints**
- `GET /api/category/`
- `POST /api/category/` (admin/manager)
- `GET /api/category/{id}/`
- `PATCH /api/category/{id}/` (admin/manager)
- `DELETE /api/category/{id}/` (admin/manager)

---

### 4.3 Contract app
**Goal:** agreements between client and freelancer.

**Models**
- `Contract`
  - `client` (FK User)
  - `provider` (FK User)
  - `title`, `description`
  - `price`, `currency`
  - `status` (draft/pending/active/completed/canceled/disputed)
  - `start_at`, `end_at`
  - audit: `created_at`, `updated_at`

**Endpoints**
- `POST /api/contract/`
- `GET /api/contract/` (filtered by requesting user)
- `GET /api/contract/{id}/`
- Status transitions endpoint:
  - `POST /api/contract/{id}/action/` with action (accept, start, complete, cancel)
  - Validate allowed transitions server-side.

---

### 4.4 Payment app (Stripe)
**Goal:** charge and track payments for contracts.

**Models**
- `PaymentIntentRecord` (or `Payment`)
  - `contract`
  - `stripe_payment_intent_id`
  - `amount`, `currency`
  - `status` (created/processing/succeeded/failed/refunded)
  - `created_at`

**Flow (recommended)**
1. Client creates/initiates payment:
   - `POST /api/payment/create-intent/` -> returns `client_secret`
2. Frontend confirms payment with Stripe
3. Stripe webhook updates status:
   - `POST /api/payment/webhook/`

**Important**
- Webhook signature verification is mandatory (`STRIPE_WEBHOOK_SECRET`).
- Do not trust client-side payment success without webhook confirmation.

---

### 4.5 RateReview app
**Goal:** review completed contracts.

**Models**
- `Review`
  - `contract` (OneToOne or FK with unique constraint per reviewer)
  - `reviewer` (FK User)
  - `reviewed_user` (FK User)
  - `rating` (0–5)
  - `comment` (text)
  - `created_at`, `updated_at`
- Optional: store `avg_rating` computed on-demand or via signals.

**Rules**
- Only allow reviews when contract is `completed`.
- Prevent duplicate reviews for same contract by same reviewer.

---

### 4.6 Dealership app
**Goal:** allow intermediary accounts.

**Models**
- `DealerProfile`
  - `user` (OneToOne)
  - `company_name`, `license_no` (if needed)
- `DealerAssignment`
  - `dealer` (FK DealerProfile or User)
  - `provider` (FK User)
  - `status` (active/inactive)
  - timestamps

**Endpoints**
- CRUD for dealer profile (admin or owner)
- Assign/unassign providers

---

### 4.7 Notification app
**Goal:** persistent notifications.

**Models**
- `Notification`
  - `user` (FK)
  - `title`, `message`
  - `type` (contract/payment/review/system)
  - `is_read` (bool)
  - timestamps

**Endpoints**
- `GET /api/notification/`
- `PATCH /api/notification/{id}/` (mark read)
- `POST /api/notification/` (admin/system internal use)
- Optional bulk:
  - `POST /api/notification/mark-all-read/`

---

## 5) API Standards
- Use **RESTful** endpoints.
- Use consistent response envelopes only if the project already does; otherwise return DRF standard structures.
- Validation errors must be meaningful.
- Use pagination on list endpoints.
- Add filtering (django-filter) for list endpoints:
  - contracts by status/date
  - reviews by reviewed_user
  - notifications by is_read

---

## 6) Permissions & Ownership Rules (Must-Have)
- Users can only view/modify:
  - their profile
  - their contracts (as client or provider)
  - their notifications
- Reviews:
  - only reviewer can create/edit (if you allow edits; simplest: no edits after creation)
- Admins can manage categories and moderate abusive content (optional).

Implement reusable permissions in `common/permissions.py`:
- `IsOwner`
- `IsParticipant` (contract participant)
- `HasRole(roles=[...])`

---

## 7) Database Strategy
- Dev: SQLite is fine (existing repo includes it). fileciteturn0file0
- Prod: PostgreSQL recommended.
- Use migrations properly. No manual DB edits.

---

## 8) Logging, Errors, and Observability
- Configure structured logging at least by settings environment.
- Log:
  - auth failures
  - contract status transitions
  - stripe webhook events + signature verification outcome
- Return sane error messages; don’t leak secrets.

---

## 9) Testing Requirements (Minimum)
Write tests for:
1. Auth: register/login/refresh + access protected endpoints
2. Contract lifecycle transitions + permission checks
3. Payment intent creation (mock Stripe) + webhook handling (signature verification path)
4. Review creation rules (only completed contracts; one per contract)
5. Notification list/mark-read

Use factories/fixtures to avoid repetitive setup.

---

## 10) Delivery Workflow (Branching & PR)
- Branch naming:
  - `feature/<app>-<short-desc>`
  - `fix/<app>-<short-desc>`
- Every PR must include:
  - What changed
  - Endpoints added/changed
  - Migration notes
  - Test evidence (command + result)
- Run checks in CI (even basic):
  - `python manage.py check`
  - `pytest` or `python manage.py test`
  - `ruff/flake8` + `black` (recommended)

---

## 11) Milestone Plan (Practical Order)

### Milestone 1 — Foundation
- Settings split + env loading
- DRF + JWT auth
- Basic project skeleton + app scaffolding
- Swagger/OpenAPI

### Milestone 2 — Core Business
- Category
- Contract
- Basic Notification creation triggered by contract events (simple signals or service layer)

### Milestone 3 — Money + Trust
- Stripe payment intent + webhook
- Reviews & rating

### Milestone 4 — Dealership
- Dealer profile + provider assignment rules

### Milestone 5 — Hardening
- Permissions audits
- Performance basics (query optimization, select_related)
- More tests
- Production config notes

---

## 12) Notes About Django Channels
You can keep `asgi.py` and Channels installed only if you need async elsewhere, but **do not implement chat**. If nothing else needs Channels, remove it to simplify.

---

## 13) Definition of Done
A feature is done when:
- Endpoint works per spec
- Permission enforced
- Tests exist
- API docs updated
- No chat endpoints or chat code introduced

---

## Appendix A — Endpoint Map (No Chat)
- `/api/accounts/`
- `/api/category/`
- `/api/contract/`
- `/api/payment/`
- `/api/ratereview/`
- `/api/dealership/`
- `/api/notification/`

---

If you want, I can also generate a **clean Django app skeleton checklist** (files to create per app) and a **standard serializer/viewset pattern** to keep code consistent across the team.
