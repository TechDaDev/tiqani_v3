"""
Client-specific API views for profile management.
All endpoints require authentication and the user must have client role.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import ClientProfile
from .client_serializers import ClientProfileSerializer, IncompleteFieldsSerializer


class IsClient(IsAuthenticated):
    """Permission class to verify user is a client."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'client'


# --- Profile Management ---

class ClientProfileView(APIView):
    """
    GET: Retrieve client profile
    PATCH: Update client profile (limited fields via CustomUser)
    """
    permission_classes = [IsClient]

    def get(self, request):
        """Retrieve client profile."""
        profile = get_object_or_404(ClientProfile, user=request.user)
        serializer = ClientProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update client profile - updates User model fields."""
        profile = get_object_or_404(ClientProfile, user=request.user)
        user = profile.user
        
        # Editable fields mapping
        allowed_fields = {
            'phone_number': 'phone_number',
            'address': 'address',
            'governorate': 'governorate',
            'gender': 'gender',
            'date_of_birth': 'date_of_birth',
            'profile_image': 'profile_image'
        }
        
        # Update user fields
        updated = False
        for api_field, model_field in allowed_fields.items():
            if api_field in request.data:
                setattr(user, model_field, request.data[api_field])
                updated = True
        
        if updated:
            user.save()
            # Profile completion auto-recalculates on profile.save()
            profile.save()
        
        serializer = ClientProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- Incomplete Fields ---

class IncompleteFieldsView(APIView):
    """
    GET: Retrieve incomplete profile fields for authenticated user
    Works for both client and technician roles
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of incomplete required fields."""
        user = request.user
        
        # Get profile based on role
        if user.role == 'client':
            profile = get_object_or_404(ClientProfile, user=user)
        elif user.role == 'technician':
            from .models import TechnicianProfile
            profile = get_object_or_404(TechnicianProfile, user=user)
        else:
            return Response({
                "detail": "Profile not found for this user role."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get incomplete fields
        incomplete = profile.get_incomplete_fields()
        total_required = len(profile.REQ_USER_FIELDS) + len(profile.REQ_PROFILE_FIELDS)
        completed = total_required - len(incomplete)
        percentage = (completed / total_required * 100) if total_required > 0 else 100.0
        
        response_data = {
            'is_complete': profile.is_complete,
            'incomplete_fields': incomplete,
            'total_required': total_required,
            'completed_count': completed,
            'completion_percentage': round(percentage, 2)
        }
        
        serializer = IncompleteFieldsSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
