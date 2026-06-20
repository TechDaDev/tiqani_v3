"""Permission checks for Phase 8 contract execution."""

from rest_framework import permissions


class IsContractClient(permissions.BasePermission):
    """Only the contract's client can access."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return hasattr(user, 'client_profile') and obj.client.user == user


class IsContractTechnician(permissions.BasePermission):
    """Only the contract's technician can access."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return hasattr(user, 'technician_profile') and obj.technician.user == user


class IsContractParticipant(permissions.BasePermission):
    """Client or technician of the contract."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        # Works for both Contract and ExecutionMilestone
        contract = getattr(obj, 'contract', obj)
        is_client = hasattr(user, 'client_profile') and contract.client.user == user
        is_technician = hasattr(user, 'technician_profile') and contract.technician.user == user
        return is_client or is_technician


class IsMilestoneContractClient(permissions.BasePermission):
    """
    Check that the user is the client of the milestone's contract.
    Works with ExecutionMilestone objects.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        contract = obj.contract
        return hasattr(user, 'client_profile') and contract.client.user == user


class IsMilestoneContractTechnician(permissions.BasePermission):
    """
    Check that the user is the technician of the milestone's contract.
    Works with ExecutionMilestone objects.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        contract = obj.contract
        return hasattr(user, 'technician_profile') and contract.technician.user == user


class IsCompletionContractClient(permissions.BasePermission):
    """Check user is the client of the completion request's contract."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return hasattr(user, 'client_profile') and obj.contract.client.user == user


class IsCompletionContractTechnician(permissions.BasePermission):
    """Check user is the technician of the completion request's contract."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return hasattr(user, 'technician_profile') and obj.contract.technician.user == user
