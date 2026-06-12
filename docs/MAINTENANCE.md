# Maintenance Guide — tiqani_v3

## Backup Strategy

### Database

```bash
# PostgreSQL
pg_dump -U tiqani_user -d tiqani_db > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite (development only)
cp db.sqlite3 backup_$(date +%Y%m%d_%H%M%S).sqlite3
```

### Media Files

```bash
# Backup uploaded media
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

### Automated Backups

For production, configure daily cron jobs or use a managed database service with automated backups (e.g., AWS RDS, DigitalOcean Managed DB).

## Restore Strategy

```bash
# PostgreSQL
createdb -U tiqani_user tiqani_db_restored
psql -U tiqani_user -d tiqani_db_restored < backup_20250101_000000.sql

# Media files
tar -xzf media_backup_20250101_000000.tar.gz
```

Always test your restore process before relying on it in production.

## Log Review

```bash
# Docker
docker compose logs -f web

# Production (journald)
journalctl -u tiqani -f

# Application logs (if file logging configured)
tail -f /var/log/tiqani/*.log
```

## Rotating Secrets

1. Generate new `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

2. Update `.env` with the new key
3. Restart the server

## Updating Dependencies

```bash
# Review outdated packages
pip list --outdated

# Update a single package safely
pip install --upgrade package-name

# Update all packages (after reviewing)
pip install --upgrade -r requirements.txt
```

Always run the full test suite after updating dependencies.

## Running Migrations

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py makemigrations --check --dry-run
```

## Seed Platform Fees

```bash
.venv/bin/python manage.py seed_platform_fees
```

This command creates the default platform fee configuration if it does not already exist. Safe to run repeatedly (idempotent).

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---|---|---|
| 500 errors on all endpoints | Database connection issue | Check `DATABASE_URL` and DB server status |
| Static files not loading | `collectstatic` not run | Run `python manage.py collectstatic --noinput` |
| Login returns 401 | Invalid credentials or expired token | Check credentials or refresh token |
| CORS errors in frontend | `CORS_ALLOWED_ORIGINS` not set correctly | Update environment variable |
| 429 Too Many Requests | Rate limit exceeded | Wait and retry, or adjust throttle rates |
| Upload rejected | File too large or invalid type | Check file size/type limits in `docs/MEDIA_STORAGE.md` |
| S3 upload failure | Missing credentials or bucket | Run `python manage.py check_media_storage` to diagnose |
| Emails not sending | SMTP misconfigured | Check SMTP host, port, credentials |
| OTP not working | Clock skew or expired code | Check server time, reduce `OTP_VALIDITY_SECONDS` |
| Migrations failing | Conflicting schema changes | Rollback, fix, and re-run migrations |
| Permission denied | Missing admin role | Assign correct `AdminProfile.role` |
