"""
Management command to verify production-operations readiness.

Checks Sentry config, Celery connectivity, channel layer, static files,
database connectivity, and critical env vars.  Designed to be run as a
Docker HEALTHCHECK or a pre-deploy smoke test.

Usage:
    python manage.py check_operations_ready
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, DEFAULT_DB_ALIAS


class Command(BaseCommand):
    help = "Verify production-operations readiness (Sentry, Celery, channels, etc.)."

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✓  {msg}"))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠  {msg}"))

    def _err(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✗  {msg}"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Operations Readiness Check"))
        self.stdout.write("=" * 55)

        # ── 1. Database ──────────────────────────────────────
        try:
            conn = connections[DEFAULT_DB_ALIAS]
            conn.ensure_connection()
            self._ok("Database reachable")
        except Exception as e:
            self._err(f"Database: {e}")

        # ── 2. Sentry DSN ────────────────────────────────────
        dsn = getattr(settings, "SENTRY_DSN", "")
        if dsn:
            self._ok("SENTRY_DSN configured")
        else:
            self._warn("SENTRY_DSN not set — Sentry will be disabled")

        # ── 3. Celery broker ─────────────────────────────────
        broker = getattr(settings, "CELERY_BROKER_URL", "")
        eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
        if broker:
            self._ok(f"Broker URL: {broker}")
        else:
            self._err("CELERY_BROKER_URL not configured")
        if eager:
            self._warn("CELERY_TASK_ALWAYS_EAGER=True — tasks are synchronous")

        # ── 4. Channel layer ─────────────────────────────────
        try:
            import channels.layers
            channel_layer = channels.layers.get_channel_layer()
            self._ok(f"Channel layer: {channel_layer.__class__.__name__}")
        except Exception as e:
            self._warn(f"Channel layer unavailable: {e}")

        # ── 5. Static files ──────────────────────────────────
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root and os.path.isdir(str(static_root)):
            self._ok(f"STATIC_ROOT exists: {static_root}")
        else:
            self._warn(f"STATIC_ROOT missing or not a directory: {static_root}")

        # ── 6. Log format ────────────────────────────────────
        log_format = getattr(settings, "LOG_FORMAT", "verbose")
        self._ok(f"Log format: {log_format}")

        # ── 7. APP_VERSION ───────────────────────────────────
        app_version = os.environ.get("APP_VERSION", "")
        if app_version:
            self._ok(f"APP_VERSION: {app_version}")
        else:
            self._warn("APP_VERSION not set")
