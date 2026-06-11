"""Views for review creation, response, helpful, report, and moderation."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.mixins import UpdateModelMixin
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import Review, ReviewReport
from .serializers import (
    ReviewPublicSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    ReviewTechnicianResponseSerializer, ReviewHelpfulSerializer,
    ReviewReportSerializer,
)
from .permissions import IsReviewOwner, IsReviewedTechnician, IsPlatformAdminOrStaff
from accounts.models import TechnicianProfile

REPORT_THRESHOLD = 3


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


class ReviewCreateView(CreateAPIView):
    """POST /api/reviews/ — create review for completed contract."""
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewCreateSerializer

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        public_serializer = ReviewPublicSerializer(review)
        return Response(public_serializer.data, status=status.HTTP_201_CREATED)


class ReviewDetailUpdateView(GenericAPIView):
    """
    GET /api/reviews/<id>/ — public detail
    PATCH /api/reviews/<id>/ — reviewer updates own review
    """
    queryset = Review.objects.all()
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ReviewUpdateSerializer
        return ReviewPublicSerializer

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsReviewOwner()]
        return [AllowAny()]

    def get(self, request, *args, **kwargs):
        """Public detail — only public reviews."""
        review = get_object_or_404(Review.objects.filter(is_public=True), id=kwargs['id'])
        serializer = ReviewPublicSerializer(review)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """Reviewer updates own review."""
        review = self.get_object()
        self.check_object_permissions(request, review)
        if not review.is_public:
            return Response({'detail': 'Cannot edit a hidden review.'}, status=status.HTTP_403_FORBIDDEN)
        if review.flagged_at:
            return Response({'detail': 'Cannot edit a flagged review.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ReviewPublicSerializer(review).data)


class ReviewTechnicianResponseView(GenericAPIView):
    """POST /api/reviews/<id>/respond/ — technician responds to review."""
    permission_classes = [IsAuthenticated, IsReviewedTechnician]
    serializer_class = ReviewTechnicianResponseSerializer

    def get_object(self):
        review = get_object_or_404(Review, id=self.kwargs['id'])
        self.check_object_permissions(self.request, review)
        if not review.is_public:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot respond to a hidden review.")
        return review

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(review, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ReviewPublicSerializer(review).data, status=status.HTTP_200_OK)


class ReviewHelpfulView(GenericAPIView):
    """POST /api/reviews/<id>/helpful/ — mark review as helpful (idempotent)."""
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        user = request.user

        from .models import ReviewHelpful
        vote, created = ReviewHelpful.objects.get_or_create(review=review, user=user)
        if created:
            review.mark_helpful()

        return Response({'helpful_count': review.helpful_count}, status=status.HTTP_200_OK)


class ReviewReportView(GenericAPIView):
    """POST /api/reviews/<id>/report/ — report a review (idempotent)."""
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewReportSerializer

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report, created = ReviewReport.objects.get_or_create(
            review=review,
            reporter=request.user,
            defaults={
                'reason': serializer.validated_data.get('reason', 'other'),
                'comment': serializer.validated_data.get('comment', ''),
            },
        )

        if created:
            review.flag()
            # Auto-flag if threshold reached
            if review.reported_count >= REPORT_THRESHOLD and not review.flagged_at:
                review.flagged_at = timezone.now()
                review.save(update_fields=['flagged_at'])

        return Response({
            'reported': created,
            'reported_count': review.reported_count,
        }, status=status.HTTP_200_OK)


# --- Moderation views ---

class ReviewModeratePublishView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/publish/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        review.publish()
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateHideView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/hide/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        review.hide()
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateVerifyView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/verify/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        review.is_verified = True
        review.save(update_fields=['is_verified', 'updated_at'])
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateUnverifyView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/unverify/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        review.is_verified = False
        review.save(update_fields=['is_verified', 'updated_at'])
        return Response(ReviewPublicSerializer(review).data)
