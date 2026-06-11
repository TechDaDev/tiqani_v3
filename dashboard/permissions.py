"""Admin dashboard permission helpers."""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.models import AdminProfile


def _get_admin_role(user):
    """Return the admin_role string for a user, or None."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'superuser'
    if hasattr(user, 'admin_profile') and user.admin_profile:
        return user.admin_profile.role
    return None


class IsPlatformAdmin(BasePermission):
    """Any staff/superuser/admin user."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        if request.user.role == 'admin':
            return True
        return False


class IsSystemAdmin(BasePermission):
    """Superuser or system_admin role."""

    def has_permission(self, request, view):
        role = _get_admin_role(request.user)
        return role in ('superuser', 'system_admin')


class IsFinanceAdmin(BasePermission):
    """Superuser, system_admin, or finance_admin."""

    def has_permission(self, request, view):
        role = _get_admin_role(request.user)
        return role in ('superuser', 'system_admin', 'finance_admin')


class IsAccountManager(BasePermission):
    """Superuser, system_admin, or account_manager (if exists)."""
    # The existing AdminProfile doesn't have account_manager, but we support it
    def has_permission(self, request, view):
        role = _get_admin_role(request.user)
        return role in ('superuser', 'system_admin', 'account_manager')


class IsContentModerator(BasePermission):
    """Superuser, system_admin, or content_moderator."""

    def has_permission(self, request, view):
        role = _get_admin_role(request.user)
        return role in ('superuser', 'system_admin', 'content_moderator')


class IsAdminOrStaff(BasePermission):
    """Broad admin access — any staff or admin user."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return bool(request.user.is_staff or request.user.is_superuser)
