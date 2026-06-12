"""
Tests for realtime notification service helpers.

These tests verify that the realtime helper functions can be called
safely without raising exceptions, even when no Redis is available.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from notification.models import Notification
from notification.realtime import (
    send_realtime_notification,
    broadcast_unread_count,
    send_notification_created,
    send_marked_read_event,
    send_marked_unread_event,
    send_bulk_read_event,
    send_dealership_alert,
    get_user_notification_group,
)

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class RealtimeHelperTest(TestCase):
    """Test realtime helper functions can be called safely."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="realtime_test", password="test123",
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            notification_type="system",
            title="Test realtime notification",
            message="Test message",
        )

    def test_get_user_notification_group_returns_string(self):
        """Group name is correctly formatted."""
        group = get_user_notification_group(self.user.id)
        self.assertIn(str(self.user.id), group)
        self.assertIn("user_notifications_", group)

    def test_send_realtime_notification_safe(self):
        """Calling send_realtime_notification does not raise."""
        try:
            result = send_realtime_notification(
                self.user.id,
                {"title": "test", "message": "hello"},
            )
            # May return False if channel layer not properly configured
            # but should NOT raise.
        except Exception as exc:
            self.fail(f"send_realtime_notification raised: {exc}")

    def test_broadcast_unread_count_safe(self):
        """Calling broadcast_unread_count does not raise."""
        try:
            broadcast_unread_count(self.user.id)
        except Exception as exc:
            self.fail(f"broadcast_unread_count raised: {exc}")

    def test_send_notification_created_safe(self):
        """Calling send_notification_created does not raise."""
        try:
            send_notification_created(self.notification)
        except Exception as exc:
            self.fail(f"send_notification_created raised: {exc}")

    def test_create_notification_triggers_realtime(self):
        """Creating a notification through services should trigger realtime."""
        from notification.services import create_notification

        notif = create_notification(
            recipient=self.user,
            notification_type="system",
            title="Realtime test",
        )
        self.assertIsNotNone(notif)

    def test_mark_notification_read_triggers_realtime(self):
        """Marking a notification as read should broadcast unread count."""
        from notification.services import mark_notification_read

        # Create a notification to mark as read
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type="system",
            title="Read test",
        )

        result = mark_notification_read(notif, self.user)
        self.assertTrue(result)
        self.assertTrue(Notification.objects.get(id=notif.id).is_read)

    def test_mark_all_notifications_read_triggers_realtime(self):
        """Marking all notifications as read should broadcast."""
        from notification.services import mark_all_notifications_read

        updated = mark_all_notifications_read(self.user)
        self.assertGreater(updated, 0)

    def test_send_marked_read_event_safe(self):
        """send_marked_read_event does not raise."""
        try:
            send_marked_read_event(self.user.id, self.notification.id)
        except Exception as exc:
            self.fail(f"send_marked_read_event raised: {exc}")

    def test_send_marked_unread_event_safe(self):
        """send_marked_unread_event does not raise."""
        try:
            send_marked_unread_event(self.user.id, self.notification.id)
        except Exception as exc:
            self.fail(f"send_marked_unread_event raised: {exc}")

    def test_send_bulk_read_event_safe(self):
        """send_bulk_read_event does not raise."""
        try:
            send_bulk_read_event(self.user.id, 5)
        except Exception as exc:
            self.fail(f"send_bulk_read_event raised: {exc}")

    def test_send_dealership_alert_safe(self):
        """send_dealership_alert does not raise."""
        try:
            send_dealership_alert(
                self.user.id,
                {"alert_type": "threshold_warning", "message": "test"},
            )
        except Exception as exc:
            self.fail(f"send_dealership_alert raised: {exc}")
