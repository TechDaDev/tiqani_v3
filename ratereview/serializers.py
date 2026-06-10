from rest_framework import serializers
from .models import Review


class ReviewPublicSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "technician",
            "reviewer",
            "reviewer_name",
            "technician_name",
            "rating",
            "comment",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return obj.reviewer.get_full_name() or obj.reviewer.username
        return None

    def get_technician_name(self, obj):
        if obj.technician and obj.technician.user:
            return obj.technician.user.get_full_name() or obj.technician.user.username
        return None
