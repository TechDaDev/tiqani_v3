"""
Background tasks for dealership app — cash-out expiry, threshold alerts, etc.

All tasks are safe to call synchronously in test/dev.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from dealership.models import (
    DealershipClientCashout,
    DealershipGuarantee,
    DealershipProfile,
)
from dealership.services import (
    calculate_net_exposure,
    calculate_usable_credit_limit,
)

logger = logging.getLogger(__name__)


@shared_task
def expire_old_cashout_codes_task():
    """
    Find cashouts with status 'code_issued' whose code_expires_at has passed,
    and mark them as 'expired'.

    Returns a summary dict.
    """
    now = timezone.now()
    expired = DealershipClientCashout.objects.filter(
        status=DealershipClientCashout.Status.CODE_ISSUED,
        code_expires_at__lt=now,
    )
    count = expired.count()
    expired.update(status=DealershipClientCashout.Status.EXPIRED)

    logger.info("Cash-out expiry: %d codes expired.", count)

    return {
        "task": "expire_old_cashout_codes",
        "expired_count": count,
    }


@shared_task
def send_dealership_threshold_alerts_task():
    """
    Check all active dealerships whose net exposure is near the credit limit.

    Sends alerts (via notification) when:
      net_exposure >= usable_credit_limit * 0.8 (approaching limit)
      net_exposure >= usable_credit_limit (already locked)

    Returns a summary dict.
    """
    from notification.services import notify_admins

    approaching = []
    locked = []

    for profile in DealershipProfile.objects.filter(
        active=True, suspended=False, blocked=False,
    ):
        usable_limit = calculate_usable_credit_limit(profile)
        if usable_limit <= 0:
            continue

        net_exp = calculate_net_exposure(profile)
        ratio = float(net_exp / usable_limit)

        if ratio >= 1.0:
            locked.append(profile)
        elif ratio >= 0.8:
            approaching.append(profile)

    # Notify admins about approaching dealerships
    for profile in approaching:
        notify_admins(
            notification_type="system",
            title=f"Dealership nearing limit: {profile.business_name}",
            message=(
                f"Net exposure is at {float(calculate_net_exposure(profile)):.1%} "
                f"of usable credit limit."
            ),
            target_type="dealership_profile",
            target_id=profile.id,
        )

    # Notify about locked dealerships
    for profile in locked:
        notify_admins(
            notification_type="system",
            title=f"Dealership locked: {profile.business_name}",
            message="Dealership has reached its financial limit and is locked.",
            target_type="dealership_profile",
            target_id=profile.id,
        )

    logger.info(
        "Threshold alerts: %d approaching limit, %d locked.",
        len(approaching), len(locked),
    )

    return {
        "task": "send_dealership_threshold_alerts",
        "approaching_count": len(approaching),
        "locked_count": len(locked),
    }


@shared_task
def send_dealership_guarantee_expiry_alerts_task():
    """
    Check guarantees expiring within the next 30 days.

    Returns a summary dict.
    """
    now = timezone.now()
    warning_window = now + timedelta(days=30)

    expiring = DealershipGuarantee.objects.filter(
        status=DealershipGuarantee.Status.VERIFIED,
        expires_at__isnull=False,
        expires_at__lte=warning_window,
        expires_at__gte=now,
    )

    count = expiring.count()

    for guarantee in expiring:
        from notification.services import create_notification
        create_notification(
            recipient=guarantee.dealership.user,
            notification_type="system",
            title="Guarantee expiring soon",
            message=(
                f"Your guarantee of {guarantee.total_guarantee_amount} IQD "
                f"expires on {guarantee.expires_at.date()}. "
                "Please renew to continue operations."
            ),
            target_type="dealership_guarantee",
            target_id=guarantee.id,
        )

    logger.info("Guarantee expiry alerts: %d guarantees expiring soon.", count)

    return {
        "task": "send_dealership_guarantee_expiry_alerts",
        "expiring_count": count,
    }
