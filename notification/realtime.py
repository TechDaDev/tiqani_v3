"""
Realtime notification helpers — bridge between Django model operations
and the Channels channel layer.

All functions are safe to call from sync code (views, services, tasks).
If the channel layer is unavailable, they fail silently with logging.
"""

import json
import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# Group name template — must match notification/consumers.py
USER_GROUP_TPL = "user_notifications_{user_id}"


def get_user_notification_group(user_id):
    """Return the Channels group name for a user's notifications."""
    return USER_GROUP_TPL.format(user_id=user_id)


def _send_to_group(group_name, event):
    """
    Send an event dict to a Channels group.

    Fails silently with a log warning if channel layer is not available.
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


def send_realtime_notification(user_id, payload):
    """
    Send a ``notification.created`` event to a specific user.

    Args:
        user_id: The recipient user's ID (UUID or int).
        payload: Dict with notification data (id, title, message, etc.).
    """
    group = get_user_notification_group(user_id)
    return _send_to_group(group, {
        "type": "notification.created",
        "payload": payload,
    })


def broadcast_unread_count(user_id):
    """
    Send a ``notification.unread_count`` event to a specific user.
    The count is fetched from the database.
    """
    group = get_user_notification_group(user_id)

    try:
        from notification.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        count = Notification.unread_count_for_user(user)
    except Exception as exc:
        logger.warning("Failed to compute unread count for %s: %s", user_id, exc)
        count = 0

    return _send_to_group(group, {
        "type": "notification.unread_count",
        "unread_count": count,
    })


def send_notification_created(notification):
    """
    Convenience wrapper: send a realtime notification created event
    from a Notification model instance.

    Should be called from ``transaction.on_commit`` to ensure the
    notification is persisted before the event fires.
    """
    user_id = notification.recipient_id
    payload = {
        "id": str(notification.id),
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at else None
        ),
        "target_type": notification.target_type,
        "target_id": (
            str(notification.target_id) if notification.target_id else None
        ),
        "target_url": notification.target_url or "",
    }
    if notification.actor_id:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            actor = User.objects.get(id=notification.actor_id)
            payload["actor_name"] = actor.get_full_name() or actor.username
        except Exception:
            pass

    return send_realtime_notification(user_id, payload)


def send_marked_read_event(user_id, notification_id):
    """Send a ``notification.marked_read`` event."""
    group = get_user_notification_group(user_id)
    return _send_to_group(group, {
        "type": "notification.marked_read",
        "notification_id": str(notification_id),
    })


def send_marked_unread_event(user_id, notification_id):
    """Send a ``notification.marked_unread`` event."""
    group = get_user_notification_group(user_id)
    return _send_to_group(group, {
        "type": "notification.marked_unread",
        "notification_id": str(notification_id),
    })


def send_bulk_read_event(user_id, updated_count):
    """Send a ``notification.bulk_read`` event."""
    group = get_user_notification_group(user_id)
    return _send_to_group(group, {
        "type": "notification.bulk_read",
        "updated": updated_count,
    })


def send_dealership_alert(user_id, payload):
    """
    Send a ``dealership.alert`` event to a specific user.

    Used for financial threshold alerts, cash-out status changes,
    guarantee expiry warnings, etc.
    """
    group = get_user_notification_group(user_id)
    return _send_to_group(group, {
        "type": "dealership.alert",
        "payload": payload,
    })
