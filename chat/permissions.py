"""
Chat permission rules.

Governs who can create rooms, send messages, make price offers,
link contracts, and manage messages.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from accounts.role_helpers import is_admin_or_staff


class IsClientUser(IsAuthenticated):
    """Allow access only to client-role users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "client"


class IsTechnicianUser(IsAuthenticated):
    """Allow access only to technician-role users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == "technician"


class CanCreateRoom(IsAuthenticated):
    """
    Only authenticated clients can create a chat room.
    Technician cannot initiate first contact.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role == "client"


class IsRoomParticipant(BasePermission):
    """
    Allow access if user is a participant (client or technician) of the room,
    or is staff/admin.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_admin_or_staff(user):
            return True
        room = obj
        return room.can_participate(user)


class CanSendMessage(BasePermission):
    """Allow sending messages if user is a participant and room is open/proposal/contract-linked."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.can_send(user)


class CanSendPriceOffer(BasePermission):
    """Only the technician participant can send price offers."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role != "technician":
            return False
        if not hasattr(user, "technician_profile"):
            return False
        return user.technician_profile == obj.technician


class CanAcceptPriceOffer(BasePermission):
    """Only the client participant can accept price offers."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role != "client":
            return False
        if not hasattr(user, "client_profile"):
            return False
        return user.client_profile == obj.client


class CanLinkContract(BasePermission):
    """
    Both client and technician can link a contract as long as the room
    is not CLOSED or BLOCKED.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.can_link_contract(user)


class CanManageMessage(BasePermission):
    """Allow editing/deleting messages based on ownership and time constraints."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_admin_or_staff(user):
            return True
        return obj.can_edit(user) or obj.can_delete(user)
