# Release Notes — tiqani_v3 (Phases 1–10)

## Phase 1 — Backend Foundation
Initial Django project setup with:
- Custom user model (CustomUser) with role-based authentication (client, technician, admin)
- JWT authentication via SimpleJWT (login, register, OTP, password reset)
- Client and technician profiles with completion tracking
- Category/skill tree structure
- Base models with UUID PKs, soft delete, and timestamps
- Health check endpoint

## Wallet Ownership Transfer
Fixed wallet model to use `OneToOneField` to `CustomUser` and switched managed tables with `db_table` aliases to match existing schema.

## Phase 2 — API Wiring & Base Serializers
- Complete serializer layer for all models
- API endpoint wiring for accounts, categories, technicians, and clients
- Pagination and filtering support

## Phase 3 — Contract Lifecycle
- Contract CRUD with draft → proposal → acceptance → stages → completion flow
- Stage-based milestone system (2–5 stages)
- Time extension requests with approval/rejection
- Contract cancel and force-cancel (admin)
- Service layer with business logic encapsulation

## Phase 4 — Wallet, Fees & Payment Preparation
- Wallet system with balance tracking and transactions
- Platform fee engine (technician commission + client service fee)
- Payment intents for funding, release, and refund flows
- Withdrawal request management with admin approval/rejection
- Contract payment breakdown calculation
- Platform earnings tracking

## Phase 5 — Reviews & Trust Workflow
- Post-contract rating and review system
- Multi-dimensional ratings (work quality, communication, timeliness, professionalism)
- Review verification (contract-linked + manual admin verification)
- Review helpful/report system
- Review moderation (hide, publish, verify, unverify)
- Auto-rating recalculation for technicians

## Phase 6 — Notifications & Activity Feed
- Per-user notification system with 20+ event types
- Notification read/unread tracking
- Mark-all-read functionality
- Admin activity feed (platform-wide audit trail)
- Notification service layer with bulk creation helpers

## Phase 7 — Admin Dashboard & Moderation APIs
- Aggregated dashboard summary (users, technicians, contracts, reviews, finance)
- User management (list, detail, activate/deactivate)
- Technician moderation (list, pending, approve, reject)
- Contract monitoring (list, detail, force-cancel)
- Review moderation (list, flagged, hide, publish, verify, unverify)
- Finance oversight (summary, earnings, payment intents, withdrawal management)
- Activity feed for admin audit

## Phase 8 — Security Hardening & Permissions
- Added `account_manager` role to AdminProfile
- Centralized role permission helpers (`accounts/role_helpers.py`)
- Refactored dashboard permissions to use central helpers
- Object-level permission hardening (wallet, notification, contract)
- Unsafe field update protection tests
- Audit log creation enforcement for key actions
- Added throttle scopes (login, password_reset, otp)
- Comprehensive security test suite (76 new tests)
- Sensitive data exposure prevention tests

**Latest commit:** `9f2270b chore(security): harden permissions audit and API consistency`

## Phase 9 — Deployment Readiness
- Multi-stage Dockerfile (Python 3.12-slim, non-root user, gunicorn)
- Docker Compose for development (PostgreSQL + Redis + Django)
- Production-like Docker Compose with static/media volumes
- Environment templates (`.env.example`, `.env.production.example`)
- GitHub Actions CI workflow (test, check, migration check with PostgreSQL)
- Entrypoint script for container startup
- Production settings hardening (proxy headers, SMTP, strict CORS/CSRF)
- Logging configuration
- Health endpoint with version field
- Comprehensive deployment documentation
- Production checklist, API overview, Postman guide, maintenance docs

**Latest commit:** `b5c73e4 chore(deploy): add Docker CI production docs and deployment readiness`

## Phase 10 — Final QA, Documentation & Frontend Handoff
- Demo seed data command (`seed_demo_data`) — creates 7 users, categories, contracts, reviews, notifications
- API route export command (`export_api_routes`) — generates route inventory
- Final backend QA command (`final_backend_qa`) — quick readiness checklist
- Frontend handoff guide (`docs/FRONTEND_HANDOFF.md`) — auth flow, role model, route guards, response patterns
- QA checklist (`docs/QA_CHECKLIST.md`) — comprehensive testing checklist
- Release notes (`docs/RELEASE_NOTES_PHASE_1_TO_10.md`)
- Complete Postman collection with all API groups
- Updated API overview with frontend integration order
- Deployment readiness tests
- Seed data tests
- Final QA command tests

**Latest commit:** This release

### Demo Credentials (run `python manage.py seed_demo_data`)

| Username | Password | Role |
|---|---|---|
| admin_demo | AdminDemo123! | system_admin |
| finance_demo | FinanceDemo123! | finance_admin |
| moderator_demo | ModeratorDemo123! | content_moderator |
| account_manager_demo | AccountManagerDemo123! | account_manager |
| client_demo | ClientDemo123! | client |
| tech_demo | TechDemo123! | technician |
| tech_pending_demo | TechPendingDemo123! | technician |

### Postman Collection
`postman/Tiqani_v3_Complete_Backend.postman_collection.json`

### Future Considerations (Phase 11+)
- Real payment gateway integration (Stripe, MyFatoorah)
- Real-time chat between clients and technicians
- Contract dispute resolution workflow
- WebSocket-based push notifications
- File/image CDN integration
- Mobile app development
- i18n / Arabic localization
