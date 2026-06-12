"""
WebSocket consumer for realtime chat.

Connects authenticated participants to a per-room Channels group.
Supports sending text messages, typing indicators, read receipts,
and price offers via WebSocket.

Authentication is handled by JWTAuthMiddlewareStack.
File uploads are NOT accepted via WebSocket — use REST multipart endpoint.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from .models import ServiceChatRoom, ServiceChatMessage
from . import services as svc

logger = logging.getLogger(__name__)


class ServiceChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Realtime chat WebSocket consumer.

    Connected users receive:
        - chat.connection.accepted
        - chat.message.created
        - chat.typing
        - chat.read
        - chat.price_offer.created
        - chat.price_accepted
        - chat.contract_linked
        - chat.room.closed
        - error
        - pong

    Accepted client messages:
        {"type": "ping"}
        {"type": "chat.message.send", "body": "..."}
        {"type": "chat.typing.start"}
        {"type": "chat.typing.stop"}
        {"type": "chat.read", "message_id": "..."}
        {"type": "chat.price_offer.send", "amount": "...", "currency": "IQD", "description": "..."}
    """

    # ------------------------------------------------------------------
    # Group helpers
    # ------------------------------------------------------------------
    CHAT_ROOM_GROUP_TPL = "service_chat_room_{room_id}"

    def _group_name(self):
        return self.CHAT_ROOM_GROUP_TPL.format(room_id=self.room_id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        if not user.is_authenticated:
            logger.info("Chat WebSocket rejected: unauthenticated")
            await self.close(code=4401)
            return

        # Extract room_id from path
        self.room_id = self._extract_room_id()
        if not self.room_id:
            logger.info("Chat WebSocket rejected: missing room_id")
            await self.close(code=4400)
            return

        # Verify room exists and user can participate
        room = await self._get_room()
        if room is None or not await self._can_participate(room, user):
            logger.info(
                "Chat WebSocket rejected: user %s not allowed in room %s",
                user.username, self.room_id,
            )
            await self.close(code=4403)
            return

        self.user = user
        self.room = room
        self.group_name = self._group_name()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Mark room as read on connect
        await self._mark_room_read()

        await self.send_json({
            "type": "chat.connection.accepted",
            "room_id": self.room_id,
            "unread_count": 0,
        })
        logger.debug(
            "Chat WebSocket connected: user=%s room=%s",
            user.username, self.room_id,
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name,
            )
        logger.debug(
            "Chat WebSocket disconnected: room=%s code=%s",
            getattr(self, "room_id", "unknown"), close_code,
        )

    # ------------------------------------------------------------------
    # Client message handlers
    # ------------------------------------------------------------------

    async def receive_json(self, content):
        msg_type = content.get("type", "")

        try:
            if msg_type == "ping":
                await self.send_json({"type": "pong"})

            elif msg_type == "chat.message.send":
                body = content.get("body", "").strip()
                if not body:
                    await self.send_json({"type": "error", "message": "Message body is required."})
                    return
                message, _ = await self._create_text_message(body)

            elif msg_type == "chat.typing.start":
                await self._broadcast_typing(is_typing=True)

            elif msg_type == "chat.typing.stop":
                await self._broadcast_typing(is_typing=False)

            elif msg_type == "chat.read":
                message_id = content.get("message_id", "")
                if message_id:
                    await self._mark_read(message_id)

            elif msg_type == "chat.price_offer.send":
                amount = content.get("amount")
                currency = content.get("currency", "IQD")
                description = content.get("description", "")
                if not amount:
                    await self.send_json({"type": "error", "message": "Amount is required."})
                    return
                message, _ = await self._create_price_offer(amount, currency, description)

            else:
                logger.warning(
                    "Unsupported message type from user %s: %s",
                    self.scope["user"], msg_type,
                )
                await self.send_json({
                    "type": "error",
                    "message": f"Unsupported message type: {msg_type}",
                })

        except PermissionError as exc:
            await self.send_json({"type": "error", "message": str(exc)})
        except ValueError as exc:
            await self.send_json({"type": "error", "message": str(exc)})
        except Exception as exc:
            logger.error("Chat WebSocket error: %s", exc, exc_info=True)
            await self.send_json({"type": "error", "message": "Internal error."})

    # ------------------------------------------------------------------
    # Server-to-client event handlers
    # These are called by channel_layer.group_send from realtime helpers.
    # ------------------------------------------------------------------

    async def chat_message_created(self, event):
        """Deliver a new message to the client."""
        await self.send_json({
            "type": "chat.message.created",
            "payload": event.get("payload", {}),
        })

    async def chat_typing(self, event):
        """Deliver typing indicator."""
        await self.send_json({
            "type": "chat.typing",
            "user_id": event.get("user_id"),
            "username": event.get("username"),
            "is_typing": event.get("is_typing", False),
        })

    async def chat_read(self, event):
        """Deliver read receipt."""
        await self.send_json({
            "type": "chat.read",
            "user_id": event.get("user_id"),
            "username": event.get("username"),
            "message_id": event.get("message_id"),
        })

    async def chat_price_offer_created(self, event):
        """Deliver a new price offer."""
        await self.send_json({
            "type": "chat.price_offer.created",
            "payload": event.get("payload", {}),
        })

    async def chat_price_accepted(self, event):
        """Deliver price accepted event."""
        await self.send_json({
            "type": "chat.price_accepted",
            "payload": event.get("payload", {}),
        })

    async def chat_contract_linked(self, event):
        """Deliver contract linked event."""
        await self.send_json({
            "type": "chat.contract_linked",
            "room_id": event.get("room_id"),
            "contract_id": event.get("contract_id"),
            "contract_reference": event.get("contract_reference"),
        })

    async def chat_room_closed(self, event):
        """Deliver room closed event."""
        await self.send_json({
            "type": "chat.room.closed",
            "room_id": event.get("room_id"),
            "closed_by_id": event.get("closed_by_id"),
            "closed_at": event.get("closed_at"),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_room_id(self):
        """Extract room_id from the WebSocket path."""
        path = self.scope.get("path", "")
        # Expected: /ws/chat/rooms/<room_id>/
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[-2] == "rooms":
            return parts[-1]
        # Alternative: /ws/chat/<room_id>/
        if len(parts) >= 2 and parts[0] == "ws" and parts[1] == "chat":
            return parts[-1]
        return None

    @database_sync_to_async
    def _get_room(self):
        """Fetch room from DB."""
        try:
            return ServiceChatRoom.objects.get(id=self.room_id)
        except ServiceChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def _can_participate(self, room, user):
        """Check if user can participate."""
        return room.can_participate(user)

    @database_sync_to_async
    def _create_text_message(self, body):
        """Create a text message via service layer."""
        room = ServiceChatRoom.objects.get(id=self.room_id)
        return svc.create_message(room, self.user, body=body)

    @database_sync_to_async
    def _create_price_offer(self, amount, currency, description):
        """Create a price offer via service layer."""
        room = ServiceChatRoom.objects.get(id=self.room_id)
        return svc.create_price_offer(room, self.user, amount, currency, description)

    @database_sync_to_async
    def _mark_room_read(self):
        """Mark room as read on connect."""
        try:
            room = ServiceChatRoom.objects.get(id=self.room_id)
            svc.mark_room_read(room, self.user)
        except Exception as exc:
            logger.debug("Failed to mark room read on connect: %s", exc)

    async def _broadcast_typing(self, is_typing):
        """Broadcast typing indicator to the room group."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.typing",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "is_typing": is_typing,
            },
        )

    @database_sync_to_async
    def _mark_read(self, message_id):
        """Mark a specific message as read."""
        try:
            room = ServiceChatRoom.objects.get(id=self.room_id)
            svc.mark_room_read(room, self.user)
        except Exception as exc:
            logger.debug("Failed to mark read via WebSocket: %s", exc)
