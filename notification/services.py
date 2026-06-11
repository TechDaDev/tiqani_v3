"""Notification service layer — creation helpers and event integrations."""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Notification, ActivityLog

logger = logging.getLogger(__name__)

User = get_user_model()


# ------------------------------------------------------------------
# Core creation helpers
# ------------------------------------------------------------------

def create_notification(
    recipient,
    notification_type,
    title,
    message='',
    actor=None,
    target_type='',
    target_id=None,
    target_url='',
    metadata=None,
):
    """Create a single notification. Returns Notification or None on error."""
    if not recipient:
        return None
    try:
        notif = Notification.objects.create(
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
        return notif
    except Exception as exc:
        logger.warning("Failed to create notification: %s", exc)
        return None


def create_notifications_bulk(recipients, notification_type, title, message='', **kwargs):
    """Create notifications for multiple recipients. Wraps each in try/except."""
    results = []
    for r in recipients:
        n = create_notification(r, notification_type, title, message, **kwargs)
        results.append(n)
    return results


def mark_notification_read(notification, user):
    """Mark a notification as read, verifying ownership."""
    if notification.recipient != user:
        return False
    notification.mark_read()
    return True


def mark_all_notifications_read(user):
    """Mark all unread notifications for a user as read."""
    now = timezone.now()
    updated = Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=now,
    )
    return updated


def create_activity(verb, actor=None, target_type='', target_id=None, target_repr='', audience='system', metadata=None):
    """Create an activity log entry."""
    try:
        return ActivityLog.objects.create(
            verb=verb,
            actor=actor,
            target_type=target_type,
            target_id=target_id,
            target_repr=target_repr,
            audience=audience,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.warning("Failed to create activity log: %s", exc)
        return None


def notify_admins(notification_type, title, message='', actor=None, target_type='', target_id=None, metadata=None):
    """Send a notification to all staff/admin users."""
    admins = User.objects.filter(is_staff=True)
    return create_notifications_bulk(admins, notification_type, title, message,
                                     actor=actor, target_type=target_type, target_id=target_id,
                                     metadata=metadata)


# ------------------------------------------------------------------
# Contract event helpers
# ------------------------------------------------------------------

def notify_contract_created(contract, actor):
    """Notify technician that a contract has been created/drafted."""
    tech_user = contract.technician.user
    n = create_notification(
        recipient=tech_user,
        notification_type=Notification.Type.CONTRACT_CREATED,
        title="New contract request",
        message=f"{actor.username} has created a contract for your services.",
        actor=actor,
        target_type='contract',
        target_id=contract.id,
        target_url=f'/contracts/{contract.id}',
    )
    create_activity(
        verb='contract_created', actor=actor,
        target_type='contract', target_id=contract.id,
        target_repr=str(contract),
        audience='admin',
    )
    return n


def notify_contract_proposal_submitted(contract, actor):
    """Notify client that the technician submitted a proposal."""
    client_user = contract.client.user
    n = create_notification(
        recipient=client_user,
        notification_type=Notification.Type.CONTRACT_PROPOSAL_SUBMITTED,
        title="Proposal submitted",
        message=f"{actor.username} has submitted a proposal for your contract.",
        actor=actor,
        target_type='contract', target_id=contract.id,
        target_url=f'/contracts/{contract.id}',
    )
    create_activity(
        verb='contract_proposal_submitted', actor=actor,
        target_type='contract', target_id=contract.id,
        target_repr=str(contract), audience='admin',
    )
    return n


def notify_contract_accepted(contract, actor, other_participant):
    """Notify the other participant that the contract was accepted."""
    n = create_notification(
        recipient=other_participant,
        notification_type=Notification.Type.CONTRACT_ACCEPTED,
        title="Contract accepted",
        message=f"{actor.username} has accepted the contract.",
        actor=actor,
        target_type='contract', target_id=contract.id,
        target_url=f'/contracts/{contract.id}',
    )
    return n


def notify_contract_in_progress(contract):
    """Notify both parties that the contract is now in progress."""
    for user in [contract.client.user, contract.technician.user]:
        create_notification(
            recipient=user,
            notification_type=Notification.Type.CONTRACT_ACCEPTED,
            title="Contract in progress",
            message="Both parties have accepted. The contract is now in progress.",
            actor=None,
            target_type='contract', target_id=contract.id,
            target_url=f'/contracts/{contract.id}',
        )
    create_activity(
        verb='contract_in_progress', actor=None,
        target_type='contract', target_id=contract.id,
        target_repr=str(contract), audience='admin',
    )


def notify_contract_canceled(contract, actor, other_participant=None, reason=''):
    """Notify the other participant that the contract was canceled."""
    if other_participant:
        create_notification(
            recipient=other_participant,
            notification_type=Notification.Type.CONTRACT_CANCELED,
            title="Contract canceled",
            message=f"Contract was canceled by {actor.username}. {reason}",
            actor=actor,
            target_type='contract', target_id=contract.id,
        )
    create_activity(
        verb='contract_canceled', actor=actor,
        target_type='contract', target_id=contract.id,
        target_repr=str(contract), audience='admin',
    )


def notify_contract_completed(contract, actor=None):
    """Notify both parties that the contract is completed."""
    for user in [contract.client.user, contract.technician.user]:
        create_notification(
            recipient=user,
            notification_type=Notification.Type.CONTRACT_COMPLETED,
            title="Contract completed",
            message="All stages have been approved. The contract is now complete.",
            actor=actor,
            target_type='contract', target_id=contract.id,
            target_url=f'/contracts/{contract.id}',
        )
    # Extra: remind client they can review
    create_notification(
        recipient=contract.client.user,
        notification_type=Notification.Type.CONTRACT_COMPLETED,
        title="Review your technician",
        message="Your contract is complete! Leave a review for your technician.",
        actor=None,
        target_type='contract', target_id=contract.id,
        target_url=f'/reviews/create?contract={contract.id}',
    )
    create_activity(
        verb='contract_completed', actor=actor,
        target_type='contract', target_id=contract.id,
        target_repr=str(contract), audience='admin',
    )


def notify_stage_submitted(stage, actor):
    """Notify client that a stage was submitted for approval."""
    contract = stage.contract
    n = create_notification(
        recipient=contract.client.user,
        notification_type=Notification.Type.STAGE_SUBMITTED,
        title="Stage submitted",
        message=f"A stage has been submitted for your approval.",
        actor=actor,
        target_type='contract_stage', target_id=stage.id,
        target_url=f'/contracts/{contract.id}',
    )
    create_activity(
        verb='stage_submitted', actor=actor,
        target_type='contract_stage', target_id=stage.id,
        target_repr=f"Stage {stage.stage_number} of {contract}", audience='admin',
    )
    return n


def notify_stage_approved(stage, actor):
    """Notify technician that a stage was approved."""
    contract = stage.contract
    n = create_notification(
        recipient=contract.technician.user,
        notification_type=Notification.Type.STAGE_APPROVED,
        title="Stage approved",
        message=f"Stage {stage.stage_number} has been approved.",
        actor=actor,
        target_type='contract_stage', target_id=stage.id,
        target_url=f'/contracts/{contract.id}',
    )
    create_activity(
        verb='stage_approved', actor=actor,
        target_type='contract_stage', target_id=stage.id,
        target_repr=f"Stage {stage.stage_number} of {contract}", audience='admin',
    )
    return n


def notify_extension_requested(ext_request, actor):
    """Notify client about an extension request."""
    contract = ext_request.contract
    n = create_notification(
        recipient=contract.client.user,
        notification_type=Notification.Type.EXTENSION_REQUESTED,
        title="Extension requested",
        message=f"Technician requested a {ext_request.requested_days}-day extension.",
        actor=actor,
        target_type='extension_request', target_id=ext_request.id,
        target_url=f'/contracts/{contract.id}',
    )
    return n


def notify_extension_approved(ext_request, actor):
    """Notify technician that extension was approved."""
    contract = ext_request.contract
    n = create_notification(
        recipient=contract.technician.user,
        notification_type=Notification.Type.EXTENSION_APPROVED,
        title="Extension approved",
        message=f"Your extension request for {ext_request.requested_days} days has been approved.",
        actor=actor,
        target_type='extension_request', target_id=ext_request.id,
    )
    return n


def notify_extension_rejected(ext_request, actor):
    """Notify technician that extension was rejected."""
    contract = ext_request.contract
    n = create_notification(
        recipient=contract.technician.user,
        notification_type=Notification.Type.EXTENSION_REJECTED,
        title="Extension rejected",
        message=f"Your extension request for {ext_request.requested_days} days was rejected.",
        actor=actor,
        target_type='extension_request', target_id=ext_request.id,
    )
    return n


# ------------------------------------------------------------------
# Review event helpers
# ------------------------------------------------------------------

def notify_review_created(review, actor):
    """Notify technician that they received a review."""
    n = create_notification(
        recipient=review.technician.user,
        notification_type=Notification.Type.REVIEW_CREATED,
        title="New review received",
        message=f"You received a {review.rating}/5 review from {actor.username}.",
        actor=actor,
        target_type='review', target_id=review.id,
        target_url=f'/reviews/{review.id}',
    )
    create_activity(
        verb='review_created', actor=actor,
        target_type='review', target_id=review.id,
        target_repr=f"{review.rating}/5 review", audience='admin',
    )
    return n


def notify_review_responded(review, actor):
    """Notify reviewer that the technician responded."""
    n = create_notification(
        recipient=review.reviewer,
        notification_type=Notification.Type.REVIEW_RESPONDED,
        title="Technician responded",
        message=f"{actor.username} has responded to your review.",
        actor=actor,
        target_type='review', target_id=review.id,
        target_url=f'/reviews/{review.id}',
    )
    create_activity(
        verb='review_responded', actor=actor,
        target_type='review', target_id=review.id,
        target_repr=f"Response to review", audience='admin',
    )
    return n


def notify_review_reported(review, actor):
    """Notify admins when a review is reported."""
    notify_admins(
        notification_type=Notification.Type.REVIEW_REPORTED,
        title="Review reported",
        message=f"A review was reported by {actor.username}.",
        actor=actor,
        target_type='review', target_id=review.id,
    )
    create_activity(
        verb='review_reported', actor=actor,
        target_type='review', target_id=review.id,
        target_repr=f"Review reported", audience='admin',
    )


def notify_review_moderated(review, actor, action):
    """Notify review participants about moderation action."""
    for user in [review.reviewer, review.technician.user]:
        if user == actor:
            continue
        create_notification(
            recipient=user,
            notification_type=Notification.Type.REVIEW_MODERATED,
            title="Review moderated",
            message=f"A review was {action} by {actor.username}.",
            actor=actor,
            target_type='review', target_id=review.id,
            target_url=f'/reviews/{review.id}',
        )
    create_activity(
        verb=f'review_{action}', actor=actor,
        target_type='review', target_id=review.id,
        target_repr=f"Review {action}", audience='admin',
    )


# ------------------------------------------------------------------
# Wallet / payment event helpers
# ------------------------------------------------------------------

def notify_wallet_transaction(wallet_transaction, actor=None):
    """Notify wallet owner about an important transaction."""
    wallet = wallet_transaction.wallet
    user = wallet.user
    tx_type = wallet_transaction.transaction_type
    n = create_notification(
        recipient=user,
        notification_type=Notification.Type.WALLET_TRANSACTION,
        title=f"Wallet {tx_type}",
        message=f"Your wallet has a {tx_type} of {wallet_transaction.amount} IQD.",
        actor=actor,
        target_type='wallet_transaction', target_id=wallet_transaction.id,
    )
    create_activity(
        verb=f'wallet_{tx_type}', actor=actor or user,
        target_type='wallet_transaction', target_id=wallet_transaction.id,
        audience='admin',
    )
    return n


def notify_payment_intent_created(payment_intent, actor=None):
    """Notify user about a payment intent."""
    n = create_notification(
        recipient=payment_intent.user,
        notification_type=Notification.Type.PAYMENT_INTENT_CREATED,
        title="Payment intent created",
        message=f"A {payment_intent.amount} IQD payment intent has been created.",
        actor=actor,
        target_type='payment_intent', target_id=payment_intent.id,
    )
    create_activity(
        verb='payment_intent_created', actor=actor or payment_intent.user,
        target_type='payment_intent', target_id=payment_intent.id,
        audience='admin',
    )
    return n


def notify_payment_intent_paid(payment_intent, actor=None):
    """Notify user that their payment intent was marked paid."""
    n = create_notification(
        recipient=payment_intent.user,
        notification_type=Notification.Type.PAYMENT_INTENT_PAID,
        title="Payment completed",
        message=f"Your {payment_intent.amount} IQD payment has been recorded.",
        actor=actor,
        target_type='payment_intent', target_id=payment_intent.id,
    )
    create_activity(
        verb='payment_intent_paid', actor=actor or payment_intent.user,
        target_type='payment_intent', target_id=payment_intent.id,
        audience='admin',
    )
    return n


def notify_withdrawal_requested(withdrawal_request, actor):
    """Notify admins about a new withdrawal request."""
    notify_admins(
        notification_type=Notification.Type.WITHDRAWAL_REQUESTED,
        title="Withdrawal request",
        message=f"{actor.username} requested a withdrawal of {withdrawal_request.amount} IQD.",
        actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
    )
    create_activity(
        verb='withdrawal_requested', actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
        audience='admin',
    )


def notify_withdrawal_approved(withdrawal_request, actor):
    """Notify the requester that their withdrawal was approved."""
    n = create_notification(
        recipient=withdrawal_request.user,
        notification_type=Notification.Type.WITHDRAWAL_APPROVED,
        title="Withdrawal approved",
        message=f"Your withdrawal of {withdrawal_request.amount} IQD has been approved.",
        actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
    )
    create_activity(
        verb='withdrawal_approved', actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
        audience='admin',
    )
    return n


def notify_withdrawal_rejected(withdrawal_request, actor):
    """Notify the requester that their withdrawal was rejected."""
    n = create_notification(
        recipient=withdrawal_request.user,
        notification_type=Notification.Type.WITHDRAWAL_REJECTED,
        title="Withdrawal rejected",
        message=f"Your withdrawal of {withdrawal_request.amount} IQD was rejected.",
        actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
    )
    create_activity(
        verb='withdrawal_rejected', actor=actor,
        target_type='withdrawal_request', target_id=withdrawal_request.id,
        audience='admin',
    )
    return n


# ------------------------------------------------------------------
# Technician admin helpers
# ------------------------------------------------------------------

def notify_technician_approved(technician_profile, actor):
    """Notify technician they were approved by admin."""
    n = create_notification(
        recipient=technician_profile.user,
        notification_type=Notification.Type.TECHNICIAN_APPROVED,
        title="Profile approved",
        message="Your technician profile has been approved! You can now accept contracts.",
        actor=actor,
        target_type='technician_profile', target_id=technician_profile.id,
    )
    create_activity(
        verb='technician_approved', actor=actor,
        target_type='technician_profile', target_id=technician_profile.id,
        target_repr=str(technician_profile), audience='admin',
    )
    return n


def notify_technician_rejected(technician_profile, actor):
    """Notify technician their profile was rejected."""
    n = create_notification(
        recipient=technician_profile.user,
        notification_type=Notification.Type.TECHNICIAN_REJECTED,
        title="Profile not approved",
        message="Your technician profile has not been approved. Please check your details.",
        actor=actor,
        target_type='technician_profile', target_id=technician_profile.id,
    )
    create_activity(
        verb='technician_rejected', actor=actor,
        target_type='technician_profile', target_id=technician_profile.id,
        target_repr=str(technician_profile), audience='admin',
    )
    return n
