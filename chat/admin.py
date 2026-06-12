"""
Chat admin configuration.

Provides read-only access for moderation and debugging.
"""

from django.contrib import admin

from .models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState


@admin.register(ServiceChatRoom)
class ServiceChatRoomAdmin(admin.ModelAdmin):
    """Admin for chat rooms."""

    list_display = (
        "id_short", "client_name", "technician_name", "status",
        "linked_contract_id", "last_message_at", "created_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = (
        "client__user__username", "client__user__email",
        "technician__user__username", "technician__user__email",
    )
    readonly_fields = (
        "id", "client", "technician", "created_by", "linked_contract",
        "status", "metadata", "last_message_at", "created_at",
        "updated_at", "closed_at", "closed_by",
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"

    def client_name(self, obj):
        return obj.client.user.username
    client_name.short_description = "Client"

    def technician_name(self, obj):
        return obj.technician.user.username
    technician_name.short_description = "Technician"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ServiceChatMessage)
class ServiceChatMessageAdmin(admin.ModelAdmin):
    """Admin for chat messages."""

    list_display = (
        "id_short", "room_short", "sender_name", "message_type",
        "preview", "is_deleted", "created_at",
    )
    list_filter = ("message_type", "is_deleted", "created_at")
    search_fields = ("body", "sender__username", "sender__email")
    readonly_fields = (
        "id", "room", "sender", "message_type", "body", "attachment",
        "attachment_name", "attachment_size", "attachment_content_type",
        "price_amount", "price_currency", "metadata", "is_deleted",
        "edited_at", "created_at", "updated_at",
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"

    def room_short(self, obj):
        return str(obj.room_id)[:8] + "..."
    room_short.short_description = "Room"

    def sender_name(self, obj):
        return obj.sender.username
    sender_name.short_description = "Sender"

    def preview(self, obj):
        return obj.safe_preview()[:60]
    preview.short_description = "Preview"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ServiceChatReadState)
class ServiceChatReadStateAdmin(admin.ModelAdmin):
    """Admin for chat read states."""

    list_display = ("id_short", "room_short", "user_name", "unread_count", "last_read_at")
    list_filter = ("updated_at",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "room", "user", "last_read_message", "last_read_at", "unread_count", "updated_at")

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"

    def room_short(self, obj):
        return str(obj.room_id)[:8] + "..."
    room_short.short_description = "Room"

    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = "User"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
