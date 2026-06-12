"""
WebSocket consumer for realtime notifications.

Connects authenticated users to a per-user channel group and delivers
realtime events: notification.created, unread_count updates, etc.

Authentication is handled by JWTAuthMiddlewareStack in the ASGI routing.
"""

import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from notification.models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Realtime notification WebSocket consumer.

    Connected users receive:
        - connection.accepted       (initial unread count)
        - notification.created      (new notification payload)
        - notification.unread_count (updated count)
        - notification.marked_read
        - notification.marked_unread
        - notification.bulk_read
        - dealership.alert
        - pong                       (in response to ping)

    Accepted client messages:
        {"type": "ping"}
        {"type": "get.unread_count"}
    """

    # ------------------------------------------------------------------
    # Group helpers
    # ------------------------------------------------------------------
    USER_GROUP_TPL = "user_notifications_{user_id}"

    def _group_name(self):
        return self.USER_GROUP_TPL.format(user_id=self.scope["user"].id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        if not user.is_authenticated:
            logger.info("WebSocket rejected: unauthenticated")
            await self.close(code=4401)
            return

        self.user = user
        self.group_name = self._group_name()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial connection payload (unread_count is advisory)
        await self.send_json({
            "type": "connection.accepted",
            "message": "Connected to realtime notifications.",
        })
        logger.debug("WebSocket connected: user=%s", user.username)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )
        logger.debug("WebSocket disconnected: code=%s", close_code)

    # ------------------------------------------------------------------
    # Client message handlers
    # ------------------------------------------------------------------

    async def receive_json(self, content):
        msg_type = content.get("type", "")

        if msg_type == "ping":
            await self.send_json({"type": "pong"})

        elif msg_type == "get.unread_count":
            count = await self._get_unread_count()
            await self.send_json({
                "type": "notification.unread_count",
                "unread_count": count,
            })

        else:
            logger.warning(
                "Unsupported message type from user %s: %s",
                self.scope["user"], msg_type,
            )
            await self.send_json({
                "type": "error",
                "message": f"Unsupported message type: {msg_type}",
            })

    # ------------------------------------------------------------------
    # Server-to-client event handlers
    # These are called by channel_layer.group_send from realtime helpers.
    # ------------------------------------------------------------------

    async def notification_created(self, event):
        """Deliver a new notification to the client."""
        await self.send_json({
            "type": "notification.created",
            "payload": event.get("payload", {}),
        })

    async def notification_unread_count(self, event):
        """Deliver an unread count update."""
        await self.send_json({
            "type": "notification.unread_count",
            "unread_count": event.get("unread_count", 0),
        })

    async def notification_marked_read(self, event):
        """Notify that a notification was marked as read."""
        await self.send_json({
            "type": "notification.marked_read",
            "notification_id": event.get("notification_id"),
        })

    async def notification_marked_unread(self, event):
        """Notify that a notification was marked as unread."""
        await self.send_json({
            "type": "notification.marked_unread",
            "notification_id": event.get("notification_id"),
        })

    async def notification_bulk_read(self, event):
        """Notify that all notifications were marked as read."""
        await self.send_json({
            "type": "notification.bulk_read",
            "updated": event.get("updated", 0),
        })

    async def dealership_alert(self, event):
        """Deliver a dealership-specific alert."""
        await self.send_json({
            "type": "dealership.alert",
            "payload": event.get("payload", {}),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_unread_count(self):
        """Return the current unread notification count for the user."""
        try:
            from asgiref.sync import sync_to_async
            count = await sync_to_async(
                Notification.unread_count_for_user
            )(self.user)
            return count
        except Exception as exc:
            logger.warning("Failed to fetch unread count: %s", exc)
            return 0
