"""Serializers for the Offer model."""

from decimal import Decimal

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .offer_models import Offer


class TechnicianSummarySerializer(serializers.Serializer):
    """Safe technician summary — no private fields."""
    user_id = serializers.CharField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    job_title = serializers.CharField(read_only=True)
    governorate = serializers.CharField(read_only=True)
    profile_image = serializers.ImageField(read_only=True)


class ClientSummarySerializer(serializers.Serializer):
    """Safe client summary — no private fields."""
    user_id = serializers.CharField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    governorate = serializers.CharField(read_only=True)
    profile_image = serializers.ImageField(read_only=True)


class ServiceRequestSummarySerializer(serializers.Serializer):
    """Lightweight service request summary for offer context."""
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class OfferListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for offer list views."""
    technician = TechnicianSummarySerializer(source="service_request.technician", read_only=True)
    client = ClientSummarySerializer(source="service_request.client", read_only=True)
    request_title = serializers.CharField(source="service_request.title", read_only=True)
    request_status = serializers.CharField(source="service_request.status", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "service_request",
            "request_title",
            "request_status",
            "technician",
            "client",
            "amount",
            "currency",
            "description",
            "duration_days",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "service_request", "technician", "client",
            "currency", "status", "created_at", "updated_at",
        ]


class OfferDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for offer."""
    technician = TechnicianSummarySerializer(source="service_request.technician", read_only=True)
    client = ClientSummarySerializer(source="service_request.client", read_only=True)
    request = ServiceRequestSummarySerializer(source="service_request", read_only=True)
    can_edit = serializers.BooleanField(read_only=True)
    can_withdraw = serializers.BooleanField(read_only=True)
    is_terminal = serializers.BooleanField(read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "service_request",
            "request",
            "technician",
            "client",
            "amount",
            "currency",
            "description",
            "duration_days",
            "status",
            "can_edit",
            "can_withdraw",
            "is_terminal",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "service_request", "request", "technician", "client",
            "currency", "status", "can_edit", "can_withdraw", "is_terminal",
            "created_at", "updated_at",
        ]


class OfferCreateSerializer(serializers.Serializer):
    """Serializer for creating a new draft offer."""
    service_request_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=5000)
    duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("Amount must be greater than zero."))
        return value


class OfferUpdateSerializer(serializers.Serializer):
    """Serializer for updating a draft offer."""
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=Decimal("0.01"), required=False,
    )
    description = serializers.CharField(max_length=5000, required=False)
    duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class OfferActionSerializer(serializers.Serializer):
    """Empty serializer for action endpoints (submit, withdraw, accept, reject)."""
    pass
