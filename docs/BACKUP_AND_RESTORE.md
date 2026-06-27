# Backup And Restore

## PostgreSQL Backup

Use `scripts/backup_postgres.sh`.

Required environment:
- `DATABASE_URL`
- optional `BACKUP_DIR`
- optional `RETENTION_DAYS`

Backups are timestamped and gzip-compressed.

## PostgreSQL Restore

Use `scripts/restore_postgres.sh <backup.sql.gz>`.

Restore requires `CONFIRM_RESTORE=YES`.

## Media Backup

Back up `MEDIA_ROOT` or object-storage bucket with encryption at rest.

## Targets

- RPO: 24 hours until production traffic requires tighter guarantees.
- RTO: 4 hours for single-region controlled deployment.

## Offsite Storage

Store encrypted backups outside the primary host/provider account.
