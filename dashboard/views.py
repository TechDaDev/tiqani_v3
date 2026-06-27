"""Admin dashboard views — summary, users, technicians, contracts, reviews, finance, activity."""

import os
from decimal import Decimal
from django.conf import settings
from django.db import models as db_models
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import (
    ListAPIView, RetrieveAPIView, UpdateAPIView, GenericAPIView, CreateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract, ContractStage
from contract.services import cancel_contract
from wallet.models import (
    PlatformEarning, PaymentIntent, WithdrawalRequest,
    Wallet, ContractPaymentBreakdown,
)
from wallet.services import (
    approve_withdrawal_request, reject_withdrawal_request,
    mark_payment_intent_paid,
)
from ratereview.models import Review, ReviewModerationAction
from ratereview.services import moderate_review
from notification.models import ActivityLog, Notification
from notification.services import (
    notify_technician_approved, notify_technician_rejected,
    create_activity,
)
from dealership.services import get_dealership_metrics

from .permissions import (
    IsPlatformAdmin, IsSystemAdmin, IsFinanceAdmin,
    IsAccountManager, IsContentModerator, IsAdminOrStaff,
)
from .serializers import (
    AdminUserListSerializer, AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    AdminTechnicianListSerializer, AdminTechnicianDetailSerializer,
    TechnicianRejectSerializer,
    AdminContractListSerializer, AdminContractDetailSerializer,
    AdminContractForceCancelSerializer,
    AdminReviewListSerializer, AdminReviewDetailSerializer,
    AdminPlatformEarningSerializer, AdminPaymentIntentSerializer,
    AdminWithdrawalSerializer, AdminWithdrawalActionSerializer,
    AdminPaymentIntentMarkPaidSerializer,
    AdminActivitySerializer,
)

User = get_user_model()


def _require_reason(request):
    reason = str(request.data.get("reason") or request.data.get("note") or "").strip()
    if not reason:
        return None, Response(
            {"reason": ["A reason is required for administrative write actions."]},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return reason, None


def _admin_activity(verb, *, actor, target_type, target_id, target_repr, previous_state, new_state, reason):
    create_activity(
        verb,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        target_repr=target_repr,
        audience="admin",
        metadata={
            "reason": reason,
            "previous_state": previous_state,
            "new_state": new_state,
        },
    )


# =====================================================================
# Dashboard summary
# =====================================================================

class DashboardSummaryView(GenericAPIView):
    """GET /api/admin/dashboard/summary/ — aggregated platform stats."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request, *args, **kwargs):
        user_counts = User.objects.aggregate(
            total=Count('id'),
            clients=Count('id', filter=Q(role='client')),
            technicians=Count('id', filter=Q(role='technician')),
            dealerships=Count('id', filter=Q(role='dealership')),
            admins=Count('id', filter=Q(role='admin')),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
        )
        tech_counts = TechnicianProfile.objects.aggregate(
            total=Count('id'),
            approved_count=Count('id', filter=Q(approved=True)),
            pending_count=Count('id', filter=Q(approved=False)),
            available_count=Count('id', filter=Q(is_available=True)),
        )
        contract_counts = Contract.objects.aggregate(
            total=Count('id'),
            draft_count=Count('id', filter=Q(status='draft')),
            pending_acceptance_count=Count('id', filter=Q(status='pending_acceptance')),
            in_progress_count=Count('id', filter=Q(status='in_progress')),
            completed_count=Count('id', filter=Q(status='completed')),
            canceled_count=Count('id', filter=Q(status='canceled')),
        )
        finance = {
            'total_contract_value': str(
                Contract.objects.filter(agreed_amount__isnull=False).aggregate(
                    v=Sum('agreed_amount'))['v'] or Decimal('0.00')
            ),
            'platform_earnings_pending': str(
                PlatformEarning.objects.filter(status='pending').aggregate(
                    v=Sum('amount'))['v'] or Decimal('0.00')
            ),
            'platform_earnings_earned': str(
                PlatformEarning.objects.filter(status='earned').aggregate(
                    v=Sum('amount'))['v'] or Decimal('0.00')
            ),
            'payment_intents_pending': PaymentIntent.objects.filter(
                status=PaymentIntent.Status.PENDING).count(),
            'withdrawals_pending': WithdrawalRequest.objects.filter(
                status=WithdrawalRequest.Status.PENDING).count(),
        }
        review_counts = Review.objects.aggregate(
            total=Count('id'),
            public=Count('id', filter=Q(is_public=True)),
            hidden=Count('id', filter=Q(is_public=False)),
            verified=Count('id', filter=Q(is_verified=True)),
            flagged=Count('id', filter=Q(flagged_at__isnull=False)),
        )
        notif_counts = {
            'total': Notification.objects.count(),
            'unread': Notification.objects.filter(is_read=False).count(),
            'activity_logs': ActivityLog.objects.count(),
        }
        data = {
            'users': user_counts,
            'technicians': {
                'total': tech_counts['total'],
                'approved': tech_counts['approved_count'],
                'pending': tech_counts['pending_count'],
                'available': tech_counts['available_count'],
            },
            'contracts': {
                'total': contract_counts['total'],
                'draft': contract_counts['draft_count'],
                'pending_acceptance': contract_counts['pending_acceptance_count'],
                'in_progress': contract_counts['in_progress_count'],
                'completed': contract_counts['completed_count'],
                'canceled': contract_counts['canceled_count'],
            },
            'finance': finance,
            'reviews': review_counts,
            'notifications': notif_counts,
            'dealerships': get_dealership_metrics(),
        }
        return Response(data)


class PlatformStatisticsView(DashboardSummaryView):
    """GET /api/admin/platform-statistics/ — release-readiness alias."""


class PlatformHealthView(GenericAPIView):
    """GET /api/admin/platform-health/ — staff-only summarized operations status."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request, *args, **kwargs):
        db_status = "ok"
        try:
            from django.db import connection

            connection.ensure_connection()
        except Exception:
            db_status = "error"

        return Response({
            "status": "ok" if db_status == "ok" else "degraded",
            "database": db_status,
            "redis": "configured" if getattr(settings, "CELERY_BROKER_URL", "") else "not_configured",
            "debug": bool(settings.DEBUG),
            "version": os.environ.get("APP_VERSION", ""),
        }, status=status.HTTP_200_OK if db_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE)


# =====================================================================
# User management
# =====================================================================

class AdminUserListView(ListAPIView):
    """GET /api/admin/users/ — list users."""
    permission_classes = [IsAuthenticated, IsAccountManager]
    serializer_class = AdminUserListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['created_at', 'username', 'role']
    filterset_fields = {
        'role': ['exact'],
        'is_active': ['exact'],
        'governorate': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return User.objects.all().order_by('-created_at')


class AdminUserDetailUpdateView(GenericAPIView):
    """
    GET /api/admin/users/<id>/ — user detail
    PATCH /api/admin/users/<id>/ — update user (safe fields only)
    """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return AdminUserUpdateSerializer
        return AdminUserDetailSerializer

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsSystemAdmin()]
        return [IsAuthenticated(), IsAccountManager()]

    def get(self, request, *args, **kwargs):
        self.check_permissions(request)
        user = self.get_object()
        serializer = AdminUserDetailSerializer(user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        self.check_permissions(request)
        user = self.get_object()
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserDetailSerializer(user).data)


class AdminUserActivateView(GenericAPIView):
    """POST /api/admin/users/<id>/activate/."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    throttle_scope = "admin_write"

    def post(self, request, *args, **kwargs):
        reason, error = _require_reason(request)
        if error:
            return error
        user = get_object_or_404(User, id=kwargs['id'])
        previous_state = {"is_active": user.is_active}
        user.is_active = True
        user.save(update_fields=['is_active'])
        _admin_activity(
            "user_restored",
            actor=request.user,
            target_type="user",
            target_id=user.id,
            target_repr=user.username,
            previous_state=previous_state,
            new_state={"is_active": user.is_active},
            reason=reason,
        )
        return Response({'status': 'ok', 'is_active': True})


class AdminUserDeactivateView(GenericAPIView):
    """POST /api/admin/users/<id>/deactivate/."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    throttle_scope = "admin_write"

    def post(self, request, *args, **kwargs):
        reason, error = _require_reason(request)
        if error:
            return error
        user = get_object_or_404(User, id=kwargs['id'])
        previous_state = {"is_active": user.is_active}
        user.is_active = False
        user.save(update_fields=['is_active'])
        _admin_activity(
            "user_suspended",
            actor=request.user,
            target_type="user",
            target_id=user.id,
            target_repr=user.username,
            previous_state=previous_state,
            new_state={"is_active": user.is_active},
            reason=reason,
        )
        return Response({'status': 'ok', 'is_active': False})


# =====================================================================
# Technician moderation
# =====================================================================

class AdminTechnicianListView(ListAPIView):
    """GET /api/admin/technicians/ — list technicians."""
    permission_classes = [IsAuthenticated, IsAccountManager]
    serializer_class = AdminTechnicianListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__username', 'user__email', 'job_title']
    ordering_fields = ['created_at', 'rate']
    filterset_fields = {
        'approved': ['exact'],
        'is_available': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        qs = TechnicianProfile.objects.select_related('user').all()
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            qs = qs.filter(rate__gte=min_rating)
        governorate = self.request.query_params.get('governorate')
        if governorate:
            qs = qs.filter(user__governorate=governorate)
        return qs.order_by('-created_at')


class AdminTechnicianPendingView(ListAPIView):
    """GET /api/admin/technicians/pending/ — unapproved technicians."""
    permission_classes = [IsAuthenticated, IsAccountManager]
    serializer_class = AdminTechnicianListSerializer

    def get_queryset(self):
        return TechnicianProfile.objects.select_related('user').filter(
            approved=False, user__is_active=True
        ).order_by('-created_at')


class AdminTechnicianDetailView(RetrieveAPIView):
    """GET /api/admin/technicians/<id>/ — detail."""
    permission_classes = [IsAuthenticated, IsAccountManager]
    serializer_class = AdminTechnicianDetailSerializer
    queryset = TechnicianProfile.objects.select_related('user').all()
    lookup_field = 'id'


class AdminTechnicianApproveView(GenericAPIView):
    """POST /api/admin/technicians/<id>/approve/."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    throttle_scope = "admin_write"

    def post(self, request, *args, **kwargs):
        reason, error = _require_reason(request)
        if error:
            return error
        tech = get_object_or_404(TechnicianProfile, id=kwargs['id'])
        previous_state = {"approved": tech.approved, "is_available": tech.is_available}
        tech.approved = True
        tech.save(update_fields=['approved'])
        _admin_activity(
            "technician_approved",
            actor=request.user,
            target_type="technician",
            target_id=tech.id,
            target_repr=str(tech),
            previous_state=previous_state,
            new_state={"approved": tech.approved, "is_available": tech.is_available},
            reason=reason,
        )
        notify_technician_approved(tech, request.user)
        return Response({'status': 'ok', 'approved': True})


class AdminTechnicianRejectView(GenericAPIView):
    """POST /api/admin/technicians/<id>/reject/."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = TechnicianRejectSerializer
    throttle_scope = "admin_write"

    def post(self, request, *args, **kwargs):
        reason, error = _require_reason(request)
        if error:
            return error
        tech = get_object_or_404(TechnicianProfile, id=kwargs['id'])
        previous_state = {"approved": tech.approved, "is_available": tech.is_available}
        tech.approved = False
        tech.is_available = False
        tech.save(update_fields=['approved', 'is_available'])
        _admin_activity(
            "technician_suspended",
            actor=request.user,
            target_type="technician",
            target_id=tech.id,
            target_repr=str(tech),
            previous_state=previous_state,
            new_state={"approved": tech.approved, "is_available": tech.is_available},
            reason=reason,
        )
        notify_technician_rejected(tech, request.user)
        return Response({'status': 'ok', 'approved': False})


# =====================================================================
# Contract monitoring
# =====================================================================

class AdminContractListView(ListAPIView):
    """GET /api/admin/contracts/ — list all contracts."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminContractListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at', 'agreed_amount', 'status']
    filterset_fields = {
        'status': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        qs = Contract.objects.select_related('client', 'technician').all()
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        if min_amount:
            qs = qs.filter(agreed_amount__gte=min_amount)
        if max_amount:
            qs = qs.filter(agreed_amount__lte=max_amount)
        has_breakdown = self.request.query_params.get('has_payment_breakdown')
        if has_breakdown == 'true':
            qs = qs.filter(payment_breakdown__isnull=False)
        elif has_breakdown == 'false':
            qs = qs.filter(payment_breakdown__isnull=True)
        return qs.order_by('-created_at')


class AdminContractDetailView(RetrieveAPIView):
    """GET /api/admin/contracts/<id>/ — full detail."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminContractDetailSerializer
    queryset = Contract.objects.all()
    lookup_field = 'id'


class AdminContractForceCancelView(GenericAPIView):
    """POST /api/admin/contracts/<id>/force-cancel/ — system_admin only."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    serializer_class = AdminContractForceCancelSerializer
    throttle_scope = "admin_write"

    def post(self, request, *args, **kwargs):
        reason, error = _require_reason(request)
        if error:
            return error
        contract = get_object_or_404(Contract, id=kwargs['id'])
        if contract.status == 'completed':
            return Response({'error': 'Cannot cancel a completed contract.'},
                            status=status.HTTP_400_BAD_REQUEST)
        contract = cancel_contract(contract, request.user, reason=reason)
        return Response({'status': 'ok', 'contract_status': contract.status})


# =====================================================================
# Review moderation
# =====================================================================

class AdminReviewListView(ListAPIView):
    """GET /api/admin/reviews/ — list all reviews."""
    permission_classes = [IsAuthenticated, IsContentModerator]
    serializer_class = AdminReviewListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at', 'rating', 'reported_count']
    filterset_fields = {
        'is_public': ['exact'],
        'is_verified': ['exact'],
        'rating': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        qs = Review.objects.select_related('reviewer', 'technician').all()
        flagged = self.request.query_params.get('flagged')
        if flagged == 'true':
            qs = qs.filter(flagged_at__isnull=False)
        return qs.order_by('-created_at')


class AdminReviewFlaggedView(ListAPIView):
    """GET /api/admin/reviews/flagged/ — flagged reviews."""
    permission_classes = [IsAuthenticated, IsContentModerator]
    serializer_class = AdminReviewListSerializer

    def get_queryset(self):
        return Review.objects.filter(flagged_at__isnull=False).order_by('-reported_count')


class AdminReviewDetailView(RetrieveAPIView):
    """GET /api/admin/reviews/<id>/ — detail with reports."""
    permission_classes = [IsAuthenticated, IsContentModerator]
    serializer_class = AdminReviewDetailSerializer
    queryset = Review.objects.all()
    lookup_field = 'id'


class AdminReviewHideView(GenericAPIView):
    """POST /api/admin/reviews/<id>/hide/."""
    permission_classes = [IsAuthenticated, IsContentModerator]

    def post(self, request, *args, **kwargs):
        review = get_object_or_404(Review, id=kwargs['id'])
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.HIDE,
            reason=request.data.get("reason", ""),
        )
        return Response({'status': 'ok', 'is_public': False})


class AdminReviewPublishView(GenericAPIView):
    """POST /api/admin/reviews/<id>/publish/."""
    permission_classes = [IsAuthenticated, IsContentModerator]

    def post(self, request, *args, **kwargs):
        review = get_object_or_404(Review, id=kwargs['id'])
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.RESTORE,
            reason=request.data.get("reason", ""),
        )
        return Response({'status': 'ok', 'is_public': True})


class AdminReviewVerifyView(GenericAPIView):
    """POST /api/admin/reviews/<id>/verify/."""
    permission_classes = [IsAuthenticated, IsContentModerator]

    def post(self, request, *args, **kwargs):
        review = get_object_or_404(Review, id=kwargs['id'])
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.VERIFY,
            reason=request.data.get("reason", ""),
        )
        return Response({'status': 'ok', 'is_verified': True})


class AdminReviewUnverifyView(GenericAPIView):
    """POST /api/admin/reviews/<id>/unverify/."""
    permission_classes = [IsAuthenticated, IsContentModerator]

    def post(self, request, *args, **kwargs):
        review = get_object_or_404(Review, id=kwargs['id'])
        moderate_review(
            review=review,
            actor=request.user,
            action=ReviewModerationAction.Action.UNVERIFY,
            reason=request.data.get("reason", ""),
        )
        return Response({'status': 'ok', 'is_verified': False})


# =====================================================================
# Finance / Oversight
# =====================================================================

class AdminFinanceSummaryView(GenericAPIView):
    """GET /api/admin/finance/summary/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]

    def get(self, request, *args, **kwargs):
        total_earned = PlatformEarning.objects.filter(
            status=PlatformEarning.Status.EARNED
        ).aggregate(v=Sum('amount'))['v'] or Decimal('0.00')
        total_pending = PlatformEarning.objects.filter(
            status=PlatformEarning.Status.PENDING
        ).aggregate(v=Sum('amount'))['v'] or Decimal('0.00')
        total_wallet = Wallet.objects.aggregate(v=Sum('balance'))['v'] or Decimal('0.00')

        return Response({
            'total_platform_earnings': str(total_earned + total_pending),
            'pending_platform_earnings': str(total_pending),
            'earned_platform_earnings': str(total_earned),
            'payment_intents_pending': PaymentIntent.objects.filter(
                status=PaymentIntent.Status.PENDING).count(),
            'payment_intents_paid': PaymentIntent.objects.filter(
                status=PaymentIntent.Status.PAID).count(),
            'withdrawals_pending': WithdrawalRequest.objects.filter(
                status=WithdrawalRequest.Status.PENDING).count(),
            'withdrawals_approved': WithdrawalRequest.objects.filter(
                status=WithdrawalRequest.Status.APPROVED).count(),
            'withdrawals_paid': WithdrawalRequest.objects.filter(
                status=WithdrawalRequest.Status.PAID).count(),
            'total_wallet_balances': str(total_wallet),
        })


class AdminPlatformEarningListView(ListAPIView):
    """GET /api/admin/finance/platform-earnings/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminPlatformEarningSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'status': ['exact'],
        'earning_type': ['exact'],
        'contract': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return PlatformEarning.objects.all().order_by('-created_at')


class AdminPaymentIntentListView(ListAPIView):
    """GET /api/admin/finance/payment-intents/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminPaymentIntentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'status': ['exact'],
        'purpose': ['exact'],
        'user': ['exact'],
        'contract': ['exact'],
    }

    def get_queryset(self):
        return PaymentIntent.objects.all().order_by('-created_at')


class AdminWithdrawalListView(ListAPIView):
    """GET /api/admin/finance/withdrawals/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminWithdrawalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'status': ['exact'],
        'user': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return WithdrawalRequest.objects.all().order_by('-created_at')


class AdminWithdrawalApproveView(GenericAPIView):
    """POST /api/admin/finance/withdrawals/<id>/approve/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminWithdrawalActionSerializer

    def post(self, request, *args, **kwargs):
        wr = get_object_or_404(WithdrawalRequest, id=kwargs['id'])
        note = request.data.get('note', '')
        try:
            wr = approve_withdrawal_request(wr, request.user, note=note)
            return Response({'status': 'ok', 'withdrawal_status': wr.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminWithdrawalRejectView(GenericAPIView):
    """POST /api/admin/finance/withdrawals/<id>/reject/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminWithdrawalActionSerializer

    def post(self, request, *args, **kwargs):
        wr = get_object_or_404(WithdrawalRequest, id=kwargs['id'])
        note = request.data.get('note', '')
        try:
            wr = reject_withdrawal_request(wr, request.user, note=note)
            return Response({'status': 'ok', 'withdrawal_status': wr.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminPaymentIntentMarkPaidView(GenericAPIView):
    """POST /api/admin/finance/payment-intents/<id>/mark-paid/."""
    permission_classes = [IsAuthenticated, IsFinanceAdmin]
    serializer_class = AdminPaymentIntentMarkPaidSerializer

    def post(self, request, *args, **kwargs):
        pi = get_object_or_404(PaymentIntent, id=kwargs['id'])
        try:
            pi = mark_payment_intent_paid(pi)
            return Response({'status': 'ok', 'payment_status': pi.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# Activity feed (admin alias for notification activity)
# =====================================================================

class AdminActivityListView(ListAPIView):
    """GET /api/admin/activity/ — activity feed."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminActivitySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'actor': ['exact'],
        'audience': ['exact'],
        'target_type': ['exact'],
        'verb': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    def get_queryset(self):
        return ActivityLog.objects.all().order_by('-created_at')
