"""Business logic for the Offer lifecycle and atomic contract creation."""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

from contract.models import Contract
from contract.offer_models import Offer

logger = logging.getLogger(__name__)


def _check_technician_owns_offer(offer, user):
    """Raise PermissionError if user is not the offer's technician."""
    if offer.technician.user_id != user.id:
        raise PermissionError("Only the assigned technician can modify this offer.")


def _check_client_owns_request(offer, user):
    """Raise PermissionError if user is not the offer's client."""
    if offer.client.user_id != user.id:
        raise PermissionError("Only the request owner can review this offer.")


# ------------------------------------------------------------------
# Technician actions
# ------------------------------------------------------------------

def create_offer(service_request, user, data):
    """Create a new DRAFT offer for an accepted service request.

    Only the assigned technician can create offers.
    Only ACCEPTED requests are eligible.
    Returns the new Offer instance.
    """
    if service_request.technician.user_id != user.id:
        raise PermissionError("Only the assigned technician can create offers.")

    if service_request.status != service_request.Status.ACCEPTED:
        raise ValueError(
            f"Offers can only be created for accepted requests. "
            f"Current status: {service_request.status}"
        )

    offer = Offer.objects.create(
        service_request=service_request,
        amount=data["amount"],
        description=data["description"],
        duration_days=data.get("duration_days"),
        status=Offer.Status.DRAFT,
    )
    return offer


def update_offer(offer, user, data):
    """Update editable fields on a DRAFT offer."""
    _check_technician_owns_offer(offer, user)

    if not offer.can_edit():
        raise ValueError("Only draft offers can be edited.")

    if "amount" in data:
        offer.amount = data["amount"]
    if "description" in data:
        offer.description = data["description"]
    if "duration_days" in data:
        offer.duration_days = data.get("duration_days")

    offer.save()
    return offer


def submit_offer(offer, user):
    """Submit a DRAFT offer, making it visible to the client.

    Auto-withdraws any previous SUBMITTED offers on the same request.
    """
    _check_technician_owns_offer(offer, user)

    if offer.status != Offer.Status.DRAFT:
        raise ValueError(f"Cannot submit an offer with status '{offer.status}'.")

    with transaction.atomic():
        # Auto-withdraw previous submitted offers
        Offer.objects.filter(
            service_request=offer.service_request,
            status=Offer.Status.SUBMITTED,
        ).exclude(pk=offer.pk).update(status=Offer.Status.WITHDRAWN)

        offer.status = Offer.Status.SUBMITTED
        offer.save()

    # Notify client
    _notify_offer_submitted(offer)

    return offer


def withdraw_offer(offer, user):
    """Withdraw a SUBMITTED offer (technician only)."""
    _check_technician_owns_offer(offer, user)

    if not offer.can_withdraw():
        raise ValueError(f"Cannot withdraw an offer with status '{offer.status}'.")

    offer.status = Offer.Status.WITHDRAWN
    offer.save()

    _notify_offer_withdrawn(offer)

    return offer


# ------------------------------------------------------------------
# Client actions
# ------------------------------------------------------------------

def accept_offer(offer, user):
    """Accept a SUBMITTED offer and atomically create a draft Contract.

    - Validates the user is the request owner.
    - Validates offer is in SUBMITTED status.
    - Creates a minimal draft Contract with agreed values.
    - Both parties are marked as having accepted.
    - Returns (offer, contract) tuple.
    """
    _check_client_owns_request(offer, user)

    if offer.status != Offer.Status.SUBMITTED:
        raise ValueError(
            f"Cannot accept an offer with status '{offer.status}'. "
            f"Only submitted offers can be accepted."
        )

    with transaction.atomic():
        offer.status = Offer.Status.ACCEPTED
        offer.save()

        contract = Contract.objects.create(
            client=offer.client,
            technician=offer.technician,
            work_description=offer.description,
            agreed_amount=offer.amount,
            currency="IQD",
            status="draft",
        )
        # Mark both parties having accepted since the offer was agreed
        contract.client_accepted = True
        contract.technician_accepted = True
        # Save triggers auto-transition to pending_acceptance if fields are complete
        # But we keep it simple — just mark accepted, no stages/duration needed
        contract.save()

    _notify_offer_accepted(offer, contract)
    return offer, contract


def reject_offer(offer, user):
    """Reject a SUBMITTED offer."""
    _check_client_owns_request(offer, user)

    if offer.status != Offer.Status.SUBMITTED:
        raise ValueError(
            f"Cannot reject an offer with status '{offer.status}'. "
            f"Only submitted offers can be rejected."
        )

    offer.status = Offer.Status.REJECTED
    offer.save()

    _notify_offer_rejected(offer)

    return offer


# ------------------------------------------------------------------
# Notification helpers
# ------------------------------------------------------------------

def _notify_offer_submitted(offer):
    """Notify client that a new offer has been submitted."""
    try:
        from notification.services import create_notification
        from notification.models import Notification

        create_notification(
            recipient=offer.client.user,
            notification_type=Notification.Type.CONTRACT_PROPOSAL_SUBMITTED,
            title="New offer submitted",
            message=f"A technician has submitted an offer for your service request.",
            actor=offer.technician.user,
            target_type="offer",
            target_id=offer.id,
            target_url=f"/offers/{offer.id}",
        )
    except Exception as exc:
        logger.warning("Failed to send offer-submitted notification: %s", exc)


def _notify_offer_withdrawn(offer):
    """Notify client that the offer was withdrawn."""
    try:
        from notification.services import create_notification
        from notification.models import Notification

        create_notification(
            recipient=offer.client.user,
            notification_type=Notification.Type.SYSTEM,
            title="Offer withdrawn",
            message="The technician has withdrawn their offer.",
            actor=offer.technician.user,
            target_type="offer",
            target_id=offer.id,
            target_url=f"/offers/{offer.id}",
        )
    except Exception as exc:
        logger.warning("Failed to send offer-withdrawn notification: %s", exc)


def _notify_offer_accepted(offer, contract):
    """Notify technician that their offer was accepted and a contract created."""
    try:
        from notification.services import create_notification
        from notification.models import Notification

        create_notification(
            recipient=offer.technician.user,
            notification_type=Notification.Type.CONTRACT_ACCEPTED,
            title="Offer accepted — contract created",
            message="Your offer has been accepted. A contract has been created.",
            actor=offer.client.user,
            target_type="contract",
            target_id=contract.id,
            target_url=f"/contracts/{contract.id}",
        )
    except Exception as exc:
        logger.warning("Failed to send offer-accepted notification: %s", exc)


def _notify_offer_rejected(offer):
    """Notify technician that their offer was rejected."""
    try:
        from notification.services import create_notification
        from notification.models import Notification

        create_notification(
            recipient=offer.technician.user,
            notification_type=Notification.Type.SYSTEM,
            title="Offer rejected",
            message="The client has rejected your offer.",
            actor=offer.client.user,
            target_type="offer",
            target_id=offer.id,
            target_url=f"/offers/{offer.id}",
        )
    except Exception as exc:
        logger.warning("Failed to send offer-rejected notification: %s", exc)
