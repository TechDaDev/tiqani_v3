#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: CONFIRM_RESTORE=YES $0 <backup.sql.gz>" >&2
  exit 2
fi

if [[ "${CONFIRM_RESTORE:-NO}" != "YES" ]]; then
  echo "Refusing destructive restore. Set CONFIRM_RESTORE=YES." >&2
  exit 3
fi

gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL"
echo "Restore complete: $BACKUP_FILE"
