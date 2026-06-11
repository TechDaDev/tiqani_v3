"""Tests for notification and activity service functions."""

from django.test import TestCase
from django.contrib.auth import get_user_model

from notification.models import Notification, ActivityLog
from notification.services import (
    create_notification, create_activity, notify_admins,
    mark_all_notifications_read,
)

User = get_user_model()


class NotificationServicesTest(TestCase):
    """Tests for core service functions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="t@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="a@t.com", password="admin123",
        )

    def test_create_notification_creates_record(self):
        """create_notification creates expected record."""
        n = create_notification(
            recipient=self.user,
            notification_type=Notification.Type.SYSTEM,
            title="Test title",
            message="Test message",
            target_type="test",
        )
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.user)
        self.assertEqual(n.title, "Test title")
        self.assertEqual(n.message, "Test message")
        self.assertEqual(n.target_type, "test")
        self.assertFalse(n.is_read)

    def test_create_notification_returns_none_on_error(self):
        """create_notification gracefully handles None recipient."""
        n = create_notification(
            recipient=None,
            notification_type=Notification.Type.SYSTEM,
            title="Should not create",
        )
        self.assertIsNone(n)

    def test_create_activity_creates_record(self):
        """create_activity creates expected record."""
        a = create_activity(
            verb="test_action",
            actor=self.user,
            target_type="test",
            audience="admin",
        )
        self.assertIsNotNone(a)
        self.assertEqual(a.verb, "test_action")
        self.assertEqual(a.actor, self.user)
        self.assertEqual(a.audience, "admin")

    def test_notify_admins_sends_to_staff(self):
        """notify_admins creates notifications for staff users."""
        results = notify_admins(
            notification_type=Notification.Type.SYSTEM,
            title="Admin alert",
            message="Something happened",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].recipient, self.admin)

    def test_mark_all_read(self):
        """mark_all_notifications_read marks all unread as read."""
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.Type.SYSTEM,
                title=f"Notif {i}",
            )
        count = mark_all_notifications_read(self.user)
        self.assertEqual(count, 3)
        remaining = Notification.objects.filter(recipient=self.user, is_read=False).count()
        self.assertEqual(remaining, 0)
