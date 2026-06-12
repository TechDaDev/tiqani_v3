"""
Tests for notification background tasks — cleanup, async creation.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from notification.models import Notification
from notification.tasks import cleanup_old_read_notifications_task

User = get_user_model()


class NotificationCleanupTaskTest(TestCase):
    """Test the old read notifications cleanup task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="notif_cleanup", password="test123",
        )
        # Create an old read notification
        self.old_notif = Notification.objects.create(
            recipient=self.user,
            notification_type="system",
            title="Old notification",
            is_read=True,
            read_at=timezone.now() - timedelta(days=200),
        )
        # Create a recent read notification
        self.recent_notif = Notification.objects.create(
            recipient=self.user,
            notification_type="system",
            title="Recent notification",
            is_read=True,
            read_at=timezone.now() - timedelta(days=1),
        )
        # Create an unread notification
        self.unread_notif = Notification.objects.create(
            recipient=self.user,
            notification_type="system",
            title="Unread notification",
            is_read=False,
        )

    def test_dry_run_reports_count(self):
        """Dry run reports affected count without deleting."""
        result = cleanup_old_read_notifications_task(dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["affected_count"], 1)  # Only the old read one
        self.assertEqual(result["action"], "would delete")

        # Verify nothing was actually deleted
        self.assertEqual(Notification.objects.count(), 3)

    def test_non_dry_run_deletes_old(self):
        """Non-dry-run deletes old read notifications."""
        result = cleanup_old_read_notifications_task(dry_run=False)

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["affected_count"], 1)  # Old read one
        self.assertEqual(result["action"], "deleted")

        # Verify old one is gone, others remain
        remaining = Notification.objects.all()
        self.assertEqual(remaining.count(), 2)
        self.assertFalse(
            Notification.objects.filter(id=self.old_notif.id).exists(),
        )

    def test_task_imports(self):
        """Notification task module imports correctly."""
        from notification.tasks import create_notification_async
        self.assertIsNotNone(create_notification_async)
