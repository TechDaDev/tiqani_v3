"""
Background tasks for accounts app — email sending, OTP cleanup.

All tasks are safe to call synchronously in test/dev when CELERY_TASK_ALWAYS_EAGER=True.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Email tasks
# ------------------------------------------------------------------


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def send_otp_email_task(user_id, otp_code, email, purpose="verification"):
    """
    Send an OTP email in the background.

    This is a wrapper — the actual email sending logic should use
    the existing accounts.email_utils module. For now, it logs the
    intent and can be wired when email templates are finalized.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        logger.info(
            "Sending OTP email to %s (purpose=%s, code=******)",
            email, purpose,
        )
        # Delegate to existing email utility if available
        try:
            from accounts.email_utils import send_otp_email
            send_otp_email(user, otp_code, purpose)
        except ImportError:
            logger.warning(
                "accounts.email_utils not available — OTP email not sent to %s",
                email,
            )
    except User.DoesNotExist:
        logger.error("User %s not found — cannot send OTP email.", user_id)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_password_reset_email_task(user_id, email, reset_link):
    """Send password reset email in background."""
    logger.info("Sending password reset email to %s", email)
    try:
        from accounts.email_utils import send_password_reset_email
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        send_password_reset_email(user, reset_link)
    except Exception as exc:
        logger.error("Failed to send password reset email: %s", exc)
        raise


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def send_generic_email_task(subject, message, recipient_list, from_email=None):
    """Send a generic email in the background."""
    from django.core.mail import send_mail
    try:
        send_mail(
            subject,
            message,
            from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        logger.info("Generic email sent to %s", recipient_list)
    except Exception as exc:
        logger.error("Failed to send generic email: %s", exc)
        raise


# ------------------------------------------------------------------
# OTP cleanup
# ------------------------------------------------------------------


@shared_task
def cleanup_expired_otps_task():
    """
    Mark expired/unused OTPs older than OTP_CLEANUP_RETENTION_DAYS as used.

    This prevents OTP records from accumulating indefinitely while
    preserving recent active OTPs for validation.

    Returns a summary dict.
    """
    from accounts.models import OTPVerification

    retention_days = getattr(settings, "OTP_CLEANUP_RETENTION_DAYS", 7)
    cutoff = timezone.now() - timedelta(days=retention_days)

    # Count expired records
    expired = OTPVerification.objects.filter(
        is_used=False,
        created_at__lt=cutoff,
    )

    expired_count = expired.count()
    marked_count = expired.update(is_used=True)

    logger.info(
        "OTP cleanup: %d expired, %d marked used (retention=%d days)",
        expired_count, marked_count, retention_days,
    )

    return {
        "task": "cleanup_expired_otps",
        "expired_count": expired_count,
        "marked_count": marked_count,
        "retention_days": retention_days,
    }
