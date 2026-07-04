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
    profiles = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    financial_summary = serializers.SerializerMethodField()
    recent_audit_events = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'first_name', 'last_name', 'phone_number',
            'governorate', 'address', 'gender', 'date_of_birth',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'profiles', 'activity', 'financial_summary', 'recent_audit_events',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_superuser', 'date_joined', 'last_login']

    def get_profiles(self, obj):
        client = getattr(obj, 'client_profile', None)
        technician = getattr(obj, 'technician_profile', None)
        return {
            'client': {
                'exists': bool(client),
                'is_complete': bool(getattr(client, 'is_complete', False)) if client else False,
            },
            'technician': {
                'exists': bool(technician),
                'is_complete': bool(getattr(technician, 'is_complete', False)) if technician else False,
                'approved': bool(getattr(technician, 'approved', False)) if technician else False,
                'job_title': getattr(technician, 'job_title', '') if technician else '',
                'missing_fields': technician.get_incomplete_fields() if technician else [],
            },
        }

    def get_activity(self, obj):
        data = {
            'requests': 0,
            'offers': 0,
            'contracts': 0,
            'reviews': 0,
            'notifications': 0,
            'audit_events': 0,
        }
        client = getattr(obj, 'client_profile', None)
        technician = getattr(obj, 'technician_profile', None)
        try:
            from servicerequest.models import ServiceRequest
            if client:
                data['requests'] += ServiceRequest.objects.filter(client=client).count()
            if technician:
                data['requests'] += ServiceRequest.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            from contract.offer_models import Offer
            if technician:
                data['offers'] += Offer.objects.filter(technician=technician).count()
            if client:
                data['offers'] += Offer.objects.filter(service_request__client=client).count()
        except Exception:
            pass
        try:
            if client:
                data['contracts'] += Contract.objects.filter(client=client).count()
            if technician:
                data['contracts'] += Contract.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            data['reviews'] = Review.objects.filter(reviewer=obj).count()
            if technician:
                data['reviews'] += Review.objects.filter(technician=technician).count()
        except Exception:
            pass
        try:
            from notification.models import Notification
            data['notifications'] = Notification.objects.filter(user=obj).count()
            data['audit_events'] = ActivityLog.objects.filter(actor=obj).count()
        except Exception:
            pass
        return data

    def get_financial_summary(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return {
            'wallet_exists': bool(wallet),
            'wallet_balance': str(wallet.balance) if wallet else None,
            'payment_intents': PaymentIntent.objects.filter(user=obj).count(),
            'withdrawals': WithdrawalRequest.objects.filter(user=obj).count(),
        }

    def get_recent_audit_events(self, obj):
        return [
            {
                'id': str(event.id),
                'verb': event.verb,
                'target_type': event.target_type,
                'target_id': str(event.target_id),
                'created_at': event.created_at,
            }
            for event in ActivityLog.objects.filter(actor=obj).order_by('-created_at')[:5]
        ]


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
    incomplete_fields = serializers.SerializerMethodField()
    has_documents = serializers.SerializerMethodField()
    has_github = serializers.SerializerMethodField()
    has_linkedin = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'username', 'email', 'phone_number',
            'job_title', 'rate', 'approved', 'is_available',
            'years_of_expertise', 'governorate', 'is_complete',
            'incomplete_fields', 'has_documents', 'has_github', 'has_linkedin',
            'created_at',
        ]

    governorate = serializers.CharField(source='user.governorate', read_only=True)

    def get_incomplete_fields(self, obj):
        return obj.get_incomplete_fields()

    def get_has_documents(self, obj):
        return bool(obj.identification_documents)

    def get_has_github(self, obj):
        return bool(obj.github)

    def get_has_linkedin(self, obj):
        return bool(obj.linkedin)


class AdminTechnicianDetailSerializer(serializers.ModelSerializer):
    user = AdminUserDetailSerializer(read_only=True)
    incomplete_fields = serializers.SerializerMethodField()
    approval_requirements = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianProfile
        fields = '__all__'

    def get_incomplete_fields(self, obj):
        return obj.get_incomplete_fields()

    def get_approval_requirements(self, obj):
        missing = obj.get_incomplete_fields()
        return {
            'can_approve': obj.user.is_active and not missing,
            'missing': missing + ([] if obj.user.is_active else ['active_account']),
        }


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
