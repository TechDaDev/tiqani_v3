# tiqani_v3 — Backend API

Django REST Framework backend for the Tiqani platform — a service marketplace connecting clients with technicians.

## Tech Stack

- **Framework:** Django 5.2 + Django REST Framework
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT (SimpleJWT)
- **Server:** Gunicorn + WhiteNoise
- **Python:** 3.12+
- **Container:** Docker / Docker Compose

## Current Backend Features

- User registration, JWT authentication, OTP verification, password reset
- Client & technician profiles with skill management
- Service categories, skills, and sub-skills
- Contract lifecycle (draft → proposal → acceptance → stages → completion)
- Wallet system with balance, transactions, withdrawals, and escrow
- Platform fee engine (automatic fee calculation per contract)
- Payment intent preparation (funding, release, refund)
- Post-contract rating and review system (with verification and moderation)
- Notification system (per-user notifications + admin activity feed)
- Admin dashboard with user, technician, contract, review, and finance management
- Role-based admin access (system_admin, account_manager, finance_admin, content_moderator)
- Security hardening: object-level permissions, unsafe field protection, rate limiting, audit trails

## Quick Start

### Local (venv)

```bash
# Clone & enter
cd tiqani_v3

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run migrations
.venv/bin/python manage.py migrate

# Seed platform fees
.venv/bin/python manage.py seed_platform_fees

# Start server
.venv/bin/python manage.py runserver
```

### Docker (development)

```bash
cp .env.example .env
docker compose up --build
```

### Docker (production-like)

```bash
cp .env.production.example .env
# Edit .env with real values
docker compose -f docker-compose.prod.yml up --build -d
```

## Environment Files

| File | Purpose |
|---|---|
| `.env.example` | Development environment template |
| `.env.production.example` | Production environment template |
| `.env` | Actual environment (gitignored) |

## Important Commands

| Command | Description |
|---|---|
| `python manage.py migrate` | Apply pending migrations |
| `python manage.py makemigrations --check --dry-run` | Verify no pending migrations |
| `python manage.py check` | Run Django system checks |
| `python manage.py test --verbosity=1` | Run full test suite |
| `python manage.py seed_platform_fees` | Seed default platform fee config (idempotent) |
| `python manage.py check_deployment_ready` | Deployment readiness check |
| `python manage.py check_media_storage` | Check media storage configuration |
| `python manage.py final_backend_qa` | Run final QA checklist |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py collectstatic --noinput` | Collect static files for production |
| `gunicorn tiqani_v3.wsgi:application --bind 0.0.0.0:8000` | Start production server |

## API Route Groups

| Group | Base Path | Auth |
|---|---|---|
| Health | `GET /api/health/` | No |
| Auth | `/api/auth/` | Mixed |
| Accounts | `/api/accounts/` | Yes |
| Categories | `/api/categories/` | Mixed |
| Technicians | `/api/technicians/` | Mixed |
| Clients | `/api/clients/` | Yes |
| Contracts | `/api/contracts/` | Yes |
| Wallet | `/api/wallet/` | Yes |
| Reviews | `/api/reviews/` | Mixed |
| Notifications | `/api/notifications/` | Yes |
| Admin | `/api/admin/` | Admin |
| Dealership | `/api/dealership/` | Dealership |

See `docs/API_OVERVIEW.md` for detailed route documentation.

## Project Structure

```
tiqani_v3/
├── tiqani_v3/                    # Project config
│   ├── settings/
│   │   ├── base.py               # Shared settings (all environments)
│   │   ├── dev.py                # Development overrides
│   │   ├── prod.py               # Production overrides (secure defaults)
│   │   └── test.py               # Test settings (high throttles)
│   ├── urls.py                   # Root URL configuration
│   ├── views.py                  # Health check endpoint
│   ├── wsgi.py                   # WSGI entry point
│   └── asgi.py                   # ASGI entry point
├── accounts/                     # User auth, profiles, roles
├── category/                     # Service categories & skills
├── contract/                     # Contract lifecycle
├── ratereview/                   # Ratings & reviews
├── wallet/                       # Wallet, transactions, fees
├── notification/                 # Notifications & activity feed
├── dashboard/                    # Admin dashboard APIs
├── postman/                      # Postman collections
├── scripts/                      # Utility scripts (entrypoint)
├── docs/                         # Documentation
├── .github/workflows/            # CI pipeline
├── Dockerfile                    # Production container image
├── docker-compose.yml            # Dev compose (Postgres + Redis + Django)
├── docker-compose.prod.yml       # Production-like compose
├── requirements.txt
└── .env.example
```

## Settings Modules

| Module | Environment | Usage |
|---|---|---|
| `tiqani_v3.settings.dev` | Dev | `python manage.py runserver` (default) |
| `tiqani_v3.settings.prod` | Prod | Gunicorn / production WSGI |
| `tiqani_v3.settings.test` | CI | Test suite (high throttle limits) |

Override via `DJANGO_SETTINGS_MODULE` environment variable.

## Seed Demo Data

```bash
.venv/bin/python manage.py seed_demo_data
```

Creates 7 demo users with different roles, categories and skills, 3 demo contracts, a verified review, and demo notifications. Idempotent — safe to run multiple times.

## Final QA Check

```bash
.venv/bin/python manage.py final_backend_qa
```

Runs a quick deployment readiness checklist on the console.

## Frontend Integration

See `docs/FRONTEND_HANDOFF.md` for:
- Auth flow (login, register, token refresh)
- Role model and admin sub-roles
- Frontend route guards by role
- API response patterns and error codes
- Demo accounts table with credentials
- Known limitations (no chat, no real payments, no WebSockets)

## Postman

Complete collection at `postman/Tiqani_v3_Complete_Backend.postman_collection.json` — covers all API groups with variable-based token management.

See `docs/POSTMAN.md` for import and usage guide.

## Deployment

See:

- `docs/DEPLOYMENT.md` — Full deployment guide (venv, Docker, production)
- `docs/PRODUCTION_CHECKLIST.md` — Pre-deployment verification checklist
- `docs/QA_CHECKLIST.md` — Comprehensive QA testing checklist
- `docs/RELEASE_NOTES_PHASE_1_TO_10.md` — Full release history
- `docs/API_OVERVIEW.md` — Complete API route documentation
- `docs/MAINTENANCE.md` — Backup, restore, and maintenance procedures
- `docs/POSTMAN.md` — Postman collection import and usage guide
