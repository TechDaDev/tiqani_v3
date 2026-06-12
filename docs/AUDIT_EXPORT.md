# Audit Export Guide

## Overview

The `export_audit_logs` management command exports security-relevant events
for compliance, forensics, or SIEM ingestion.

## Usage

```bash
# JSON output (default)
python manage.py export_audit_logs --days 30

# CSV output, redirected to file
python manage.py export_audit_logs --days 7 --format csv > audit_export.csv

# Pipe to jq for filtering
python manage.py export_audit_logs --days 90 | jq '.[] | select(.source == "user_login")'
```

## Data Sources

| Source | Description | Fields |
|---|---|---|
| `admin_log` | Django admin LogEntry | timestamp, user_id, action, content_type, change_message |
| `token_issued` | JWT token created | timestamp, user_id, token_id |
| `token_blacklisted` | JWT token revoked | timestamp, user_id, token_id |
| `user_login` | User last_login updated | timestamp, user_id, email |
| `user_registered` | New user registered | timestamp, user_id, email |

## Custom Security Events

Application code emits events via `log_security_event()`:

```python
from tiqani_v3.security_events import log_security_event

log_security_event(
    "auth.login.failed",
    user_id=user.pk,
    email=user.email,
    detail="Invalid password (3rd attempt)",
    request=request,
)
```

These appear in the `security` logger and Sentry breadcrumbs, but are NOT
(yet) stored in the database — export them from log aggregation tools.
