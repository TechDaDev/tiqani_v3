#!/bin/sh
set -eu

MEDIA_ROOT="${MEDIA_ROOT:-/tmp/tiqani/media}"
STATIC_ROOT="${STATIC_ROOT:-/tmp/tiqani/staticfiles}"
PORT="${PORT:-8000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Initializing local fallback paths at MEDIA_ROOT=$MEDIA_ROOT STATIC_ROOT=$STATIC_ROOT"
mkdir -p "$MEDIA_ROOT" "$STATIC_ROOT"

echo "Running migrations"
python -u manage.py migrate --noinput

echo "Collecting static files"
python -u manage.py collectstatic --noinput --clear

echo "Starting Gunicorn on port $PORT"
exec gunicorn tiqani_v3.wsgi:application \
  --bind "0.0.0.0:$PORT" \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile - \
  --error-logfile -
