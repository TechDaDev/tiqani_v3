"""
Chat models — ServiceChatRoom, ServiceChatMessage, ServiceChatReadState.

Designed for pre-contract negotiation between clients and technicians.
Chat comes before contract; linked_contract is nullable until agreement.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from tiqani_v3.file_validators import validate_document_file


# Forward reference for service_request
SERVICE_REQUEST_MODEL = "servicerequest.ServiceRequest"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chat_attachment_path(instance, filename):
    """Generate unique file path for chat attachments."""
    ext = filename.split(".")[-1].lower()
    folder = "chat/attachments"
    uid_part = str(instance.id).split("-")[-1] if instance.id else uuid.uuid4().hex[:8]
    return f"{folder}/{uid_part}.{ext}"


# ---------------------------------------------------------------------------
# ServiceChatRoom
# ---------------------------------------------------------------------------

class ServiceChatRoom(models.Model):
    """
    A chat room for pre-contract negotiation between a client and a technician.

    Rules:
        - Only a client can initiate a room with a technician.
        - One active room per client+technician pair unless previous is closed.
        - Room can be linked to a contract after agreement.
        - When linked_contract is set, status becomes CONTRACT_LINKED.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", _("Open")
        PROPOSAL_CREATED = "PROPOSAL_CREATED", _("Proposal Created")
        CONTRACT_LINKED = "CONTRACT_LINKED", _("Contract Linked")
        CLOSED = "CLOSED", _("Closed")
        BLOCKED = "BLOCKED", _("Blocked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        "accounts.ClientProfile",
        on_delete=models.CASCADE,
        related_name="chat_rooms_as_client",
        verbose_name=_("Client"),
    )
    technician = models.ForeignKey(
        "accounts.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="chat_rooms_as_technician",
        verbose_name=_("Technician"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_rooms_created",
        verbose_name=_("Created By"),
    )
    linked_contract = models.ForeignKey(
        "contract.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_rooms",
        verbose_name=_("Linked Contract"),
    )
    service_request = models.ForeignKey(
        SERVICE_REQUEST_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_rooms",
        verbose_name=_("Service Request"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
        verbose_name=_("Status"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    last_message_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Last Message At"),
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed At"))
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_rooms_closed",
        verbose_name=_("Closed By"),
    )

    class Meta:
        verbose_name = _("Service Chat Room")
        verbose_name_plural = _("Service Chat Rooms")
        constraints = [
            models.UniqueConstraint(
                fields=["service_request"],
                name="uq_room_service_request",
                condition=models.Q(service_request__isnull=False),
            ),
        ]
        indexes=[
            models.Index(fields=["client", "technician", "status"], name="idx_room_client_tech_status"),
            models.Index(fields=["technician", "status", "updated_at"], name="idx_room_tech_status_time"),
            models.Index(fields=["client", "status", "updated_at"], name="idx_room_client_status_time"),
            models.Index(fields=["linked_contract"], name="idx_room_linked_contract"),
            models.Index(fields=["service_request"], name="idx_room_service_request"),
            models.Index(fields=["last_message_at"], name="idx_room_last_message"),
        ]

    def __str__(self):
        return f"Room({self.client_id} <-> {self.technician_id}) [{self.status}]"

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------

    def can_participate(self, user):
        """Check if user is the client or technician in this room."""
        if not user or not user.is_authenticated:
            return False
        return (
            (hasattr(user, "client_profile") and user.client_profile == self.client)
            or (hasattr(user, "technician_profile") and user.technician_profile == self.technician)
            or user.is_staff
        )

    def other_participant(self, user):
        """Return the other participant's user object."""
        if not user or not user.is_authenticated:
            return None
        if hasattr(user, "client_profile") and user.client_profile == self.client:
            return self.technician.user
        if hasattr(user, "technician_profile") and user.technician_profile == self.technician:
            return self.client.user
        return None

    def can_send(self, user):
        """Check if user can send a message in this room."""
        if not self.can_participate(user):
            return False
        return self.status in (
            self.Status.OPEN,
            self.Status.PROPOSAL_CREATED,
            self.Status.CONTRACT_LINKED,
        )

    def can_link_contract(self, user):
        """Check if user can link a contract to this room."""
        return self.can_participate(user) and self.status not in (
            self.Status.CLOSED,
            self.Status.BLOCKED,
        )

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def mark_contract_linked(self, contract):
        """Set linked_contract and update status."""
        self.linked_contract = contract
        if self.status != self.Status.BLOCKED:
            self.status = self.Status.CONTRACT_LINKED
        self.save(update_fields=["linked_contract", "status", "updated_at"])

    def clean(self):
        """Validate that client and technician are different users."""
        if self.client_id and self.technician_id:
            if self.client.user_id == self.technician.user_id:
                raise ValidationError("Client and technician cannot be the same user.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ServiceChatMessage
# ---------------------------------------------------------------------------

class ServiceChatMessage(models.Model):
    """
    A message within a ServiceChatRoom.

    Rules:
        - TEXT requires non-empty body.
        - FILE requires attachment.
        - PRICE_OFFER requires price_amount.
        - SYSTEM messages created only by service layer.
        - sender must be room participant unless SYSTEM.
    """

    class MessageType(models.TextChoices):
        TEXT = "TEXT", _("Text")
        FILE = "FILE", _("File")
        SYSTEM = "SYSTEM", _("System")
        PRICE_OFFER = "PRICE_OFFER", _("Price Offer")
        PRICE_ACCEPTED = "PRICE_ACCEPTED", _("Price Accepted")
        CONTRACT_LINKED = "CONTRACT_LINKED", _("Contract Linked")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ServiceChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Room"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages_sent",
        verbose_name=_("Sender"),
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        db_index=True,
        verbose_name=_("Message Type"),
    )
    body = models.TextField(
        blank=True,
        default="",
        max_length=2000,
        verbose_name=_("Message Body"),
    )
    attachment = models.FileField(
        upload_to=chat_attachment_path,
        null=True,
        blank=True,
        validators=[validate_document_file],
        verbose_name=_("Attachment"),
    )
    attachment_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Attachment Name"),
    )
    attachment_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Attachment Size (bytes)"),
    )
    attachment_content_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Attachment Content Type"),
    )
    price_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Price Amount"),
    )
    price_currency = models.CharField(
        max_length=3,
        default="IQD",
        verbose_name=_("Price Currency"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    is_deleted = models.BooleanField(default=False, verbose_name=_("Is Deleted"))
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Edited At"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service Chat Message")
        verbose_name_plural = _("Service Chat Messages")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"], name="idx_msg_room_created"),
            models.Index(fields=["sender", "created_at"], name="idx_msg_sender_created"),
            models.Index(fields=["room", "message_type", "created_at"], name="idx_msg_room_type_created"),
            models.Index(fields=["room", "is_deleted", "created_at"], name="idx_msg_room_deleted_created"),
        ]

    def __str__(self):
        return f"Msg({self.message_type}) in Room({self.room_id})"

    # ------------------------------------------------------------------
    # Permission helpers
    # ------------------------------------------------------------------

    def can_edit(self, user):
        """Sender can edit text messages within 1 hour."""
        if not user or not user.is_authenticated:
            return False
        if self.sender != user:
            return False
        if self.is_deleted:
            return False
        if self.message_type != ServiceChatMessage.MessageType.TEXT:
            return False
        from django.utils import timezone
        age = (timezone.now() - self.created_at).total_seconds()
        return age < 3600  # 1 hour

    def can_delete(self, user):
        """Sender or admin can soft-delete."""
        if not user or not user.is_authenticated:
            return False
        return self.sender == user or user.is_staff

    def safe_preview(self):
        """Return a safe text preview of the message."""
        if self.is_deleted:
            return "[deleted]"
        if self.message_type == self.MessageType.FILE:
            return f"[File: {self.attachment_name or 'attachment'}]"
        if self.message_type == self.MessageType.PRICE_OFFER:
            return f"[Price Offer: {self.price_amount} {self.price_currency}]"
        if self.message_type == self.MessageType.PRICE_ACCEPTED:
            return "[Price Accepted]"
        if self.message_type == self.MessageType.CONTRACT_LINKED:
            return "[Contract Linked]"
        return self.body or ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        errors = {}
        if self.message_type == self.MessageType.TEXT and not self.body:
            errors["body"] = "Text messages require a non-empty body."
        if self.message_type == self.MessageType.FILE and not self.attachment:
            errors["attachment"] = "File messages require an attachment."
        if self.message_type == self.MessageType.PRICE_OFFER and self.price_amount is None:
            errors["price_amount"] = "Price offers require an amount."
        if self.message_type == self.MessageType.SYSTEM and self.body:
            if len(self.body) > 500:
                errors["body"] = "System message body too long."
        # Enforce max_length on body field
        if self.body and len(self.body) > 2000:
            errors["body"] = "Message body exceeds 2000 characters."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.attachment_name and self.attachment:
            self.attachment_name = self.attachment.name.split("/")[-1]
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ServiceChatReadState
# ---------------------------------------------------------------------------

class ServiceChatReadState(models.Model):
    """
    Tracks per-user read state within a chat room.

    Unique constraint on (room, user) ensures one read state per participant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ServiceChatRoom,
        on_delete=models.CASCADE,
        related_name="read_states",
        verbose_name=_("Room"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_read_states",
        verbose_name=_("User"),
    )
    last_read_message = models.ForeignKey(
        ServiceChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Last Read Message"),
    )
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Read At"),
    )
    unread_count = models.PositiveIntegerField(default=0, verbose_name=_("Unread Count"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service Chat Read State")
        verbose_name_plural = _("Service Chat Read States")
        unique_together = ["room", "user"]
        indexes = [
            models.Index(fields=["user", "updated_at"], name="idx_read_user_updated"),
            models.Index(fields=["room", "last_read_at"], name="idx_read_room_last_read"),
        ]

    def __str__(self):
        return f"ReadState(Room {self.room_id}, User {self.user_id})"
