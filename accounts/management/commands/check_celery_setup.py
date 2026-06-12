"""
Management command to verify Celery/Redis setup configuration.

Usage:
    python manage.py check_celery_setup
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check Celery/Redis setup configuration."

    def _info(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✓  {msg}"))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠  {msg}"))

    def _error(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✗  {msg}"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Celery Setup Check"))
        self.stdout.write("=" * 55)

        # ── Celery app import ─────────────────────────────────
        try:
            from tiqani_v3.celery import app as celery_app
            self._info(f"Celery app loaded: {celery_app.main}")
        except Exception as e:
            self._error(f"Cannot load Celery app: {e}")
            return

        # ── Broker ────────────────────────────────────────────
        broker = getattr(settings, "CELERY_BROKER_URL", "")
        if broker:
            self._info(f"Broker URL: {broker}")
        else:
            self._error("CELERY_BROKER_URL not configured")

        # ── Mode ──────────────────────────────────────────────
        eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
        if eager:
            self._warn("CELERY_TASK_ALWAYS_EAGER=True — tasks run synchronously")
        else:
            self._info("CELERY_TASK_ALWAYS_EAGER=False — async mode")

        # ── Beat scheduler ────────────────────────────────────
        scheduler = getattr(settings, "CELERY_BEAT_SCHEDULER", "")
        if "django_celery_beat" in scheduler:
            self._info("Beat scheduler: django-celery-beat (DatabaseScheduler)")
            if "django_celery_beat" in settings.INSTALLED_APPS:
                self._info("django_celery_beat is in INSTALLED_APPS")
            else:
                self._error("django_celery_beat NOT in INSTALLED_APPS")
        else:
            self._warn(f"Beat scheduler: {scheduler}")

        # ── Task modules discovered ───────────────────────────
        expected_modules = [
            "accounts.tasks",
            "notification.tasks",
            "dealership.tasks",
            "tiqani_v3.tasks",
        ]
        discovered = 0
        for mod_name in expected_modules:
            try:
                __import__(mod_name)
                self._info(f"Task module loaded: {mod_name}")
                discovered += 1
            except ImportError as e:
                self._warn(f"Task module NOT loaded: {mod_name} ({e})")
        self._info(f"Task modules discovered: {discovered}/{len(expected_modules)}")

        # ── Settings summary ──────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("Settings"))
        self._info(f"TIME_ZONE: {settings.TIME_ZONE}")
        self._info(f"CELERY_TIMEZONE: {settings.CELERY_TIMEZONE}")
        self._info(f"Task time limit: {getattr(settings, 'CELERY_TASK_TIME_LIMIT', 'N/A')}s")
        self._info(f"Soft time limit: {getattr(settings, 'CELERY_TASK_SOFT_TIME_LIMIT', 'N/A')}s")

        self.stdout.write(self.style.MIGRATE_HEADING("Check complete."))
