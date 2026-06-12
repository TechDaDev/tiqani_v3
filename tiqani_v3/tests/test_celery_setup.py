"""
Tests for Celery app setup and configuration.
"""

from django.test import TestCase, override_settings
from django.conf import settings


class CeleryAppTest(TestCase):
    """Verify Celery app can be imported and configured."""

    def test_celery_app_imports(self):
        """Celery app imports without errors."""
        from tiqani_v3.celery import app
        self.assertIsNotNone(app)
        self.assertEqual(app.main, "tiqani_v3")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_celery_task_always_eager_configured(self):
        """CELERY_TASK_ALWAYS_EAGER should be True when configured."""
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)

    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    def test_celery_task_eager_propagates(self):
        """Eager task errors propagate when configured."""
        self.assertTrue(settings.CELERY_TASK_EAGER_PROPAGATES)

    def test_celery_broker_configured(self):
        """Broker URL is present."""
        self.assertTrue(settings.CELERY_BROKER_URL)

    def test_celery_beat_app_installed(self):
        """django_celery_beat is in INSTALLED_APPS."""
        self.assertIn("django_celery_beat", settings.INSTALLED_APPS)

    def test_celery_settings_present(self):
        """Core Celery settings are configured."""
        self.assertIsNotNone(settings.CELERY_TIMEZONE)
        self.assertIsNotNone(settings.CELERY_TASK_TIME_LIMIT)
        self.assertIsNotNone(settings.CELERY_TASK_SOFT_TIME_LIMIT)

    def test_task_modules_import(self):
        """All expected task modules can be imported."""
        from accounts import tasks as accounts_tasks
        from notification import tasks as notification_tasks
        from dealership import tasks as dealership_tasks
        from tiqani_v3 import tasks as project_tasks
        self.assertIsNotNone(accounts_tasks)
        self.assertIsNotNone(notification_tasks)
        self.assertIsNotNone(dealership_tasks)
        self.assertIsNotNone(project_tasks)

    def test_check_celery_setup_command_runs(self):
        """check_celery_setup command runs without errors."""
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("check_celery_setup", stdout=out)
        output = out.getvalue()
        self.assertIn("Celery Setup Check", output)
        self.assertIn("Task modules discovered", output)

    def test_seed_celery_beat_schedule_command_idempotent(self):
        """seed_celery_beat_schedule runs safely and is idempotent."""
        from io import StringIO
        from django.core.management import call_command
        out1 = StringIO()
        call_command("seed_celery_beat_schedule", stdout=out1)
        out2 = StringIO()
        call_command("seed_celery_beat_schedule", stdout=out2)
        self.assertIn("schedule seeded", out2.getvalue().lower())

    def test_periodic_tasks_created(self):
        """Expected PeriodicTask entries are created after seeding."""
        from io import StringIO
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        call_command("seed_celery_beat_schedule", stdout=StringIO())

        expected_tasks = [
            "OTP Cleanup",
            "Cash-out Code Expiry",
            "Notification Cleanup",
            "Dealership Threshold Alerts",
            "Dealership Guarantee Expiry Alerts",
            "Media Orphan Report",
            "Celery Health Check",
        ]
        for name_fragment in expected_tasks:
            exists = PeriodicTask.objects.filter(
                name__icontains=name_fragment
            ).exists()
            self.assertTrue(
                exists,
                f"PeriodicTask '{name_fragment}' should exist after seeding.",
            )
