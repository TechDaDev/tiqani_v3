from rest_framework.permissions import BasePermission, IsAuthenticated


class IsClient(IsAuthenticated):
    """Allow access only to users with client role."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "client"


class IsTechnician(IsAuthenticated):
    """Allow access only to users with technician role."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "technician"


class IsOwnerOrAdmin(BasePermission):
    """
    Allow access if the requesting user is the object owner or a staff/admin user.
    Expects the view to define a `get_object_user(obj)` method or the object
    to have a `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        user = getattr(obj, "user", None)
        if user is None and hasattr(view, "get_object_user"):
            user = view.get_object_user(obj)
        return bool(
            request.user
            and (request.user.is_staff or (user and request.user == user))
        )
