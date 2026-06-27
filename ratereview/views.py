"""Views for review creation, response, helpful, report, and moderation."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.mixins import UpdateModelMixin
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import Review, ReviewModerationAction, ReviewReport
from .serializers import (
    ReviewPublicSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    ReviewTechnicianResponseSerializer, ReviewHelpfulSerializer,
    ReviewReportSerializer, ContractReviewCreateSerializer,
    ReviewEligibilitySerializer, UserReputationSnapshotSerializer,
)
from .permissions import IsReviewOwner, IsReviewedTechnician, IsPlatformAdminOrStaff
from accounts.models import TechnicianProfile
from contract.models import Contract
from .services import (
    create_contract_review,
    get_review_eligibility,
    moderate_review,
    recalculate_user_reputation,
    update_contract_review,
)

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
        # Notify technician
        from notification.services import notify_review_created
        try:
            notify_review_created(review, request.user)
        except Exception:
            pass
        public_serializer = ReviewPublicSerializer(review)
        return Response(public_serializer.data, status=status.HTTP_201_CREATED)


class ContractReviewEligibilityView(GenericAPIView):
    """GET /api/contracts/<contract_id>/review-eligibility/."""
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewEligibilitySerializer

    def get(self, request, *args, **kwargs):
        contract = get_object_or_404(
            Contract.objects.select_related("client__user", "technician__user"),
            id=kwargs["contract_id"],
        )
        eligibility = get_review_eligibility(contract, request.user)
        return Response(self.get_serializer(eligibility.as_dict()).data)


class ContractReviewCreateView(GenericAPIView):
    """POST /api/contracts/<contract_id>/reviews/."""
    permission_classes = [IsAuthenticated]
    serializer_class = ContractReviewCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dimensions = {
            key: data.get(key)
            for key in [
                "work_quality_rating",
                "communication_rating",
                "timeliness_rating",
                "professionalism_rating",
            ]
            if key in data
        }
        try:
            review, created = create_contract_review(
                contract_id=kwargs["contract_id"],
                actor=request.user,
                rating=data["rating"],
                title=data.get("title", ""),
                comment=data.get("comment", ""),
                dimensions=dimensions,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Contract.DoesNotExist:
            return Response({"detail": "CONTRACT_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            ReviewPublicSerializer(review).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


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
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            update_contract_review(review=review, actor=request.user, data=serializer.validated_data)
        except PermissionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
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
        from notification.services import notify_review_responded
        try:
            notify_review_responded(review, request.user)
        except Exception:
            pass
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
            from notification.services import notify_review_reported
            try:
                notify_review_reported(review, request.user)
            except Exception:
                pass

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
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.RESTORE,
            reason=request.data.get("reason", ""),
        )
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateHideView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/hide/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.HIDE,
            reason=request.data.get("reason", ""),
        )
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateVerifyView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/verify/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.VERIFY,
            reason=request.data.get("reason", ""),
        )
        return Response(ReviewPublicSerializer(review).data)


class ReviewModerateUnverifyView(GenericAPIView):
    """POST /api/reviews/<id>/moderate/unverify/ — admin only."""
    permission_classes = [IsPlatformAdminOrStaff]

    def get_object(self):
        return get_object_or_404(Review, id=self.kwargs['id'])

    def post(self, request, *args, **kwargs):
        review = self.get_object()
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.UNVERIFY,
            reason=request.data.get("reason", ""),
        )
        return Response(ReviewPublicSerializer(review).data)


class UserReputationView(GenericAPIView):
    """GET /api/users/<user_id>/reputation/."""
    permission_classes = [AllowAny]
    serializer_class = UserReputationSnapshotSerializer

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        user = get_object_or_404(get_user_model(), id=kwargs["user_id"])
        role = request.query_params.get("role") or user.role
        snapshot = recalculate_user_reputation(user, role=role)
        return Response(self.get_serializer(snapshot).data)


class UserReviewsList(ListAPIView):
    """GET /api/users/<user_id>/reviews/."""
    permission_classes = [AllowAny]
    serializer_class = ReviewPublicSerializer

    def get_queryset(self):
        from django.contrib.auth import get_user_model
        user = get_object_or_404(get_user_model(), id=self.kwargs["user_id"])
        return Review.objects.filter(
            reviewee=user,
            status=Review.Status.PUBLISHED,
            is_public=True,
        ).order_by("-created_at")
