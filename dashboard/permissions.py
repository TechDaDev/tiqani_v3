"""Admin dashboard permission helpers.

Now delegates to accounts.role_helpers for consistent checks.
"""

from rest_framework.permissions import BasePermission

from accounts.role_helpers import (
    is_platform_admin,
    is_system_admin,
    is_finance_admin,
    is_account_manager,
    is_content_moderator,
    is_admin_or_staff as _helpers_admin_or_staff,
)


class IsPlatformAdmin(BasePermission):
    """Any staff/superuser/admin user."""

    def has_permission(self, request, view):
        return is_platform_admin(request.user)


class IsSystemAdmin(BasePermission):
    """Superuser or system_admin role."""

    def has_permission(self, request, view):
        return is_system_admin(request.user)


class IsFinanceAdmin(BasePermission):
    """Superuser, system_admin, or finance_admin."""

    def has_permission(self, request, view):
        return is_finance_admin(request.user)


class IsAccountManager(BasePermission):
    """Superuser, system_admin, or account_manager."""

    def has_permission(self, request, view):
        return is_account_manager(request.user)


class IsContentModerator(BasePermission):
    """Superuser, system_admin, or content_moderator."""

    def has_permission(self, request, view):
        return is_content_moderator(request.user)


class IsAdminOrStaff(BasePermission):
    """Broad admin access — any staff or admin user."""

    def has_permission(self, request, view):
        return _helpers_admin_or_staff(request.user)
