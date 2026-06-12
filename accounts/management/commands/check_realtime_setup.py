"""
Management command to verify Channels/WebSocket realtime setup.

Usage:
    python manage.py check_realtime_setup
    python manage.py check_realtime_setup --ping-layer
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check Channels/WebSocket realtime setup configuration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ping-layer",
            action="store_true",
            help="Attempt to send a test message through the channel layer.",
        )

    def _info(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✓  {msg}"))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠  {msg}"))

    def _error(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✗  {msg}"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Realtime Setup Check"))
        self.stdout.write("=" * 55)

        # ── ASGI application ───────────────────────────────────────
        asgi_app = getattr(settings, "ASGI_APPLICATION", "")
        if asgi_app:
            self._info(f"ASGI_APPLICATION: {asgi_app}")
        else:
            self._error("ASGI_APPLICATION not configured")

        # ── Channels installed ─────────────────────────────────────
        if "channels" in settings.INSTALLED_APPS:
            self._info("channels is in INSTALLED_APPS")
        else:
            self._error("channels NOT in INSTALLED_APPS")

        # ── Channel layer backend ──────────────────────────────────
        channel_layers = getattr(settings, "CHANNEL_LAYERS", {})
        default_layer = channel_layers.get("default", {})
        backend = default_layer.get("BACKEND", "NOT CONFIGURED")

        if "channels_redis" in backend:
            host_config = default_layer.get("CONFIG", {}).get("hosts", [])
            if host_config:
                raw_url = str(host_config[0])
                # Mask password if present
                masked = self._mask_redis_url(raw_url)
                self._info(f"Channel layer backend: {backend}")
                self._info(f"Redis URL: {masked}")
            else:
                self._warn(f"Channel layer backend: {backend} (no hosts configured)")
        elif "InMemory" in backend:
            self._warn("Channel layer: InMemoryChannelLayer (no Redis)")
        else:
            self._warn(f"Channel layer backend: {backend}")

        # ── Test / in-memory mode ──────────────────────────────────
        is_test = "InMemory" in backend
        if is_test:
            self._warn("In-memory channel layer — realtime events won't persist across processes")

        # ── WebSocket path ─────────────────────────────────────────
        try:
            from tiqani_v3.routing import websocket_urlpatterns
            paths = [str(p.pattern) for p in websocket_urlpatterns]
            for p in paths:
                self._info(f"WebSocket path: /{p}")
        except Exception as e:
            self._warn(f"Cannot load WebSocket routes: {e}")

        # ── Optional channel layer ping ────────────────────────────
        if options.get("ping_layer"):
            self._ping_channel_layer()

        self.stdout.write(self.style.MIGRATE_HEADING("Check complete."))

    def _mask_redis_url(self, url):
        """Mask the password portion of a Redis URL for safe display."""
        if "@" in url:
            try:
                scheme_rest = url.split("://", 1)
                if len(scheme_rest) == 2:
                    credentials, host = scheme_rest[1].split("@", 1)
                    user_part = credentials.split(":", 1)[0] if ":" in credentials else credentials
                    return f"{scheme_rest[0]}://{user_part}:****@****"
            except Exception:
                pass
        return url

    def _ping_channel_layer(self):
        """Try to send a test message through the channel layer."""
        self.stdout.write()
        self.stdout.write(self.style.MIGRATE_HEADING("Channel Layer Ping..."))
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer is None:
                self._error("Channel layer not available")
                return

            # Send a test message (will go nowhere without a consumer)
            async_to_sync(channel_layer.send)("test_channel", {
                "type": "test.message",
                "text": "ping",
            })
            self._info("Test message sent to channel layer")
        except Exception as exc:
            self._error(f"Channel layer ping failed: {exc}")
