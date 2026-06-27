"""Serializers for notification and activity feed."""

from rest_framework import serializers
from .models import Notification, ActivityLog, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Detail/list serializer for user notifications."""

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'actor', 'actor_name',
            'target_type', 'target_id', 'target_url',
            'title_key', 'body_key', 'metadata', 'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None


class NotificationMarkReadSerializer(serializers.Serializer):
    """No required body for mark-read/mark-unread."""
    pass


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for admin activity feed."""

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'actor', 'actor_name', 'verb',
            'target_type', 'target_id', 'target_repr',
            'audience', 'metadata', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """In-app notification preference serializer."""

    class Meta:
        model = NotificationPreference
        fields = [
            'offers', 'contracts', 'payments', 'execution', 'messages',
            'disputes', 'refunds', 'reviews', 'security', 'system',
            'email_enabled', 'push_enabled', 'created_at', 'updated_at',
        ]
        read_only_fields = ['email_enabled', 'push_enabled', 'created_at', 'updated_at']
