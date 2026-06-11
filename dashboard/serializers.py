"""Serializers for admin dashboard APIs."""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract, ContractStage, TimeExtensionRequest
from wallet.models import (
    PlatformEarning, PaymentIntent, WithdrawalRequest,
    ContractPaymentBreakdown, WalletTransaction,
)
from ratereview.models import Review, ReviewReport
from notification.models import ActivityLog

User = get_user_model()


# ------------------------------------------------------------------
# Dashboard summary (no model serializer needed — built manually)
# ------------------------------------------------------------------

class DashboardSummarySerializer(serializers.Serializer):
    users = serializers.DictField()
    technicians = serializers.DictField()
    contracts = serializers.DictField()
    finance = serializers.DictField()
    reviews = serializers.DictField()
    notifications = serializers.DictField()


# ------------------------------------------------------------------
# User management serializers
# ------------------------------------------------------------------

class AdminUserListSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'first_name', 'last_name', 'phone_number',
            'governorate', 'is_active', 'date_joined',
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'first_name', 'last_name', 'phone_number',
            'governorate', 'address', 'gender', 'date_of_birth',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_superuser', 'date_joined', 'last_login']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active', 'first_name', 'last_name', 'phone_number', 'governorate', 'address']
        extra_kwargs = {f: {'required': False} for f in fields}


# ------------------------------------------------------------------
# Technician admin serializers
# ------------------------------------------------------------------

class AdminTechnicianListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'username', 'email', 'phone_number',
            'job_title', 'rate', 'approved', 'is_available',
            'years_of_expertise', 'governorate', 'is_complete',
            'created_at',
        ]

    governorate = serializers.CharField(source='user.governorate', read_only=True)


class AdminTechnicianDetailSerializer(serializers.ModelSerializer):
    user = AdminUserDetailSerializer(read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = '__all__'


class TechnicianRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


# ------------------------------------------------------------------
# Contract admin serializers
# ------------------------------------------------------------------

class AdminContractListSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_reference', 'status',
            'client_name', 'technician_name',
            'agreed_amount', 'stage_number',
            'client_accepted', 'technician_accepted',
            'created_at',
        ]

    def get_client_name(self, obj):
        return str(obj.client) if obj.client else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None


class AdminContractDetailSerializer(serializers.ModelSerializer):
    stages = serializers.SerializerMethodField()
    payment_breakdown = serializers.SerializerMethodField()
    payment_intents = serializers.SerializerMethodField()
    platform_earnings = serializers.SerializerMethodField()
    extension_requests = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = '__all__'

    def get_stages(self, obj):
        stages = obj.stages.all().order_by('stage_number')
        return [
            {
                'id': str(s.id), 'stage_number': s.stage_number,
                'amount': str(s.amount), 'is_approved_by_client': s.is_approved_by_client,
                'completed_at': s.completed_at, 'created_at': s.created_at,
            }
            for s in stages
        ]

    def get_payment_breakdown(self, obj):
        if hasattr(obj, 'payment_breakdown'):
            pb = obj.payment_breakdown
            return {
                'id': str(pb.id), 'contract_amount': str(pb.contract_amount),
                'technician_commission_amount': str(pb.technician_commission_amount),
                'client_service_fee_amount': str(pb.client_service_fee_amount),
                'total_platform_fee': str(pb.total_platform_fee),
                'client_total_amount': str(pb.client_total_amount),
                'technician_net_amount': str(pb.technician_net_amount),
            }
        return None

    def get_payment_intents(self, obj):
        return list(obj.payment_intents.values('id', 'amount', 'status', 'purpose', 'created_at'))

    def get_platform_earnings(self, obj):
        return list(obj.platform_earnings.values('id', 'earning_type', 'amount', 'status'))

    def get_extension_requests(self, obj):
        return list(obj.extension_requests.values('id', 'requested_days', 'status', 'reason', 'created_at'))


class AdminContractForceCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


# ------------------------------------------------------------------
# Review admin serializers
# ------------------------------------------------------------------

class AdminReviewListSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'reviewer_name', 'technician_name',
            'rating', 'is_public', 'is_verified',
            'helpful_count', 'reported_count', 'flagged_at',
            'created_at',
        ]

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() or obj.reviewer.username if obj.reviewer else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None


class AdminReviewDetailSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = '__all__'

    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() or obj.reviewer.username if obj.reviewer else None

    def get_technician_name(self, obj):
        return str(obj.technician) if obj.technician else None

    def get_reports(self, obj):
        return list(obj.reports.values('reporter', 'reason', 'comment', 'created_at'))


# ------------------------------------------------------------------
# Finance serializers
# ------------------------------------------------------------------

class AdminPlatformEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformEarning
        fields = '__all__'


class AdminPaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = '__all__'


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = '__all__'


class AdminWithdrawalActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)


class AdminPaymentIntentMarkPaidSerializer(serializers.Serializer):
    pass


# ------------------------------------------------------------------
# Activity serializers
# ------------------------------------------------------------------

class AdminActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = '__all__'

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None
