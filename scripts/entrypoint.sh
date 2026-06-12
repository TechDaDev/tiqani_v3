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

# ── Wait for database ──────────────────────────────────────────────
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    # Extract host and port from DATABASE_URL if it's postgres
    case "$DATABASE_URL" in
        postgres*)
            DB_HOST=$(echo "$DATABASE_URL" | awk -F[@:/] '{print $4}')
            DB_PORT=$(echo "$DATABASE_URL" | awk -F[@:/] '{print $5}' | awk -F'?' '{print $1}')
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
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
    echo "  Done."
fi

# ── Seed Celery Beat schedule ──────────────────────────────────────
if [ "${SEED_CELERY_BEAT:-false}" = "true" ]; then
    echo "Seeding Celery Beat schedule..."
    python manage.py seed_celery_beat_schedule
    echo "  Done."
fi

# ── Collect static files ───────────────────────────────────────────
if [ "${RUN_COLLECTSTATIC:-false}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    echo "  Done."
fi

# ── Seed platform fees ─────────────────────────────────────────────
if [ "${SEED_PLATFORM_FEES:-false}" = "true" ]; then
    echo "Seeding platform fees..."
    python manage.py seed_platform_fees
    echo "  Done."
fi

# ── Execute main command ───────────────────────────────────────────
echo "Starting: $@"
exec "$@"
