# Backup & Restore

## PostgreSQL Backup

### Manual Backup

```bash
# Dump the database
pg_dump -h db -U tiqani_user -d tiqani_db -F c -f /backups/tiqani_$(date +%Y%m%d_%H%M%S).dump

# With Docker Compose
docker compose exec db pg_dump -U tiqani_user -d tiqani_db -F c -f /tmp/backup.dump
docker compose cp db:/tmp/backup.dump ./backups/
```

### Automatic Backup (Cron)

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * docker compose exec -T db pg_dump -U tiqani_user -d tiqani_db -F c > /backups/tiqani_$(date +\%Y\%m\%d).dump
```

## PostgreSQL Restore

```bash
# Restore from dump (WARNING: replaces all data)
pg_restore -h db -U tiqani_user -d tiqani_db --clean --if-exists -F c /backups/tiqani_20261201.dump

# With Docker Compose
docker compose cp ./backups/tiqani_20261201.dump db:/tmp/
docker compose exec db pg_restore -U tiqani_user -d tiqani_db --clean --if-exists -F c /tmp/tiqani_20261201.dump
```

## Media / S3 Backup

- **S3-compatible storage**: Your provider handles durability. Enable versioning.
- **Local media**: `tar -czf media_backup.tar.gz media/`

## Environment / Config Backup

```bash
# Backup .env file separately — it contains secrets
cp .env /backups/env_$(date +%Y%m%d).backup
```

## Key Notes

| Resource | Strategy | Priority |
|---|---|---|
| PostgreSQL | `pg_dump` daily | High |
| Media files | S3 versioning or file backup | Medium |
| `.env` config | Manual copy with secrets | High |
| Redis | **Ephemeral** — no backup needed | None |
| Celery Beat schedule | Stored in PostgreSQL (part of DB backup) | Medium |

## Dealership Financial Data

Dealership financial records (ledger, recharges, cash-outs, guarantees) are
stored in the PostgreSQL database and included in every `pg_dump`. No
separate export is required for backup, but **financial data should be the
first priority during restore verification**.

## Audit Export Backup

Run the audit export command periodically and store the output:

```bash
python manage.py export_audit_logs --days 30 --format json > /backups/audit_$(date +%Y%m%d).json
```

## Restore Verification Checklist

- [ ] Database restored without errors
- [ ] Admin login works
- [ ] Demo users exist
- [ ] Health endpoint returns 200
- [ ] Wallet balances match expected
- [ ] Dealership financial data intact
- [ ] Notification count matches
- [ ] Static files accessible
- [ ] Media files accessible
- [ ] `.env` restored with correct secrets
- [ ] Celery Beat schedule reseeded: `python manage.py seed_celery_beat_schedule`
- [ ] Test a simple API call (`GET /api/categories/`)

## Test Restore Procedure

Periodically (every 3 months recommended):

1. Set up a fresh Docker Compose environment
2. Restore the latest backup
3. Run the QA checklist above
4. Run `python manage.py final_backend_qa`
5. Document any issues
