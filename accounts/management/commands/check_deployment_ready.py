"""
Management command to verify deployment readiness.

Usage:
    python manage.py check_deployment_ready

Prints key configuration values and warnings to help verify production readiness.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, DEFAULT_DB_ALIAS
from wallet.models import PlatformFeeConfig


class Command(BaseCommand):
    help = "Check deployment readiness — settings, database, and config"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Deployment Readiness Check"))
        self.stdout.write("=" * 50)

        # ── Settings module ─────────────────────────────────────────
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'not set')
        self.stdout.write(f"\nSettings module: {settings_module}")

        # ── Debug mode ──────────────────────────────────────────────
        if settings.DEBUG:
            self.stdout.write(self.style.WARNING("  WARNING: DEBUG is enabled!"))
        else:
            self.stdout.write(self.style.SUCCESS("  DEBUG: disabled ✓"))

        # ── SECRET_KEY ──────────────────────────────────────────────
        sk = getattr(settings, "SECRET_KEY", "")
        if not sk or sk == "change-me" or sk == "change-me-to-a-long-random-string":
            self.stdout.write(self.style.ERROR("  ERROR: SECRET_KEY is insecure or default!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  SECRET_KEY: set ({len(sk)} chars) ✓"))

        # ── ALLOWED_HOSTS ───────────────────────────────────────────
        hosts = getattr(settings, "ALLOWED_HOSTS", [])
        if not hosts:
            self.stdout.write(self.style.ERROR("  ERROR: ALLOWED_HOSTS is empty!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  ALLOWED_HOSTS: {', '.join(hosts)} ✓"))

        # ── Database engine ─────────────────────────────────────────
        db = settings.DATABASES.get(DEFAULT_DB_ALIAS, {})
        engine = db.get("ENGINE", "unknown")
        db_name = db.get("NAME", "unknown")
        self.stdout.write(f"  Database engine: {engine}")
        self.stdout.write(f"  Database name: {db_name}")
        if "sqlite" in engine:
            self.stdout.write(self.style.WARNING("  WARNING: Using SQLite — production should use PostgreSQL."))

        # ── Database connection check ───────────────────────────────
        try:
            conn = connections[DEFAULT_DB_ALIAS]
            conn.ensure_connection()
            self.stdout.write(self.style.SUCCESS("  Database connection: OK ✓"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Database connection: FAILED — {e}"))

        # ── CORS allowed origins ────────────────────────────────────
        cors = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        self.stdout.write(f"  CORS allowed origins: {len(cors)} configured")
        if cors:
            for o in cors:
                self.stdout.write(f"    - {o}")

        # ── CSRF trusted origins ────────────────────────────────────
        csrf = getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
        self.stdout.write(f"  CSRF trusted origins: {len(csrf)} configured")

        # ── Platform fee config ─────────────────────────────────────
        fee_count = PlatformFeeConfig.objects.count()
        if fee_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  Platform fee configs: {fee_count} ✓"))
        else:
            self.stdout.write(self.style.WARNING("  WARNING: No platform fee configs found! Run seed_platform_fees."))

        # ── Pending migrations ──────────────────────────────────────
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                self.stdout.write(self.style.WARNING(f"  WARNING: {len(plan)} pending migration(s)!"))
                for m, _ in plan:
                    self.stdout.write(f"    - {m.app_label}.{m.name}")
            else:
                self.stdout.write(self.style.SUCCESS("  Migrations: up to date ✓"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Could not check migrations: {e}"))

        # ── Summary ─────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Check complete."))
