"""
Chat service layer — business logic for rooms, messages, price offers,
contract linking, and realtime event dispatch.

All functions are safe to call from views, consumers, or tasks.
Realtime events use transaction.on_commit to ensure DB consistency.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract
from notification.services import create_notification
from notification.models import Notification

from .models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_read_state(room, user):
    """Get or create a read state entry for a user in a room."""
    read_state, created = ServiceChatReadState.objects.get_or_create(
        room=room,
        user=user,
        defaults={"unread_count": 0},
    )
    return read_state


def _increment_unread(room, exclude_user):
    """Increment unread count for all participants except the sender."""
    participants = []
    if hasattr(exclude_user, "client_profile"):
        participants.append(room.technician.user)
    elif hasattr(exclude_user, "technician_profile"):
        participants.append(room.client.user)
    else:
        # If we can't determine, increment for both
        participants = [room.client.user, room.technician.user]
        participants = [u for u in participants if u != exclude_user]

    for user in participants:
        read_state, _ = ServiceChatReadState.objects.get_or_create(
            room=room,
            user=user,
            defaults={"unread_count": 0},
        )
        read_state.unread_count = models.F("unread_count") + 1
        read_state.save(update_fields=["unread_count", "updated_at"])


# Avoid circular import for the above
from django.db import models as db_models


# ---------------------------------------------------------------------------
# Room management
# ---------------------------------------------------------------------------

def get_or_create_chat_room(client_user, technician_profile, created_by=None):
    """
    Get an existing active room or create a new OPEN room.

    Args:
        client_user: The client CustomUser instance.
        technician_profile: The TechnicianProfile instance.
        created_by: The user creating the room (defaults to client_user).

    Returns:
        (ServiceChatRoom, created: bool)
    """
    if not hasattr(client_user, "client_profile"):
        raise ValueError("User must have a client profile.")

    client_profile = client_user.client_profile

    if client_profile.user_id == technician_profile.user_id:
        raise ValueError("Client cannot start a room with themselves.")

    if created_by is None:
        created_by = client_user

    # Check for existing active room
    existing = ServiceChatRoom.objects.filter(
        client=client_profile,
        technician=technician_profile,
        status__in=[
            ServiceChatRoom.Status.OPEN,
            ServiceChatRoom.Status.PROPOSAL_CREATED,
            ServiceChatRoom.Status.CONTRACT_LINKED,
        ],
    ).first()

    if existing:
        return existing, False

    # Create new room
    room = ServiceChatRoom.objects.create(
        client=client_profile,
        technician=technician_profile,
        created_by=created_by,
        status=ServiceChatRoom.Status.OPEN,
    )
    return room, True


def get_or_create_room_for_request(service_request, created_by=None):
    """
    Get an existing room linked to a service request, or create a new one.

    The room is created between the request's client and technician.
    Only works for ACCEPTED requests (negotiation stage).

    Returns:
        (ServiceChatRoom, created: bool)
    """
    from servicerequest.models import ServiceRequest

    if service_request.status not in (ServiceRequest.Status.ACCEPTED, ServiceRequest.Status.PENDING):
        raise ValueError("Service request must be accepted or pending to create a conversation.")

    # Check if room already exists for this request
    existing = ServiceChatRoom.objects.filter(service_request=service_request).first()
    if existing:
        return existing, False

    # Check if an active room already exists between these participants
    existing_room = ServiceChatRoom.objects.filter(
        client=service_request.client,
        technician=service_request.technician,
        status__in=[
            ServiceChatRoom.Status.OPEN,
            ServiceChatRoom.Status.PROPOSAL_CREATED,
            ServiceChatRoom.Status.CONTRACT_LINKED,
        ],
    ).first()

    if existing_room:
        # Link the existing room to this request
        existing_room.service_request = service_request
        existing_room.save(update_fields=["service_request"])
        return existing_room, False

    # Create new room
    room = ServiceChatRoom.objects.create(
        client=service_request.client,
        technician=service_request.technician,
        service_request=service_request,
        created_by=created_by or service_request.client.user,
        status=ServiceChatRoom.Status.OPEN,
    )
    return room, True


def get_room_queryset_for_user(user):
    """
    Return rooms where user is a participant.
    Staff/admin see all rooms.
    """
    if user.is_staff:
        return ServiceChatRoom.objects.all().select_related(
            "client__user", "technician__user"
        )

    qs = ServiceChatRoom.objects.none()
    if hasattr(user, "client_profile"):
        qs = qs | ServiceChatRoom.objects.filter(client=user.client_profile)
    if hasattr(user, "technician_profile"):
        qs = qs | ServiceChatRoom.objects.filter(technician=user.technician_profile)

    return qs.select_related("client__user", "technician__user").distinct()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def create_message(room, sender, body=None, message_type="TEXT", attachment=None,
                   attachment_name="", attachment_size=None, attachment_content_type="",
                   price_amount=None, price_currency="IQD", metadata=None):
    """
    Create a message in a room, update room state, and trigger realtime events.

    Returns (ServiceChatMessage, created: bool)
    """
    if not room.can_send(sender):
        raise PermissionError("User cannot send messages in this room.")

    message = ServiceChatMessage(
        room=room,
        sender=sender,
        message_type=message_type,
        body=body or "",
        attachment=attachment,
        attachment_name=attachment_name,
        attachment_size=attachment_size,
        attachment_content_type=attachment_content_type,
        price_amount=price_amount,
        price_currency=price_currency,
        metadata=metadata or {},
    )

    with transaction.atomic():
        message.save()
        room.last_message_at = timezone.now()
        room.save(update_fields=["last_message_at", "updated_at"])
        _update_unread_counts(room, sender)

        transaction.on_commit(lambda: _notify_message_created(message))
        transaction.on_commit(lambda: _realtime_message_created(message))

    return message, True


def _update_unread_counts(room, sender):
    """Increment unread count for the other participant."""
    other_user = room.other_participant(sender)
    if other_user:
        read_state, _ = ServiceChatReadState.objects.get_or_create(
            room=room,
            user=other_user,
            defaults={"unread_count": 0},
        )
        ServiceChatReadState.objects.filter(
            room=room, user=other_user
        ).update(
            unread_count=db_models.F("unread_count") + 1,
            updated_at=timezone.now(),
        )


def _notify_message_created(message):
    """Send push/in-app notification for the message."""
    room = message.room
    other_user = room.other_participant(message.sender)
    if not other_user:
        return

    notification_type = Notification.Type.SYSTEM
    title = f"New message from {message.sender.username}"
    body_preview = message.safe_preview()

    if message.message_type == ServiceChatMessage.MessageType.PRICE_OFFER:
        notification_type = Notification.Type.CONTRACT_PROPOSAL_SUBMITTED
        title = f"Price offer from {message.sender.username}"
        body_preview = f"Amount: {message.price_amount} {message.price_currency}"
    elif message.message_type == ServiceChatMessage.MessageType.PRICE_ACCEPTED:
        notification_type = Notification.Type.CONTRACT_ACCEPTED
        title = f"{message.sender.username} accepted your price offer"

    try:
        create_notification(
            recipient=other_user,
            notification_type=notification_type,
            title=title,
            message=body_preview,
            actor=message.sender,
            target_type="chat_room",
            target_id=room.id,
            target_url=f"/chat/rooms/{room.id}",
            metadata={"room_id": str(room.id), "message_id": str(message.id)},
        )
    except Exception as exc:
        logger.warning("Failed to notify chat message: %s", exc)


def _realtime_message_created(message):
    """Broadcast message via Channels."""
    try:
        from .realtime import send_chat_message_created
        send_chat_message_created(message)
    except Exception as exc:
        logger.debug("Realtime message broadcast skipped: %s", exc)


# ---------------------------------------------------------------------------
# Price offers
# ---------------------------------------------------------------------------

def create_price_offer(room, technician_user, amount, currency="IQD", description=""):
    """
    Technician creates a price offer in the room.

    Sets room status to PROPOSAL_CREATED.
    """
    if not hasattr(technician_user, "technician_profile"):
        raise PermissionError("Only technicians can send price offers.")

    if technician_user.technician_profile != room.technician:
        raise PermissionError("Technician is not a participant in this room.")

    metadata = {"description": description} if description else {}

    message = ServiceChatMessage(
        room=room,
        sender=technician_user,
        message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
        body=description or "",
        price_amount=Decimal(str(amount)),
        price_currency=currency,
        metadata=metadata,
    )

    with transaction.atomic():
        message.save()
        # Update room status
        if room.status == ServiceChatRoom.Status.OPEN:
            room.status = ServiceChatRoom.Status.PROPOSAL_CREATED
        room.last_message_at = timezone.now()
        room.save(update_fields=["status", "last_message_at", "updated_at"])
        _update_unread_counts(room, technician_user)

        transaction.on_commit(lambda: _notify_message_created(message))
        transaction.on_commit(lambda: _realtime_price_offer_created(message))

    return message, True


def _realtime_price_offer_created(message):
    """Broadcast price offer via Channels."""
    try:
        from .realtime import send_price_offer_created
        send_price_offer_created(message)
    except Exception as exc:
        logger.debug("Realtime price offer broadcast skipped: %s", exc)


def accept_price_offer(room, client_user, message_id):
    """
    Client accepts a price offer in the room.

    Creates a PRICE_ACCEPTED message and updates room state.
    Returns the accepted message that was referenced.
    """
    if not hasattr(client_user, "client_profile"):
        raise PermissionError("Only clients can accept price offers.")

    if client_user.client_profile != room.client:
        raise PermissionError("Client is not a participant in this room.")

    # Find the price offer message
    try:
        offer_msg = ServiceChatMessage.objects.get(
            id=message_id,
            room=room,
            message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
            is_deleted=False,
        )
    except ServiceChatMessage.DoesNotExist:
        raise ValueError("Price offer not found or has been deleted.")

    metadata = {
        "accepted_offer_id": str(offer_msg.id),
        "accepted_amount": str(offer_msg.price_amount),
        "accepted_currency": offer_msg.price_currency,
    }

    accept_msg = ServiceChatMessage(
        room=room,
        sender=client_user,
        message_type=ServiceChatMessage.MessageType.PRICE_ACCEPTED,
        body=f"Accepted price offer: {offer_msg.price_amount} {offer_msg.price_currency}",
        price_amount=offer_msg.price_amount,
        price_currency=offer_msg.price_currency,
        metadata=metadata,
    )

    with transaction.atomic():
        accept_msg.save()
        room.last_message_at = timezone.now()
        room.save(update_fields=["last_message_at", "updated_at"])
        _update_unread_counts(room, client_user)

        transaction.on_commit(lambda: _notify_message_created(accept_msg))
        transaction.on_commit(lambda: _realtime_price_accepted(accept_msg))

    return offer_msg, accept_msg


def _realtime_price_accepted(message):
    """Broadcast price accepted via Channels."""
    try:
        from .realtime import send_price_accepted
        send_price_accepted(message)
    except Exception as exc:
        logger.debug("Realtime price accepted broadcast skipped: %s", exc)


# ---------------------------------------------------------------------------
# Contract linking
# ---------------------------------------------------------------------------

def link_contract_to_room(room, contract, actor):
    """
    Link an existing contract to a chat room.

    Validates that the contract participants match the room participants.
    Sets room status to CONTRACT_LINKED.
    """
    if contract.client != room.client:
        raise ValueError("Contract client does not match room client.")

    if contract.technician != room.technician:
        raise ValueError("Contract technician does not match room technician.")

    metadata = {
        "contract_id": str(contract.id),
        "contract_reference": contract.contract_reference,
    }

    system_msg = ServiceChatMessage(
        room=room,
        sender=actor,
        message_type=ServiceChatMessage.MessageType.CONTRACT_LINKED,
        body=f"Contract {contract.contract_reference} linked to this conversation.",
        metadata=metadata,
    )

    with transaction.atomic():
        room.mark_contract_linked(contract)
        system_msg.save()
        room.last_message_at = timezone.now()
        room.save(update_fields=["last_message_at", "updated_at"])

        transaction.on_commit(lambda: _notify_contract_linked(room, contract, actor))
        transaction.on_commit(lambda: _realtime_contract_linked(room, contract))

    return system_msg, True


def _notify_contract_linked(room, contract, actor):
    """Notify both participants that contract was linked."""
    for user in [room.client.user, room.technician.user]:
        try:
            create_notification(
                recipient=user,
                notification_type=Notification.Type.CONTRACT_CREATED,
                title="Contract linked to conversation",
                message=f"Contract {contract.contract_reference} has been linked.",
                actor=actor,
                target_type="contract",
                target_id=contract.id,
                target_url=f"/contracts/{contract.id}",
                metadata={"room_id": str(room.id), "contract_id": str(contract.id)},
            )
        except Exception as exc:
            logger.warning("Failed to notify contract link: %s", exc)


def _realtime_contract_linked(room, contract):
    """Broadcast contract linked via Channels."""
    try:
        from .realtime import send_contract_linked
        send_contract_linked(room, contract)
    except Exception as exc:
        logger.debug("Realtime contract linked broadcast skipped: %s", exc)


# ---------------------------------------------------------------------------
# Room management actions
# ---------------------------------------------------------------------------

def mark_room_read(room, user):
    """
    Mark all messages in a room as read for a user.
    Returns the updated read state.
    """
    if not room.can_participate(user):
        raise PermissionError("User is not a participant in this room.")

    read_state, created = ServiceChatReadState.objects.get_or_create(
        room=room,
        user=user,
        defaults={"unread_count": 0},
    )

    # Find the latest message
    latest_message = ServiceChatMessage.objects.filter(
        room=room,
        is_deleted=False,
    ).order_by("-created_at").first()

    read_state.last_read_message = latest_message
    read_state.last_read_at = timezone.now()
    read_state.unread_count = 0
    read_state.save(update_fields=["last_read_message", "last_read_at", "unread_count", "updated_at"])

    if latest_message:
        transaction.on_commit(
            lambda: _realtime_read_receipt(room, user, str(latest_message.id))
        )

    return read_state


def _realtime_read_receipt(room, user, message_id):
    """Broadcast read receipt via Channels."""
    try:
        from .realtime import send_chat_read
        send_chat_read(room.id, user, message_id)
    except Exception as exc:
        logger.debug("Realtime read receipt broadcast skipped: %s", exc)


def close_room(room, user, reason=""):
    """
    Close a room. Participants can close if no active contract.
    Staff/admin can always close/block.
    """
    if not room.can_participate(user) and not user.is_staff:
        raise PermissionError("User cannot close this room.")

    if room.linked_contract and room.linked_contract.status in (
        "in_progress", "pending_acceptance",
    ):
        raise ValueError("Cannot close room with an active contract.")

    metadata = {"reason": reason} if reason else {}

    system_msg = ServiceChatMessage(
        room=room,
        sender=user,
        message_type=ServiceChatMessage.MessageType.SYSTEM,
        body=f"Room closed by {user.username}.{' Reason: ' + reason if reason else ''}",
        metadata=metadata,
    )

    with transaction.atomic():
        room.status = ServiceChatRoom.Status.CLOSED
        room.closed_at = timezone.now()
        room.closed_by = user
        room.last_message_at = timezone.now()
        room.save(update_fields=["status", "closed_at", "closed_by", "last_message_at", "updated_at"])
        system_msg.save()

        transaction.on_commit(lambda: _realtime_room_closed(room))

    return room


def _realtime_room_closed(room):
    """Broadcast room closed via Channels."""
    try:
        from .realtime import send_room_closed
        send_room_closed(room)
    except Exception as exc:
        logger.debug("Realtime room closed broadcast skipped: %s", exc)


# ---------------------------------------------------------------------------
# Unread summary
# ---------------------------------------------------------------------------

def get_unread_summary(user):
    """Get total unread count and per-room breakdown."""
    if not user or not user.is_authenticated:
        return {"total_unread": 0, "rooms": []}

    read_states = ServiceChatReadState.objects.filter(
        user=user,
        unread_count__gt=0,
    ).select_related("room")

    total = 0
    rooms_data = []
    for rs in read_states:
        total += rs.unread_count
        rooms_data.append({
            "room_id": str(rs.room_id),
            "unread_count": rs.unread_count,
            "last_message_at": rs.room.last_message_at.isoformat() if rs.room.last_message_at else None,
        })

    return {"total_unread": total, "rooms": rooms_data}
