"""
Serializers for ServiceRequest — create, list, detail, and status actions.
"""

from rest_framework import serializers
from .models import ServiceRequest


class TechnicianBasicSerializer(serializers.Serializer):
    """Public-safe technician summary for request context."""
    user_id = serializers.CharField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    job_title = serializers.CharField(read_only=True)
    governorate = serializers.CharField(read_only=True)
    profile_image = serializers.ImageField(read_only=True)


class ClientBasicSerializer(serializers.Serializer):
    """Public-safe client summary for request context."""
    user_id = serializers.CharField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    governorate = serializers.CharField(read_only=True)
    profile_image = serializers.ImageField(read_only=True)


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    client = ClientBasicSerializer(read_only=True)
    technician = TechnicianBasicSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    skill_name = serializers.CharField(source="skill.name", read_only=True, default=None)

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "client",
            "technician",
            "category",
            "category_name",
            "skill",
            "skill_name",
            "title",
            "description",
            "governorate",
            "status",
            "is_urgent",
            "preferred_date",
            "preferred_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "client", "status", "created_at", "updated_at"]


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer including all safe fields."""
    client = ClientBasicSerializer(read_only=True)
    technician = TechnicianBasicSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    skill_name = serializers.CharField(source="skill.name", read_only=True, default=None)

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "client",
            "technician",
            "category",
            "category_name",
            "skill",
            "skill_name",
            "title",
            "description",
            "governorate",
            "service_address",
            "preferred_date",
            "preferred_time",
            "is_urgent",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "client", "status", "created_at", "updated_at"]


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new service request (client only)."""
    technician = serializers.UUIDField()  # Accepts user UUID from public profile

    class Meta:
        model = ServiceRequest
        fields = [
            "technician",
            "category",
            "skill",
            "title",
            "description",
            "governorate",
            "service_address",
            "preferred_date",
            "preferred_time",
            "is_urgent",
        ]

    def validate_technician(self, value):
        """Look up TechnicianProfile by user UUID; ensure approved and available."""
        from accounts.models import TechnicianProfile, CustomUser
        try:
            user = CustomUser.objects.get(id=value)
            try:
                profile = TechnicianProfile.objects.get(user=user)
            except TechnicianProfile.DoesNotExist:
                raise serializers.ValidationError("No technician profile found for this user.")
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Technician not found.")
        if not profile.approved:
            raise serializers.ValidationError("This technician is not yet approved.")
        if not profile.is_available:
            raise serializers.ValidationError("This technician is currently unavailable.")
        return profile


class ServiceRequestActionSerializer(serializers.Serializer):
    """Serializer for status action endpoints (accept, decline, cancel, withdraw)."""
    pass
