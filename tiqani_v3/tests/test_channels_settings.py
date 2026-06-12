"""
Tests for Django Channels settings and configuration.
"""

from django.test import TestCase, override_settings
from django.conf import settings


class ChannelsSettingsTest(TestCase):
    """Verify Channels configuration."""

    def test_channels_in_installed_apps(self):
        """channels is in INSTALLED_APPS."""
        self.assertIn("channels", settings.INSTALLED_APPS)

    def test_asgi_application_configured(self):
        """ASGI_APPLICATION setting is present."""
        self.assertTrue(
            getattr(settings, "ASGI_APPLICATION", ""),
            "ASGI_APPLICATION should be configured",
        )

    def test_channel_layers_configured(self):
        """CHANNEL_LAYERS is configured."""
        channel_layers = getattr(settings, "CHANNEL_LAYERS", {})
        self.assertIn("default", channel_layers)
        self.assertIn("BACKEND", channel_layers["default"])

    @override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
    def test_channel_layer_in_memory_in_test(self):
        """When overridden, channel layer should be InMemoryChannelLayer."""
        backend = settings.CHANNEL_LAYERS["default"]["BACKEND"]
        self.assertIn("InMemory", backend)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChannelsOverriddenSettingsTest(TestCase):
    """Test with overridden in-memory channel layer."""

    def test_in_memory_layer_works(self):
        """Verify the in-memory channel layer can be imported."""
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        self.assertIsNotNone(channel_layer)

    def test_routing_imports(self):
        """Verify ASGI routing module can be imported without errors."""
        from tiqani_v3.routing import application, websocket_urlpatterns
        self.assertIsNotNone(application)
        self.assertGreaterEqual(len(websocket_urlpatterns), 1)

    def test_ws_auth_imports(self):
        """Verify ws_auth module can be imported."""
        from tiqani_v3.ws_auth import JWTAuthMiddleware, JWTAuthMiddlewareStack
        self.assertIsNotNone(JWTAuthMiddleware)
        self.assertIsNotNone(JWTAuthMiddlewareStack)

    def test_consumer_imports(self):
        """Verify notification consumer can be imported."""
        from notification.consumers import NotificationConsumer
        self.assertIsNotNone(NotificationConsumer)

    def test_realtime_helpers_import(self):
        """Verify realtime helper module can be imported."""
        from notification.realtime import (
            send_realtime_notification,
            broadcast_unread_count,
            send_notification_created,
            get_user_notification_group,
        )
        self.assertIsNotNone(send_realtime_notification)
        self.assertIsNotNone(broadcast_unread_count)
        self.assertIsNotNone(send_notification_created)
        self.assertIsNotNone(get_user_notification_group)

    def test_check_realtime_setup_command_runs(self):
        """check_realtime_setup command runs without errors."""
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("check_realtime_setup", stdout=out)
        output = out.getvalue()
        self.assertIn("Realtime Setup Check", output)
        self.assertIn("WebSocket path", output)

    def test_check_realtime_setup_command_does_not_print_secrets(self):
        """The check command should not expose secrets/tokens."""
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("check_realtime_setup", stdout=out)
        output = out.getvalue().lower()
        # Should not contain raw secrets
        self.assertNotIn("secret", output)
