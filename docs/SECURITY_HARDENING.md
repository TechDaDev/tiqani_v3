# Security Hardening

## Authentication

- JWT access lifetime remains 120 minutes.
- Refresh lifetime remains 7 days.
- Frontend stores tokens in HTTP-only cookies and forwards them only from server-side route handlers.
- Logout invalidates refresh tokens where backend supports blacklist behavior.

## Authorization

- Admin APIs require staff/admin permissions.
- Phase 12 admin state changes require a non-empty reason.
- User suspension/restoration and technician approval/suspension create audit events with previous and new state.
- Object ownership and IDOR checks remain enforced in domain services and API views.

## Headers

- Django production settings enable secure cookies, HSTS, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`, and proxy HTTPS support.
- Frontend config sets CSP, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and production-only HSTS.

## Rate Limits

- Existing scopes: `anon`, `user`, `login`, `password_reset`, `otp`, finance, review, notification, chat, attachment, schema.
- Phase 12 adds `admin_write`.
- Rates are environment-configurable.

## Uploads

- Validators enforce extensions, size limits, blocked executable/archive/script types, and MIME denylist.
- Profile images, category icons, documents, and proof files have separate limits.
- Antivirus scanning is deferred and must be added before accepting high-risk public attachments at scale.

## Logging

- Request IDs are attached to responses.
- Structured logging redacts passwords, tokens, cookies, authorization headers, secrets, and API keys.
- Audit events remain separate from application logs.
