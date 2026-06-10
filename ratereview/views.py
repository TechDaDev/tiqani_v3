from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404

from .models import Review
from .serializers import ReviewPublicSerializer
from accounts.models import TechnicianProfile


class TechnicianReviewsList(ListAPIView):
    """Public list of public reviews for a technician."""
    permission_classes = [AllowAny]
    serializer_class = ReviewPublicSerializer

    def get_queryset(self):
        technician = get_object_or_404(
            TechnicianProfile, id=self.kwargs["technician_id"]
        )
        return Review.objects.filter(
            technician=technician, is_public=True
        ).order_by("-created_at")


class ReviewDetailView(RetrieveAPIView):
    """Public detail for a single public review."""
    permission_classes = [AllowAny]
    serializer_class = ReviewPublicSerializer
    queryset = Review.objects.filter(is_public=True)
    lookup_field = "id"
