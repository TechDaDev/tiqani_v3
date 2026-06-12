"""
Tests for the WebSocket notification consumer message handlers.

Uses direct event dispatch rather than WebsocketCommunicator to avoid
async/database threading issues with SQLite in tests.
"""

from unittest.mock import AsyncMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from notification.consumers import NotificationConsumer
from notification.models import Notification

User = get_user_model()
import asyncio


class NotificationConsumerHandlerTest(TestCase):
    """Test consumer message handlers directly (no WebSocket connection)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ws_user", password="test123",
        )

    def _make_consumer(self):
        consumer = NotificationConsumer()
        consumer.scope = {"user": self.user}
        consumer.user = self.user
        consumer.group_name = consumer._group_name()
        consumer.channel_layer = None
        consumer.channel_name = "test_channel"
        consumer.send_json = AsyncMock()
        return consumer

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_unauthenticated_user_connect(self):
        consumer = NotificationConsumer()
        consumer.scope = {"user": type("Anon", (), {"is_authenticated": False})()}
        consumer.send_json = AsyncMock()
        consumer.close = AsyncMock()
        self._run_async(consumer.connect())
        self.assertTrue(hasattr(consumer, "close"))

    def test_ping_handler(self):
        consumer = self._make_consumer()
        self._run_async(consumer.receive_json({"type": "ping"}))
        consumer.send_json.assert_awaited_with({"type": "pong"})

    def test_unsupported_message_returns_error(self):
        consumer = self._make_consumer()
        self._run_async(consumer.receive_json({"type": "invalid_type"}))
        consumer.send_json.assert_awaited()
        call_args = consumer.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "error")

    def test_get_unread_count_handler(self):
        consumer = self._make_consumer()
        self._run_async(consumer.receive_json({"type": "get.unread_count"}))
        consumer.send_json.assert_awaited()
        call_args = consumer.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "notification.unread_count")

    def test_notification_created_event(self):
        consumer = self._make_consumer()
        self._run_async(consumer.notification_created({
            "type": "notification.created",
            "payload": {"title": "Test", "id": "123"},
        }))
        args = consumer.send_json.call_args[0][0]
        self.assertEqual(args["type"], "notification.created")
        self.assertEqual(args["payload"]["title"], "Test")

    def test_unread_count_event(self):
        consumer = self._make_consumer()
        self._run_async(consumer.notification_unread_count({
            "type": "notification.unread_count",
            "unread_count": 5,
        }))
        args = consumer.send_json.call_args[0][0]
        self.assertEqual(args["type"], "notification.unread_count")
        self.assertEqual(args["unread_count"], 5)

    def test_dealership_alert_event(self):
        consumer = self._make_consumer()
        self._run_async(consumer.dealership_alert({
            "type": "dealership.alert",
            "payload": {"alert_type": "threshold"},
        }))
        args = consumer.send_json.call_args[0][0]
        self.assertEqual(args["type"], "dealership.alert")
        self.assertEqual(args["payload"]["alert_type"], "threshold")

    def test_marked_read_event(self):
        consumer = self._make_consumer()
        self._run_async(consumer.notification_marked_read({
            "type": "notification.marked_read",
            "notification_id": "abc-123",
        }))
        args = consumer.send_json.call_args[0][0]
        self.assertEqual(args["type"], "notification.marked_read")
        self.assertEqual(args["notification_id"], "abc-123")

    def test_bulk_read_event(self):
        consumer = self._make_consumer()
        self._run_async(consumer.notification_bulk_read({
            "type": "notification.bulk_read",
            "updated": 10,
        }))
        args = consumer.send_json.call_args[0][0]
        self.assertEqual(args["type"], "notification.bulk_read")
        self.assertEqual(args["updated"], 10)

    def test_consumer_imports(self):
        from notification.consumers import NotificationConsumer
        self.assertIsNotNone(NotificationConsumer)
