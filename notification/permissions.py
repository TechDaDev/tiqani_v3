"""Permissions for notification endpoints."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsNotificationOwner(BasePermission):
    """User can only access their own notifications."""

    def has_object_permission(self, request, view, obj):
        return obj.recipient == request.user


class IsAdminOrStaffForActivity(BasePermission):
    """Only admin/staff can access the activity feed."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
