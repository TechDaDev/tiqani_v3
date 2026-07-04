#!/bin/sh
# =============================================================================
# tiqani_v3 — Docker entrypoint script
# =============================================================================
# Responsibilities:
#   1. Wait for the database to be ready
#   2. Run migrations (if RUN_MIGRATIONS=true)
#   3. Collect static files (if RUN_COLLECTSTATIC=true)
#   4. Seed platform fee config (if SEED_PLATFORM_FEES=true)
#   5. Execute the main container command
# =============================================================================

set -e

is_true() {
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes|y) return 0 ;;
        *) return 1 ;;
    esac
}

# ── Wait for database ──────────────────────────────────────────────
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    # Extract host and port from DATABASE_URL if it's postgres
    case "$DATABASE_URL" in
        postgres*)
            DB_HOST=$(python - <<'PY'
import os
from urllib.parse import urlparse
print(urlparse(os.environ["DATABASE_URL"]).hostname or "")
PY
)
            DB_PORT=$(python - <<'PY'
import os
from urllib.parse import urlparse
print(urlparse(os.environ["DATABASE_URL"]).port or 5432)
PY
)
            DB_PORT="${DB_PORT:-5432}"
            echo "  Host: $DB_HOST, Port: $DB_PORT"
            # Simple TCP wait loop
            for i in $(seq 1 30); do
                if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
                    echo "  Database is ready."
                    break
                fi
                echo "  Waiting... ($i/30)"
                sleep 1
            done
            ;;
    esac
fi

# ── Run migrations ─────────────────────────────────────────────────
if is_true "${RUN_MIGRATIONS:-false}"; then
    echo "Running migrations..."
    python manage.py migrate --noinput
    echo "  Done."
fi

# ── Seed Celery Beat schedule ──────────────────────────────────────
if is_true "${SEED_CELERY_BEAT:-false}"; then
    echo "Seeding Celery Beat schedule..."
    python manage.py seed_celery_beat_schedule
    echo "  Done."
fi

# ── Collect static files ───────────────────────────────────────────
if is_true "${RUN_COLLECTSTATIC:-false}"; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    echo "  Done."
fi

# ── Seed platform fees ─────────────────────────────────────────────
if is_true "${SEED_PLATFORM_FEES:-false}"; then
    echo "Seeding platform fees..."
    python manage.py seed_platform_fees
    echo "  Done."
fi

# ── Seed Celery Beat schedule (ops tasks) ──────────────────────────
if is_true "${SEED_CELERY_BEAT:-false}"; then
    echo "Seeding Celery Beat schedule for Phase 15 ops tasks..."
    python manage.py seed_celery_beat_schedule
    echo "  Done."
fi

# ── Execute main command ───────────────────────────────────────────
echo "Starting: $@"
exec "$@"
