from rest_framework.permissions import BasePermission, IsAuthenticated


class IsContractParticipantOrAdmin(BasePermission):
    """Object-level: user is client, technician, or admin for this contract."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        if hasattr(user, "client_profile") and obj.client.user == user:
            return True
        if hasattr(user, "technician_profile") and obj.technician.user == user:
            return True
        return False


class IsContractClient(BasePermission):
    """Object-level: user is the contract client."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            hasattr(user, "client_profile") and obj.client.user == user
        )


class IsContractTechnician(BasePermission):
    """Object-level: user is the contract technician."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            hasattr(user, "technician_profile") and obj.technician.user == user
        )


class IsAdminUser(IsAuthenticated):
    """Only admin/staff users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_staff
