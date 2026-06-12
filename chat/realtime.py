"""
Realtime chat helpers — bridge between Django operations and the Channels layer.

All functions are safe to call from sync code. They fail silently with logging
if the channel layer is unavailable.
"""

import json
import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Group name template — must match chat/consumers.py
CHAT_ROOM_GROUP_TPL = "service_chat_room_{room_id}"


def get_chat_room_group(room_id):
    """Return the Channels group name for a chat room."""
    return CHAT_ROOM_GROUP_TPL.format(room_id=room_id)


def _send_to_group(group_name, event):
    """
    Send an event dict to a Channels group.
    Fails silently if channel layer is not available.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.debug("Channel layer not available — skipping realtime event.")
            return False
        async_to_sync(channel_layer.group_send)(group_name, event)
        return True
    except Exception as exc:
        logger.warning("Failed to send realtime event to %s: %s", group_name, exc)
        return False


def _message_to_payload(message):
    """Convert a ServiceChatMessage to a serializable dict."""
    return {
        "id": str(message.id),
        "room_id": str(message.room_id),
        "sender_id": str(message.sender_id),
        "sender_username": message.sender.username,
        "message_type": message.message_type,
        "body": message.body,
        "safe_preview": message.safe_preview(),
        "attachment_name": message.attachment_name or "",
        "attachment_url": message.attachment.url if message.attachment else "",
        "price_amount": str(message.price_amount) if message.price_amount else None,
        "price_currency": message.price_currency,
        "metadata": message.metadata,
        "is_deleted": message.is_deleted,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "created_at": message.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def send_chat_message_created(message):
    """Broadcast a new chat message to all room participants."""
    group = get_chat_room_group(message.room_id)
    return _send_to_group(group, {
        "type": "chat.message.created",
        "payload": _message_to_payload(message),
    })


def send_chat_typing(room_id, user, is_typing):
    """Broadcast typing indicator to the room."""
    group = get_chat_room_group(room_id)
    return _send_to_group(group, {
        "type": "chat.typing",
        "user_id": str(user.id),
        "username": user.username,
        "is_typing": is_typing,
    })


def send_chat_read(room_id, user, message_id):
    """Broadcast read receipt to the room."""
    group = get_chat_room_group(room_id)
    return _send_to_group(group, {
        "type": "chat.read",
        "user_id": str(user.id),
        "username": user.username,
        "message_id": message_id,
    })


def send_price_offer_created(message):
    """Broadcast a new price offer to room participants."""
    group = get_chat_room_group(message.room_id)
    return _send_to_group(group, {
        "type": "chat.price_offer.created",
        "payload": _message_to_payload(message),
    })


def send_price_accepted(message):
    """Broadcast price accepted event to room participants."""
    group = get_chat_room_group(message.room_id)
    return _send_to_group(group, {
        "type": "chat.price_accepted",
        "payload": _message_to_payload(message),
    })


def send_contract_linked(room, contract):
    """Broadcast contract linked event to room participants."""
    group = get_chat_room_group(room.id)
    return _send_to_group(group, {
        "type": "chat.contract_linked",
        "room_id": str(room.id),
        "contract_id": str(contract.id),
        "contract_reference": contract.contract_reference,
    })


def send_room_closed(room):
    """Broadcast room closed event to participants."""
    group = get_chat_room_group(room.id)
    return _send_to_group(group, {
        "type": "chat.room.closed",
        "room_id": str(room.id),
        "closed_by_id": str(room.closed_by_id) if room.closed_by_id else None,
        "closed_at": room.closed_at.isoformat() if room.closed_at else None,
    })
