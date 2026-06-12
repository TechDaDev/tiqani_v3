"""
Dealership views — profiles, recharges, cashouts, admin endpoints.
"""

import logging
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import (
    ListAPIView, RetrieveAPIView, GenericAPIView, CreateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipCreditLedger,
    DealershipSettlement,
)
from .permissions import (
    IsDealership,
    IsClientUser,
    IsDealershipOrAdmin,
    IsSystemAdminOrFinance,
    IsAccountManagerOrFinance,
    IsContentModeratorDenied,
)
from .serializers import (
    DealershipProfileSerializer,
    DealershipSummarySerializer,
    DealershipRechargeFeeConfigSerializer,
    RechargePreviewSerializer,
    RechargePreviewResponseSerializer,
    RechargeCreateSerializer,
    RechargeResponseSerializer,
    CashoutPreviewSerializer,
    CashoutPreviewResponseSerializer,
    CashoutCreateSerializer,
    CashoutConfirmSerializer,
    CashoutResponseSerializer,
    AdminDealershipListSerializer,
    AdminDealershipDetailSerializer,
    AdminDealershipGuaranteeSerializer,
    AdminGuaranteeVerifySerializer,
    AdminGuaranteeRejectSerializer,
    AdminDealershipApproveSerializer,
    AdminDealershipActionSerializer,
    AdminRechargeListSerializer,
    AdminCashoutListSerializer,
    AdminSettlementListSerializer,
    AdminSettlementGenerateSerializer,
    AdminSettlementCompleteSerializer,
    ClientLookupSerializer,
)
from .services import (
    calculate_total_guarantee,
    calculate_usable_credit_limit,
    calculate_net_exposure,
    calculate_available_recharge_capacity,
    calculate_recharge_fee,
    should_lock_dealership,
    create_recharge,
    create_cashout,
    confirm_cashout,
    verify_cashout_code,
    generate_settlement,
    complete_settlement,
    get_dealership_metrics,
    DealershipRechargeFeeConfig as FeeConfigModel,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# =====================================================================
# Dealership Summary & Profile
# =====================================================================

class DealershipMeView(GenericAPIView):
    """GET /api/dealership/me/ — current dealership profile."""
    permission_classes = [IsAuthenticated, IsDealership]

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, user=request.user)
        serializer = DealershipProfileSerializer(profile)
        return Response(serializer.data)


class DealershipSummaryView(GenericAPIView):
    """
    GET /api/dealership/me/summary/
    Financial summary for mobile app.
    """
    permission_classes = [IsAuthenticated, IsDealership]

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, user=request.user)

        total_guarantee = calculate_total_guarantee(profile)
        usable_limit = calculate_usable_credit_limit(profile)
        net_exp = calculate_net_exposure(profile)
        available = calculate_available_recharge_capacity(profile)

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        today_recharges = DealershipClientRecharge.objects.filter(
            dealership=profile,
            status=DealershipClientRecharge.Status.COMPLETED,
            completed_at__gte=today_start,
        ).aggregate(total=Sum('wallet_credit_amount'))['total'] or Decimal('0.00')

        today_cashouts = DealershipClientCashout.objects.filter(
            dealership=profile,
            status=DealershipClientCashout.Status.COMPLETED,
            completed_at__gte=today_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        pending_cashouts = DealershipClientCashout.objects.filter(
            dealership=profile,
            status__in=[
                DealershipClientCashout.Status.PENDING,
                DealershipClientCashout.Status.CODE_ISSUED,
            ],
        ).count()

        pending_settlements = DealershipSettlement.objects.filter(
            dealership=profile,
            status__in=[DealershipSettlement.Status.DRAFT, DealershipSettlement.Status.PENDING],
        ).count()

        data = {
            'dealership_id': str(profile.id),
            'business_name': profile.business_name,
            'status': profile.status,
            'active': profile.active,
            'financially_locked': profile.financially_locked,
            'recharge_enabled': profile.recharge_enabled,
            'cashout_enabled': profile.cashout_enabled,
            'total_verified_guarantee': str(total_guarantee),
            'usage_limit_percent': str(profile.usage_limit_percent),
            'usable_credit_limit': str(usable_limit),
            'net_exposure': str(net_exp),
            'available_recharge_capacity': str(available),
            'is_financially_locked': profile.financially_locked,
            'today_recharge_total': str(today_recharges),
            'today_cashout_total': str(today_cashouts),
            'pending_cashouts_count': pending_cashouts,
            'pending_settlements_count': pending_settlements,
            'currency': 'IQD',
        }
        serializer = DealershipSummarySerializer(data)
        return Response(serializer.data)


# =====================================================================
# Client Lookup
# =====================================================================

class ClientLookupView(GenericAPIView):
    """
    GET /api/dealership/clients/lookup/?q=phone_or_email
    Fast client lookup for dealership.
    """
    permission_classes = [IsAuthenticated, IsDealership]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query or len(query) < 3:
            return Response(
                {'error': 'Query must be at least 3 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clients = User.objects.filter(
            role='client',
        ).filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )[:20]

        results = []
        for c in clients:
            results.append({
                'id': str(c.id),
                'username': c.username,
                'full_name': c.get_full_name() or c.username,
                'phone': c.phone_number or '',
                'wallet_eligible': True,
            })

        return Response(results)


# =====================================================================
# Recharge Fee Config
# =====================================================================

class FeeConfigDetailView(GenericAPIView):
    """GET /api/dealership/fee-config/ — get active fee config."""
    permission_classes = [IsAuthenticated, IsDealership]

    def get(self, request, *args, **kwargs):
        config = DealershipRechargeFeeConfig.get_active_config()
        serializer = DealershipRechargeFeeConfigSerializer(config)
        return Response(serializer.data)


# =====================================================================
# Recharge Preview
# =====================================================================

class RechargePreviewView(GenericAPIView):
    """
    POST /api/dealership/recharges/preview/
    Preview fee calculation without executing.
    """
    permission_classes = [IsAuthenticated, IsDealership]

    def post(self, request, *args, **kwargs):
        serializer = RechargePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = get_object_or_404(DealershipProfile, user=request.user)
        fee_config = FeeConfigModel.get_active_config()
        fee_mode = serializer.validated_data['fee_mode']

        calc = calculate_recharge_fee(
            wallet_credit_amount=serializer.validated_data.get('wallet_credit_amount'),
            cash_received_amount=serializer.validated_data.get('cash_received_amount'),
            fee_config=fee_config,
            fee_mode=fee_mode,
        )

        available_before = calculate_available_recharge_capacity(profile)
        available_after = available_before - calc['dealership_exposure_amount']
        will_lock, _, _ = should_lock_dealership(profile, calc['dealership_exposure_amount'])

        response_data = {
            'currency': 'IQD',
            'fee_mode': calc['fee_mode'],
            'fee_percent': str(calc['fee_percent']),
            'cash_received_amount': str(calc['cash_received_amount']),
            'wallet_credit_amount': str(calc['wallet_credit_amount']),
            'dealership_fee_amount': str(calc['dealership_fee_amount']),
            'dealership_exposure_amount': str(calc['dealership_exposure_amount']),
            'available_recharge_capacity_before': str(available_before),
            'available_recharge_capacity_after': str(available_after),
            'will_lock_dealership': will_lock,
            'message': 'Preview calculated successfully.',
        }

        resp_serializer = RechargePreviewResponseSerializer(response_data)
        return Response(resp_serializer.data)


# =====================================================================
# Recharge Create
# =====================================================================

class RechargeCreateView(GenericAPIView):
    """
    POST /api/dealership/recharges/
    Create a recharge and credit client wallet.

    Supports Idempotency-Key header.
    """
    permission_classes = [IsAuthenticated, IsDealership]

    def post(self, request, *args, **kwargs):
        serializer = RechargeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = get_object_or_404(DealershipProfile, user=request.user)

        # Idempotency key from header or body
        idempotency_key = (
            request.META.get('HTTP_IDEMPOTENCY_KEY')
            or serializer.validated_data.get('idempotency_key')
            or None
        )

        client_id = serializer.validated_data['client_id']
        client = get_object_or_404(User, id=client_id)

        try:
            recharge, created = create_recharge(
                dealership=profile,
                client=client,
                fee_mode=serializer.validated_data['fee_mode'],
                wallet_credit_amount=serializer.validated_data.get('wallet_credit_amount'),
                cash_received_amount=serializer.validated_data.get('cash_received_amount'),
                created_by=request.user,
                idempotency_key=idempotency_key,
                proof_file=serializer.validated_data.get('proof_file'),
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp_serializer = RechargeResponseSerializer(recharge)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(resp_serializer.data, status=http_status)


# =====================================================================
# Recharge List
# =====================================================================

class RechargeListView(ListAPIView):
    """GET /api/dealership/recharges/ — list dealership recharges."""
    permission_classes = [IsAuthenticated, IsDealership]
    serializer_class = RechargeResponseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'client': ['exact'],
        'created_at': ['gte', 'lte'],
        'completed_at': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'completed_at', 'wallet_credit_amount']

    def get_queryset(self):
        profile = get_object_or_404(DealershipProfile, user=self.request.user)
        qs = DealershipClientRecharge.objects.filter(dealership=profile)
        # Amount filters
        min_amount = self.request.query_params.get('amount_min')
        max_amount = self.request.query_params.get('amount_max')
        if min_amount:
            qs = qs.filter(wallet_credit_amount__gte=Decimal(min_amount))
        if max_amount:
            qs = qs.filter(wallet_credit_amount__lte=Decimal(max_amount))
        return qs


class RechargeDetailView(RetrieveAPIView):
    """GET /api/dealership/recharges/<id>/"""
    permission_classes = [IsAuthenticated, IsDealership]
    serializer_class = RechargeResponseSerializer

    def get_object(self):
        profile = get_object_or_404(DealershipProfile, user=self.request.user)
        return get_object_or_404(
            DealershipClientRecharge,
            id=self.kwargs['recharge_id'],
            dealership=profile,
        )


# =====================================================================
# Cash-out Preview
# =====================================================================

class CashoutPreviewView(GenericAPIView):
    """
    POST /api/dealership/cashouts/preview/
    Preview cash-out before creating.
    """
    permission_classes = [IsAuthenticated, IsClientUser]

    def post(self, request, *args, **kwargs):
        serializer = CashoutPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dealership = get_object_or_404(
            DealershipProfile,
            id=serializer.validated_data['dealership_id'],
        )
        amount = serializer.validated_data['amount']

        from wallet.models import Wallet
        wallet = Wallet.objects.filter(user=request.user).first()
        balance_before = wallet.balance if wallet else Decimal('0.00')
        balance_after = balance_before - amount if balance_before >= amount else balance_before

        response_data = {
            'currency': 'IQD',
            'amount': str(amount),
            'client_wallet_balance_before': str(balance_before),
            'client_wallet_balance_after': str(balance_after),
            'dealership_status': dealership.status,
            'cashout_enabled': dealership.cashout_enabled,
            'requires_admin_approval': False,
            'code_will_expire_in_seconds': 600,
            'message': 'Preview calculated.',
        }

        resp_serializer = CashoutPreviewResponseSerializer(response_data)
        return Response(resp_serializer.data)


# =====================================================================
# Cash-out Create
# =====================================================================

class CashoutCreateView(GenericAPIView):
    """
    POST /api/dealership/cashouts/
    Client initiates a cash-out request.
    """
    permission_classes = [IsAuthenticated, IsClientUser]

    def post(self, request, *args, **kwargs):
        serializer = CashoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dealership = get_object_or_404(
            DealershipProfile,
            id=serializer.validated_data['dealership_id'],
        )

        idempotency_key = (
            request.META.get('HTTP_IDEMPOTENCY_KEY')
            or serializer.validated_data.get('idempotency_key')
            or None
        )

        try:
            cashout, created = create_cashout(
                dealership=dealership,
                client=request.user,
                amount=serializer.validated_data['amount'],
                idempotency_key=idempotency_key,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp_serializer = CashoutResponseSerializer(cashout)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(resp_serializer.data, status=http_status)


# =====================================================================
# Cash-out Confirmation
# =====================================================================

class CashoutConfirmView(GenericAPIView):
    """
    POST /api/dealership/cashouts/<cashout_id>/confirm-code/
    Dealership confirms cash-out with client's code.
    """
    permission_classes = [IsAuthenticated, IsDealership]

    def post(self, request, *args, **kwargs):
        serializer = CashoutConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = get_object_or_404(DealershipProfile, user=request.user)
        cashout = get_object_or_404(
            DealershipClientCashout,
            id=self.kwargs['cashout_id'],
            dealership=profile,
        )

        confirmation_code = serializer.validated_data['confirmation_code']

        # Verify code
        try:
            verify_cashout_code(cashout, confirmation_code, request.user)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Confirm cash-out
        try:
            cashout = confirm_cashout(cashout, request.user)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp_serializer = CashoutResponseSerializer(cashout)
        return Response(resp_serializer.data)


# =====================================================================
# Cash-out List
# =====================================================================

class CashoutListView(ListAPIView):
    """GET /api/dealership/cashouts/ — list cash-outs."""
    permission_classes = [IsAuthenticated]
    serializer_class = CashoutResponseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'client': ['exact'],
        'created_at': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'completed_at', 'amount']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'dealership':
            profile = get_object_or_404(DealershipProfile, user=user)
            qs = DealershipClientCashout.objects.filter(dealership=profile)
        elif user.role == 'client':
            qs = DealershipClientCashout.objects.filter(client=user)
        else:
            qs = DealershipClientCashout.objects.none()

        min_amount = self.request.query_params.get('amount_min')
        max_amount = self.request.query_params.get('amount_max')
        if min_amount:
            qs = qs.filter(amount__gte=Decimal(min_amount))
        if max_amount:
            qs = qs.filter(amount__lte=Decimal(max_amount))
        return qs


class CashoutDetailView(RetrieveAPIView):
    """GET /api/dealership/cashouts/<id>/"""
    permission_classes = [IsAuthenticated]
    serializer_class = CashoutResponseSerializer

    def get_object(self):
        user = self.request.user
        qs = DealershipClientCashout.objects.all()
        if user.role == 'dealership':
            profile = get_object_or_404(DealershipProfile, user=user)
            qs = qs.filter(dealership=profile)
        elif user.role == 'client':
            qs = qs.filter(client=user)
        return get_object_or_404(qs, id=self.kwargs['cashout_id'])


# =====================================================================
# Settlement List
# =====================================================================

class SettlementListView(ListAPIView):
    """GET /api/dealership/settlements/ — list dealership settlements."""
    permission_classes = [IsAuthenticated, IsDealership]
    serializer_class = AdminSettlementListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'period_start': ['gte', 'lte'],
        'period_end': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'period_start', 'period_end']

    def get_queryset(self):
        profile = get_object_or_404(DealershipProfile, user=self.request.user)
        return DealershipSettlement.objects.filter(dealership=profile)


# =====================================================================
# Admin Endpoints
# =====================================================================

class AdminDealershipListView(ListAPIView):
    """GET /api/admin/dealerships/ — list all dealerships."""
    permission_classes = [IsAuthenticated, IsAccountManagerOrFinance, IsContentModeratorDenied]
    serializer_class = AdminDealershipListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['business_name', 'owner_name', 'user__username', 'user__email']
    ordering_fields = ['created_at', 'business_name', 'status']
    filterset_fields = {
        'status': ['exact'],
        'active': ['exact'],
        'financially_locked': ['exact'],
        'suspended': ['exact'],
        'blocked': ['exact'],
        'governorate': ['exact'],
    }

    def get_queryset(self):
        return DealershipProfile.objects.all().select_related('user').order_by('-created_at')


class AdminDealershipDetailView(RetrieveAPIView):
    """GET /api/admin/dealerships/<id>/ — dealership detail."""
    permission_classes = [IsAuthenticated, IsAccountManagerOrFinance, IsContentModeratorDenied]
    serializer_class = AdminDealershipDetailSerializer
    queryset = DealershipProfile.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'dealership_id'


class AdminDealershipApproveView(GenericAPIView):
    """POST /api/admin/dealerships/<id>/approve/"""
    permission_classes = [IsAuthenticated, IsAccountManagerOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])
        serializer = AdminDealershipApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile.status = DealershipProfile.Status.ACTIVE
        profile.active = True
        profile.suspended = False
        profile.blocked = False
        profile.approved_by = request.user
        profile.approved_at = timezone.now()
        profile.save(update_fields=[
            'status', 'active', 'suspended', 'blocked',
            'approved_by', 'approved_at', 'updated_at',
        ])

        # Activity log
        from notification.services import create_activity
        create_activity(
            verb='dealership_approved',
            actor=request.user,
            target_type='dealership_profile',
            target_id=profile.id,
            target_repr=f"Dealership {profile.business_name} approved",
            audience='admin',
        )

        return Response(AdminDealershipDetailSerializer(profile).data)


class AdminDealershipSuspendView(GenericAPIView):
    """POST /api/admin/dealerships/<id>/suspend/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])
        serializer = AdminDealershipActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile.suspended = True
        profile.save(update_fields=['suspended', 'updated_at'])

        from notification.services import create_activity
        create_activity(
            verb='dealership_suspended',
            actor=request.user,
            target_type='dealership_profile',
            target_id=profile.id,
            target_repr=f"Dealership {profile.business_name} suspended",
            audience='admin',
            metadata={'reason': serializer.validated_data.get('reason', '')},
        )

        return Response(AdminDealershipDetailSerializer(profile).data)


class AdminDealershipBlockView(GenericAPIView):
    """POST /api/admin/dealerships/<id>/block/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])
        serializer = AdminDealershipActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile.blocked = True
        profile.active = False
        profile.save(update_fields=['blocked', 'active', 'updated_at'])

        from notification.services import create_activity
        create_activity(
            verb='dealership_blocked',
            actor=request.user,
            target_type='dealership_profile',
            target_id=profile.id,
            target_repr=f"Dealership {profile.business_name} blocked",
            audience='admin',
            metadata={'reason': serializer.validated_data.get('reason', '')},
        )

        return Response(AdminDealershipDetailSerializer(profile).data)


class AdminDealershipUnlockView(GenericAPIView):
    """POST /api/admin/dealerships/<id>/unlock/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])

        profile.financially_locked = False
        profile.save(update_fields=['financially_locked', 'updated_at'])

        from notification.services import create_activity
        create_activity(
            verb='dealership_unlocked',
            actor=request.user,
            target_type='dealership_profile',
            target_id=profile.id,
            target_repr=f"Dealership {profile.business_name} unlocked",
            audience='admin',
        )

        return Response(AdminDealershipDetailSerializer(profile).data)


# =====================================================================
# Admin Guarantees
# =====================================================================

class AdminGuaranteeListView(ListAPIView):
    """GET /api/admin/dealerships/<id>/guarantees/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]
    serializer_class = AdminDealershipGuaranteeSerializer

    def get_queryset(self):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])
        return DealershipGuarantee.objects.filter(dealership=profile)


class AdminGuaranteeCreateView(CreateAPIView):
    """POST /api/admin/dealerships/<id>/guarantees/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]
    serializer_class = AdminDealershipGuaranteeSerializer

    def perform_create(self, serializer):
        profile = get_object_or_404(DealershipProfile, id=self.kwargs['dealership_id'])
        serializer.save(dealership=profile)


class AdminGuaranteeVerifyView(GenericAPIView):
    """POST /api/admin/dealership-guarantees/<id>/verify/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        guarantee = get_object_or_404(
            DealershipGuarantee, id=self.kwargs['guarantee_id'],
        )
        serializer = AdminGuaranteeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guarantee.status = DealershipGuarantee.Status.VERIFIED
        guarantee.verified_by = request.user
        guarantee.verified_at = timezone.now()
        if serializer.validated_data.get('notes'):
            guarantee.notes = serializer.validated_data['notes']
        guarantee.save(update_fields=[
            'status', 'verified_by', 'verified_at', 'notes', 'updated_at',
        ])

        # Create ledger entry
        DealershipCreditLedger.objects.create(
            dealership=guarantee.dealership,
            transaction_type=DealershipCreditLedger.TransactionType.GUARANTEE_ADDED,
            amount=guarantee.total_guarantee_amount,
            balance_after=calculate_total_guarantee(guarantee.dealership),
            reference_type='dealership_guarantee',
            reference_id=guarantee.id,
            created_by=request.user,
            notes=f"Guarantee verified: {guarantee.total_guarantee_amount} IQD",
        )

        from notification.services import create_activity
        create_activity(
            verb='guarantee_verified',
            actor=request.user,
            target_type='dealership_guarantee',
            target_id=guarantee.id,
            target_repr=f"Guarantee {guarantee.total_guarantee_amount} IQD verified",
            audience='admin',
        )

        return Response(AdminDealershipGuaranteeSerializer(guarantee).data)


class AdminGuaranteeRejectView(GenericAPIView):
    """POST /api/admin/dealership-guarantees/<id>/reject/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        guarantee = get_object_or_404(
            DealershipGuarantee, id=self.kwargs['guarantee_id'],
        )
        serializer = AdminGuaranteeRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guarantee.status = DealershipGuarantee.Status.REJECTED
        if serializer.validated_data.get('notes'):
            guarantee.notes = serializer.validated_data['notes']
        guarantee.save(update_fields=['status', 'notes', 'updated_at'])

        from notification.services import create_activity
        create_activity(
            verb='guarantee_rejected',
            actor=request.user,
            target_type='dealership_guarantee',
            target_id=guarantee.id,
            target_repr=f"Guarantee {guarantee.total_guarantee_amount} IQD rejected",
            audience='admin',
        )

        return Response(AdminDealershipGuaranteeSerializer(guarantee).data)


# =====================================================================
# Admin Recharge/Cashout/Settlement List Views
# =====================================================================

class AdminRechargeListView(ListAPIView):
    """GET /api/admin/dealership-recharges/"""
    permission_classes = [IsAuthenticated, IsAccountManagerOrFinance, IsContentModeratorDenied]
    serializer_class = AdminRechargeListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['dealership__business_name', 'client__username', 'receipt_number']
    filterset_fields = {
        'status': ['exact'],
        'dealership': ['exact'],
        'client': ['exact'],
        'created_at': ['gte', 'lte'],
        'completed_at': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'completed_at', 'wallet_credit_amount']
    queryset = DealershipClientRecharge.objects.all().select_related(
        'dealership', 'client'
    ).order_by('-created_at')


class AdminCashoutListView(ListAPIView):
    """GET /api/admin/dealership-cashouts/"""
    permission_classes = [IsAuthenticated, IsAccountManagerOrFinance, IsContentModeratorDenied]
    serializer_class = AdminCashoutListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['dealership__business_name', 'client__username']
    filterset_fields = {
        'status': ['exact'],
        'dealership': ['exact'],
        'client': ['exact'],
        'created_at': ['gte', 'lte'],
        'completed_at': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'completed_at', 'amount']
    queryset = DealershipClientCashout.objects.all().select_related(
        'dealership', 'client'
    ).order_by('-created_at')


class AdminSettlementListView(ListAPIView):
    """GET /api/admin/dealership-settlements/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]
    serializer_class = AdminSettlementListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'dealership': ['exact'],
        'period_start': ['gte', 'lte'],
        'period_end': ['gte', 'lte'],
    }
    ordering_fields = ['created_at', 'period_start', 'period_end']
    queryset = DealershipSettlement.objects.all().select_related('dealership').order_by('-created_at')


class AdminSettlementGenerateView(GenericAPIView):
    """POST /api/admin/dealership-settlements/generate/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        serializer = AdminSettlementGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dealership = get_object_or_404(
            DealershipProfile,
            id=serializer.validated_data['dealership_id'],
        )

        try:
            settlement = generate_settlement(
                dealership=dealership,
                period_start=serializer.validated_data['period_start'],
                period_end=serializer.validated_data['period_end'],
                created_by=request.user,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            AdminSettlementListSerializer(settlement).data,
            status=status.HTTP_201_CREATED,
        )


class AdminSettlementCompleteView(GenericAPIView):
    """POST /api/admin/dealership-settlements/<id>/complete/"""
    permission_classes = [IsAuthenticated, IsSystemAdminOrFinance, IsContentModeratorDenied]

    def post(self, request, *args, **kwargs):
        settlement = get_object_or_404(
            DealershipSettlement, id=self.kwargs['settlement_id'],
        )
        serializer = AdminSettlementCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            settlement = complete_settlement(settlement, request.user)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(AdminSettlementListSerializer(settlement).data)
