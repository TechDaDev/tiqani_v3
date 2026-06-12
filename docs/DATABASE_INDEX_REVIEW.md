# Database Index Review

## Indexes Added (Phase 16)

| Model | Fields | Purpose |
|---|---|---|
| `Notification` | `recipient`, `is_read`, `created_at` | Fast unread count queries per user |
| `WalletTransaction` | `wallet`, `created_at` | Transaction history lookup |
| `WalletTransaction` | `transaction_type`, `status`, `created_at` | Filtered transaction queries |
| `Contract` | `client`, `status` | Client contract listing by status |
| `Contract` | `technician`, `status` | Technician contract listing by status |
| `Contract` | `status`, `created_at` | Admin contract filtering/sorting |
| `DealershipClientRecharge` | `dealership`, `status`, `created_at` | Dealership recharge history |
| `DealershipClientRecharge` | `idempotency_key` | Idempotency check |
| `DealershipClientCashout` | `dealership`, `status`, `created_at` | Dealership cashout history |
| `DealershipClientCashout` | `code_expires_at`, `status` | Cash-out code expiry sweep |
| `DealershipCreditLedger` | `dealership`, `created_at` | Credit ledger audit trail |
| `DealershipCreditLedger` | `transaction_type`, `created_at` | Transaction-type filtering |
| `Review` | `technician`, `is_public`, `is_verified`, `created_at` | Public review queries |

## Why Each Matters

- **Notification**: The most frequently queried per-user table. Unread counts power the badge UI.
- **WalletTransaction**: Financial audit trail — every withdrawal, payment, and fee creates a row.
- **Contract**: The core business object — filtered by participant and status constantly.
- **DealershipClientRecharge/Cashout**: Financial agent operations — queried by dealership and status.
- **DealershipCreditLedger**: Immutable ledger — needs chronological querying by dealership.
- **Review**: Public profile display — filtered by technician + public + verified.

## Migration Safety

All indexes are created with `CREATE INDEX CONCURRENTLY`-compatible Django migrations.
No table locks are held for extended periods in PostgreSQL.

## Future Indexes to Consider

- `ActivityLog.action` + `created_at` — if activity log grows large
- `User.last_login` — if running inactive-user reports
- `Contract.contract_type` + `status` — if filtering by type becomes common
- Full-text search indexes on `User.name`, `Contract.description` — if search grows

## How to Inspect Slow Queries

```bash
# Enable query logging in PostgreSQL
docker compose exec db sh -c "psql -U tiqani_user -d tiqani_db -c 'SET log_min_duration_statement = 200;'"

# Django debug toolbar or connection.queries
python manage.py shell -c "
from django.db import connection
from django.db.models import Count
qs = Notification.objects.filter(recipient_id=1, is_read=False)
print(qs.query)
"

# Check index usage
docker compose exec db sh -c "psql -U tiqani_user -d tiqani_db -c 'EXPLAIN ANALYZE SELECT * FROM notification_notification WHERE recipient_id = 1 AND is_read = false;'"
```
