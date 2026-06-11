# QA Checklist — tiqani_v3

## Setup Checks
- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` copied from `.env.example`
- [ ] Database migrations run: `python manage.py migrate`
- [ ] Platform fees seeded: `python manage.py seed_platform_fees`
- [ ] Demo data seeded: `python manage.py seed_demo_data`
- [ ] Development server starts: `python manage.py runserver`

## DB Migration Checks
- [ ] `python manage.py check` — no issues
- [ ] `python manage.py makemigrations --check --dry-run` — no pending migrations
- [ ] `python manage.py migrate` — applies cleanly

## Seed Demo Data Check
- [ ] `python manage.py seed_demo_data` runs without error
- [ ] Running again reports existing data (idempotent)
- [ ] `admin_demo` user exists and can log in
- [ ] `client_demo` user exists and can log in
- [ ] `tech_demo` user exists and can log in
- [ ] Demo categories exist
- [ ] Demo contracts exist (draft, in_progress, completed)
- [ ] Demo review exists and is public
- [ ] Demo notifications exist

## Auth Checks
- [ ] Register new user returns 201
- [ ] Login with valid credentials returns 200 + tokens
- [ ] Login with invalid credentials returns 401
- [ ] Token refresh works
- [ ] OTP verification flow works
- [ ] Password reset flow works

## Role Guard Checks
- [ ] Unauthenticated requests return 401
- [ ] Normal users cannot access admin endpoints (403)
- [ ] Clients cannot access technician-only endpoints (403)
- [ ] Technicians cannot access client-only endpoints (403)
- [ ] System admin can access all admin endpoints
- [ ] Finance admin can access finance but not technician approval
- [ ] Content moderator can access reviews but not finance
- [ ] Account manager can access users/technicians but not finance

## Client Flow
- [ ] Client can view own profile
- [ ] Client can update own profile
- [ ] Client can create contract
- [ ] Client can accept contract stages
- [ ] Client can view own contracts only
- [ ] Client can view own wallet
- [ ] Client can create withdrawal requests
- [ ] Client can create review

## Technician Flow
- [ ] Technician can view own profile
- [ ] Technician can submit contract stages
- [ ] Technician can respond to reviews
- [ ] Technician can view own contracts only
- [ ] Pending technicians are not visible in public listing
- [ ] Technician can view own wallet

## Contract Flow
- [ ] Draft contracts created (status = 'draft')
- [ ] Contract proposal/acceptance works
- [ ] Stage submission and approval works
- [ ] Extension requests work
- [ ] Contract cancellation works
- [ ] Force cancel (admin) works
- [ ] Unrelated users cannot view contract details

## Wallet Flow
- [ ] Wallet shows correct balance
- [ ] Transaction history is accurate
- [ ] Withdrawal request can be created
- [ ] Withdrawal approval (admin) works
- [ ] Withdrawal rejection (admin) works
- [ ] Payment intents can be listed
- [ ] Platform earnings track correctly

## Review Flow
- [ ] Public reviews are visible without auth
- [ ] Hidden reviews return 404 for public
- [ ] Review creation works for completed contracts
- [ ] Review helpful mark works
- [ ] Review report works
- [ ] Moderator can hide/publish/verify/unverify

## Notification Flow
- [ ] Notifications listed for authenticated user only
- [ ] Unread count returns correct value
- [ ] Mark-read works
- [ ] Mark-all-read works
- [ ] Users cannot see other users' notifications

## Admin Flow
- [ ] Dashboard summary returns stats
- [ ] User list/search works
- [ ] User activate/deactivate works
- [ ] Technician list/pending/detail works
- [ ] Technician approve/reject works
- [ ] Contract list/detail/force-cancel works
- [ ] Review list/flagged/detail works
- [ ] Finance summary works
- [ ] Activity feed works
- [ ] Activity log created for key actions

## Security Checks
- [ ] Normal users cannot change own role
- [ ] Normal users cannot approve technicians
- [ ] Unrelated users cannot access contract/wallet/notification data
- [ ] Hidden reviews not public
- [ ] Public reviews don't expose emails
- [ ] Admin endpoints reject clients/technicians

## Production Config Checks
- [ ] `DEBUG=False` when using prod settings
- [ ] `SECRET_KEY` is unique and strong
- [ ] `ALLOWED_HOSTS` is set
- [ ] `DATABASE_URL` points to PostgreSQL
- [ ] `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` are set
- [ ] HTTPS is configured
- [ ] Secure cookies enabled
- [ ] Logging is configured

## Docker Checks
- [ ] Dockerfile builds without error
- [ ] `docker compose up --build` starts all services
- [ ] Health endpoint returns 200 from container
- [ ] Database migrations run on startup
- [ ] Static files are served

## CI Checks
- [ ] GitHub Actions CI workflow exists
- [ ] CI runs on push/PR to dev/main
- [ ] Tests pass in CI
- [ ] Migration check passes in CI
- [ ] System check passes in CI
