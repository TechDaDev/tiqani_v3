"""Permissions for review operations."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsReviewOwner(BasePermission):
    """Only the review's reviewer (author) can edit."""

    def has_object_permission(self, request, view, obj):
        return obj.reviewer == request.user


class IsReviewedTechnician(BasePermission):
    """Only the technician being reviewed can respond."""

    def has_object_permission(self, request, view, obj):
        return (
            hasattr(request.user, 'technician_profile')
            and obj.technician == request.user.technician_profile
        )


class IsPlatformAdminOrStaff(BasePermission):
    """Only admin/staff can moderate."""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsAuthenticatedOrStaffForPost(BasePermission):
    """
    - Read: anyone
    - Write: authenticated users only (or staff)
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
