"""
Dealership permission helpers.

Reuses dashboard/accounts role_helpers for admin checks.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from accounts.role_helpers import (
    is_system_admin,
    is_finance_admin,
    is_account_manager,
    is_content_moderator,
)


class IsDealership(IsAuthenticated):
    """Allow access only to dealership users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'dealership'


class IsClientUser(IsAuthenticated):
    """Allow access only to client users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'client'


class IsDealershipOrAdmin(IsAuthenticated):
    """Allow dealership users or any admin/staff."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.role == 'dealership':
            return True
        return bool(request.user.is_staff or request.user.is_superuser)


class IsSystemAdminOrFinance(BasePermission):
    """System admin or finance admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_system_admin(request.user) or is_finance_admin(request.user)


class IsAccountManagerOrFinance(BasePermission):
    """Account manager, finance admin, or system admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            is_system_admin(request.user)
            or is_finance_admin(request.user)
            or is_account_manager(request.user)
        )


class IsContentModeratorDenied(BasePermission):
    """Deny content moderators from accessing dealership endpoints.
    Does NOT deny system_admin or superuser access.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # System admins and superusers always pass
        if is_system_admin(request.user):
            return True
        # Only content moderators (not higher roles) are denied
        if is_content_moderator(request.user):
            return False
        return True
