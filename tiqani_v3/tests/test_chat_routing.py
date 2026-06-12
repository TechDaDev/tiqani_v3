"""Tests for chat WebSocket routing."""

from django.test import TestCase

from tiqani_v3.routing import websocket_urlpatterns


class ChatRoutingTests(TestCase):
    """Verify chat WebSocket routes exist."""

    def test_chat_websocket_route_exists(self):
        """Check that the chat room WebSocket route is registered."""
        patterns = [str(p.pattern) for p in websocket_urlpatterns]
        chat_routes = [p for p in patterns if "chat" in p.lower()]
        self.assertGreaterEqual(len(chat_routes), 1, "Chat WebSocket route not found")

    def test_notification_websocket_still_exists(self):
        """Existing notification WebSocket route should still be registered."""
        patterns = [str(p.pattern) for p in websocket_urlpatterns]
        notif_routes = [p for p in patterns if "notification" in p.lower()]
        self.assertGreaterEqual(len(notif_routes), 1, "Notification WebSocket route not found")
