"""
Centralised role-helper functions for admin/staff permission checks.

Every helper returns a bool and is safe to call on unauthenticated users.
"""

from django.contrib.auth import get_user_model


def _get_admin_role(user):
    """Return the admin_role string for a user, or None."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'superuser'
    if hasattr(user, 'admin_profile') and user.admin_profile:
        return user.admin_profile.role
    return None


def get_admin_role(user):
    """Public alias."""
    return _get_admin_role(user)


def is_platform_admin(user):
    """Any staff / superuser / admin-role user."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if user.role == 'admin':
        return True
    return False


def is_system_admin(user):
    """Superuser or system_admin role."""
    role = _get_admin_role(user)
    return role in ('superuser', 'system_admin')


def is_finance_admin(user):
    """Superuser, system_admin, or finance_admin."""
    role = _get_admin_role(user)
    return role in ('superuser', 'system_admin', 'finance_admin')


def is_account_manager(user):
    """Superuser, system_admin, or account_manager."""
    role = _get_admin_role(user)
    return role in ('superuser', 'system_admin', 'account_manager')


def is_content_moderator(user):
    """Superuser, system_admin, or content_moderator."""
    role = _get_admin_role(user)
    return role in ('superuser', 'system_admin', 'content_moderator')


def is_admin_or_staff(user):
    """Broad admin access — any staff or superuser."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser)
