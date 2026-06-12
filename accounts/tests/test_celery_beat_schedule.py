"""
Tests for Celery Beat schedule — periodic task creation and idempotency.
"""

from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django_celery_beat.models import PeriodicTask


class CeleryBeatScheduleTest(TestCase):
    """Test the seed_celery_beat_schedule command."""

    def test_seed_command_creates_tasks(self):
        """Running seed command creates expected PeriodicTasks."""
        # Count before
        before = PeriodicTask.objects.count()

        out = StringIO()
        call_command("seed_celery_beat_schedule", stdout=out)

        after = PeriodicTask.objects.count()
        self.assertGreater(after, before)
        self.assertIn("created", out.getvalue().lower())

    def test_seed_command_is_idempotent(self):
        """Running seed twice does not create duplicate tasks."""
        call_command("seed_celery_beat_schedule", stdout=StringIO())
        count1 = PeriodicTask.objects.count()

        call_command("seed_celery_beat_schedule", stdout=StringIO())
        count2 = PeriodicTask.objects.count()

        self.assertEqual(count1, count2)

    def test_seed_creates_expected_tasks(self):
        """Specific expected tasks are created."""
        call_command("seed_celery_beat_schedule", stdout=StringIO())

        task_names = [
            task.name for task in PeriodicTask.objects.all()
        ]
        joined = " ".join(task_names)

        expected_fragments = [
            "OTP Cleanup",
            "Cash-out Code Expiry",
            "Notification Cleanup",
            "Dealership Threshold Alerts",
            "Dealership Guarantee Expiry Alerts",
            "Media Orphan Report",
            "Celery Health Check",
        ]

        for frag in expected_fragments:
            self.assertIn(frag, joined, f"Expected '{frag}' in seeded tasks")
