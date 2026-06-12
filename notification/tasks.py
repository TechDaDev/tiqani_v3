"""
Background tasks for notifications — async creation, digests, cleanup.

These tasks are safe to call from anywhere but financial transactions
must NOT depend on notification task success.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
    acks_late=True,
)
def create_notification_async(
    recipient_id,
    notification_type,
    title,
    message="",
    actor_id=None,
    target_type="",
    target_id=None,
    target_url="",
    metadata=None,
):
    """
    Create a notification in the background.

    Financial/wallet transactions should NOT depend on this task's success.
    Use transaction.on_commit to schedule when the DB transaction is confirmed.
    """
    from django.contrib.auth import get_user_model
    from notification.models import Notification

    User = get_user_model()

    try:
        recipient = User.objects.get(id=recipient_id)
        actor = User.objects.get(id=actor_id) if actor_id else None

        Notification.objects.create(
            recipient=recipient,
            actor=actor,
            notification_type=notification_type,
            title=title,
            message=message,
            target_type=target_type,
            target_id=target_id,
            target_url=target_url,
            metadata=metadata or {},
        )
    except User.DoesNotExist:
        logger.warning(
            "Cannot create notification: recipient %s not found.",
            recipient_id,
        )
    except Exception as exc:
        logger.error("Failed to create notification async: %s", exc)
        raise


@shared_task
def cleanup_old_read_notifications_task(dry_run=True):
    """
    Archive/delete read notifications older than NOTIFICATION_RETENTION_DAYS.

    Default retention: 180 days.
    dry_run=True: report what would be deleted without actually deleting.
    Returns a summary dict.
    """
    retention_days = getattr(settings, "NOTIFICATION_RETENTION_DAYS", 180)
    cutoff = timezone.now() - timedelta(days=retention_days)

    old_read = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff,
    )

    count = old_read.count()

    if not dry_run:
        deleted, _ = old_read.delete()
        action = "deleted"
        affected = deleted
    else:
        action = "would delete"
        affected = count

    logger.info(
        "Notification cleanup (dry_run=%s): %s %d notifications older than %d days",
        dry_run, action, affected, retention_days,
    )

    return {
        "task": "cleanup_old_read_notifications",
        "dry_run": dry_run,
        "affected_count": affected,
        "retention_days": retention_days,
        "action": action,
    }


# Import here to avoid circular import at module level
from notification.models import Notification  # noqa: E402, F811
