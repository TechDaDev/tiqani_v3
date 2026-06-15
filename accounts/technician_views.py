"""
Technician-specific API views for profile, skills, images, and availability management.
All endpoints require authentication and the user must have technician role.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import TechnicianProfile, TechnicianImage, TechnicianSkillSet, CustomUser
from .technician_serializers import (
    TechnicianProfileSerializer,
    TechnicianListSerializer,
    TechnicianImageSerializer,
    TechnicianSkillSetSerializer,
    TechnicianAvailabilitySerializer,
)


class IsTechnician(IsAuthenticated):
    """Permission class to verify user is a technician."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'technician'


# --- Pagination ---

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# --- Public Technician List ---

class TechnicianListView(APIView):
    """
    GET: List technicians with role-based filtering
    
    Access Control:
    - Anonymous users: See only approved and complete technicians
    - Client users: See only approved and complete technicians
    - Admin users: See all technicians (including incomplete/unapproved)
    
    Filters: search (full_name, job_title, about), governorate, is_available, 
             skill_id, category_id, min_rating
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """List technicians based on user role and authentication status."""
        queryset = TechnicianProfile.objects.select_related('user')

        # Apply role-based filtering
        user = request.user
        is_admin = user.is_authenticated and user.is_staff
        
        # Only show approved and complete if not admin
        if not is_admin:
            queryset = queryset.filter(
                is_complete=True,
                approved=True
            )

        # Search by keyword (full_name, job_title, about)
        search = request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(job_title__icontains=search) |
                Q(about__icontains=search)
            )

        # Filter by governorate
        governorate = request.query_params.get('governorate')
        if governorate:
            queryset = queryset.filter(user__governorate=governorate)

        # Filter by availability
        is_available = request.query_params.get('is_available')
        if is_available is not None:
            is_available = is_available.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_available=is_available)

        # Filter by skill
        skill_id = request.query_params.get('skill_id')
        if skill_id:
            queryset = queryset.filter(skill_set__skills__id=skill_id).distinct()

        # Filter by category
        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(
                skill_set__categories__id=category_id
            ).distinct()

        # Filter by minimum rating
        min_rating = request.query_params.get('min_rating')
        if min_rating is not None:
            try:
                min_rating_val = float(min_rating)
                if 0 <= min_rating_val <= 5:
                    queryset = queryset.filter(rate__gte=min_rating_val)
            except (ValueError, TypeError):
                pass

        # Order by rating
        order_by = request.query_params.get('order_by', '-rate')
        queryset = queryset.order_by(order_by)

        # Pagination
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = TechnicianListSerializer(paginated_queryset, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


# --- Profile Management ---

class TechnicianProfileView(APIView):
    """
    GET: Retrieve technician profile
    PATCH: Update technician profile (job_title, about, years_of_expertise, etc.)
    """
    permission_classes = [IsTechnician]

    def get(self, request):
        """Retrieve technician profile."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        serializer = TechnicianProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update technician profile."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        serializer = TechnicianProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- Skills Management ---

class TechnicianSkillsView(APIView):
    """
    GET: Retrieve technician skills, categories, and sub-skills
    PATCH: Update technician skills assignment
    """
    permission_classes = [IsTechnician]

    def get(self, request):
        """Retrieve technician skills."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)

        # If the profile is not linked yet, try to attach the existing skill set
        skill_set = getattr(profile, 'skill_set', None)
        if not skill_set:
            skill_set = TechnicianSkillSet.objects.filter(technician=profile).order_by('-created_at').first()

        if not skill_set:
            return Response({
                "detail": "No skill set assigned yet.",
                "categories": [],
                "skills": [],
                "sub_skills": []
            }, status=status.HTTP_200_OK)

        serializer = TechnicianSkillSetSerializer(skill_set, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update technician skills."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        
        # Create or get skill set
        skill_set, created = TechnicianSkillSet.objects.get_or_create(technician=profile)

        serializer = TechnicianSkillSetSerializer(
            skill_set,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Update profile completion status
        profile.save()
        
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- Portfolio Images Management ---

class TechnicianImagesListView(APIView):
    """
    GET: List technician portfolio images
    POST: Upload new portfolio image
    """
    permission_classes = [IsTechnician]

    def get(self, request):
        """List all technician images."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        images = profile.images.all().order_by('-created_at')
        serializer = TechnicianImageSerializer(
            images,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Upload new portfolio image."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        
        serializer = TechnicianImageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # Save with technician reference
        image = serializer.save(technician=profile)
        
        # Update profile completion
        profile.save()
        
        return Response(
            TechnicianImageSerializer(image, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class TechnicianImageDetailView(APIView):
    """
    PATCH: Update image description
    DELETE: Remove portfolio image
    """
    permission_classes = [IsTechnician]

    def patch(self, request, image_id):
        """Update image description."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        image = get_object_or_404(TechnicianImage, id=image_id, technician=profile)
        
        serializer = TechnicianImageSerializer(
            image,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, image_id):
        """Delete portfolio image."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        image = get_object_or_404(TechnicianImage, id=image_id, technician=profile)
        
        image.delete()
        
        # Update profile completion
        profile.save()
        
        return Response(
            {"detail": "Image deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


# --- Availability Management ---

class TechnicianAvailabilityView(APIView):
    """
    GET: Check technician availability status
    PATCH: Update availability status
    """
    permission_classes = [IsTechnician]

    def get(self, request):
        """Get availability status."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        return Response({
            "is_available": profile.is_available,
            "last_active": profile.last_active,
            "is_online": profile.is_online
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update availability status."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        serializer = TechnicianAvailabilitySerializer(
            profile,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            "is_available": profile.is_available,
            "message": f"Availability status updated to {'available' if profile.is_available else 'unavailable'}."
        }, status=status.HTTP_200_OK)


# --- Ratings View ---

class TechnicianRatingsView(APIView):
    """
    GET: Retrieve technician ratings and reviews summary
    """
    permission_classes = [IsTechnician]

    def get(self, request):
        """Get technician ratings and review statistics."""
        profile = get_object_or_404(TechnicianProfile, user=request.user)
        
        # Build ratings response
        response_data = {
            "average_rating": float(profile.rate),
            "total_reviews": 0,  # Will be calculated from related reviews model when implemented
            "rating_breakdown": {
                "5_stars": 0,
                "4_stars": 0,
                "3_stars": 0,
                "2_stars": 0,
                "1_stars": 0
            },
            "recent_reviews": []
        }
        
        # TODO: Calculate from reviews_received relationship when rating model is added
        
        return Response(response_data, status=status.HTTP_200_OK)


# --- Public Technician Detail ---

class TechnicianDetailView(APIView):
    """
    GET: Public detail for an approved technician.
    Owner/admin can see own profile even if not approved.
    """
    permission_classes = [AllowAny]

    def get(self, request, id):
        profile = get_object_or_404(TechnicianProfile, id=id)

        # Owner or admin can see unapproved profiles
        user = request.user
        is_owner = user.is_authenticated and user == profile.user
        is_admin = user.is_authenticated and user.is_staff

        if not profile.approved and not is_owner and not is_admin:
            return Response(
                {"detail": "Technician not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TechnicianProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)
