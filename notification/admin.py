from django.contrib import admin
from .models import Notification, ActivityLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'recipient__email', 'actor__username', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'verb', 'audience', 'target_type', 'created_at')
    list_filter = ('audience', 'verb', 'created_at')
    search_fields = ('actor__username', 'actor__email', 'verb', 'target_type')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
