"""
Chat serializers — rooms, messages, read states, price offers.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState


# ---------------------------------------------------------------------------
# Profile mini-serializers (lightweight, no sensitive fields)
# ---------------------------------------------------------------------------

class ChatUserSerializer(serializers.Serializer):
    """Lightweight user representation for chat context."""
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)

    def get_full_name(self, obj):
        name = obj.get_full_name()
        return name or obj.username

    def get_profile_image(self, obj):
        if obj.profile_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


# ---------------------------------------------------------------------------
# ServiceChatMessage serializers
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    """Full message serializer for read operations."""

    sender_info = ChatUserSerializer(source="sender", read_only=True)
    safe_body = serializers.SerializerMethodField()

    class Meta:
        model = ServiceChatMessage
        fields = (
            "id",
            "room_id",
            "sender",
            "sender_info",
            "message_type",
            "body",
            "safe_body",
            "attachment",
            "attachment_name",
            "attachment_size",
            "attachment_content_type",
            "price_amount",
            "price_currency",
            "metadata",
            "is_deleted",
            "edited_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "room_id",
            "sender",
            "sender_info",
            "safe_body",
            "is_deleted",
            "edited_at",
            "created_at",
            "updated_at",
        )

    def get_safe_body(self, obj):
        return obj.safe_preview()


class MessageCreateSerializer(serializers.Serializer):
    """Create a text message in a room."""
    body = serializers.CharField(
        max_length=2000,
        required=True,
        allow_blank=False,
    )


class AttachmentUploadSerializer(serializers.Serializer):
    """Upload a file attachment message."""
    file = serializers.FileField(required=True)
    body = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        default="",
    )


# ---------------------------------------------------------------------------
# Price offer serializers
# ---------------------------------------------------------------------------

class PriceOfferSerializer(serializers.Serializer):
    """Technician sends a price offer."""
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=True,
        min_value=0.01,
    )
    currency = serializers.CharField(
        max_length=3,
        default="IQD",
        required=False,
    )
    description = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        default="",
    )


class AcceptPriceSerializer(serializers.Serializer):
    """Accept a price offer (no extra body needed)."""
    pass


# ---------------------------------------------------------------------------
# Room-level serializers
# ---------------------------------------------------------------------------

class RoomCreateSerializer(serializers.Serializer):
    """Client initiates contact with a technician."""
    technician_id = serializers.UUIDField(required=True)
    initial_message = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        default="",
    )


class RoomCloseSerializer(serializers.Serializer):
    """Close a room with an optional reason."""
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )


class LinkContractSerializer(serializers.Serializer):
    """Link an existing contract to the room."""
    contract_id = serializers.UUIDField(required=True)


# ---------------------------------------------------------------------------
# Read state
# ---------------------------------------------------------------------------

class ReadStateSerializer(serializers.ModelSerializer):
    """Read state for a user in a room."""

    class Meta:
        model = ServiceChatReadState
        fields = (
            "id",
            "room_id",
            "user_id",
            "last_read_message_id",
            "last_read_at",
            "unread_count",
            "updated_at",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Room detail serializer
# ---------------------------------------------------------------------------

class RoomSerializer(serializers.ModelSerializer):
    """Room serialization with participant info and last message."""

    client_user = serializers.SerializerMethodField()
    technician_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    linked_contract_status = serializers.SerializerMethodField()
    service_request_title = serializers.SerializerMethodField()
    service_request_status = serializers.SerializerMethodField()

    class Meta:
        model = ServiceChatRoom
        fields = (
            "id",
            "client_id",
            "technician_id",
            "client_user",
            "technician_user",
            "created_by_id",
            "linked_contract_id",
            "linked_contract_status",
            "service_request_id",
            "service_request_title",
            "service_request_status",
            "status",
            "metadata",
            "last_message",
            "unread_count",
            "last_message_at",
            "created_at",
            "updated_at",
            "closed_at",
            "closed_by_id",
        )
        read_only_fields = fields

    def get_service_request_title(self, obj):
        if obj.service_request:
            return obj.service_request.title
        return None

    def get_service_request_status(self, obj):
        if obj.service_request:
            return obj.service_request.status
        return None

    def get_client_user(self, obj):
        request = self.context.get("request")
        return ChatUserSerializer(obj.client.user, context={"request": request}).data

    def get_technician_user(self, obj):
        request = self.context.get("request")
        return ChatUserSerializer(obj.technician.user, context={"request": request}).data

    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).order_by("-created_at").first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        try:
            read_state = obj.read_states.get(user=request.user)
            return read_state.unread_count
        except ServiceChatReadState.DoesNotExist:
            return 0

    def get_linked_contract_status(self, obj):
        if obj.linked_contract:
            return obj.linked_contract.status
        return None


class RoomListSerializer(serializers.ModelSerializer):
    """Lighter room serialization for list views."""

    client_user = serializers.SerializerMethodField()
    technician_user = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    service_request_title = serializers.SerializerMethodField()
    service_request_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ServiceChatRoom
        fields = (
            "id",
            "status",
            "client_user",
            "technician_user",
            "linked_contract_id",
            "service_request_id",
            "service_request_title",
            "last_message_preview",
            "unread_count",
            "last_message_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_client_user(self, obj):
        request = self.context.get("request")
        return ChatUserSerializer(obj.client.user, context={"request": request}).data

    def get_technician_user(self, obj):
        request = self.context.get("request")
        return ChatUserSerializer(obj.technician.user, context={"request": request}).data

    def get_service_request_title(self, obj):
        if obj.service_request:
            return obj.service_request.title
        return None

    def get_last_message_preview(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).order_by("-created_at").first()
        if last_msg:
            return {
                "id": str(last_msg.id),
                "message_type": last_msg.message_type,
                "preview": last_msg.safe_preview(),
                "sender_id": str(last_msg.sender_id),
                "created_at": last_msg.created_at.isoformat(),
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        try:
            read_state = obj.read_states.get(user=request.user)
            return read_state.unread_count
        except ServiceChatReadState.DoesNotExist:
            return 0


# ---------------------------------------------------------------------------
# Unread summary
# ---------------------------------------------------------------------------

class UnreadSummarySerializer(serializers.Serializer):
    total_unread = serializers.IntegerField()
    rooms = serializers.ListField(child=serializers.DictField())


class RequestRoomCreateSerializer(serializers.Serializer):
    """Create or get a conversation for a service request."""
    request_id = serializers.UUIDField(required=True)
