"""
Dealership serializers — profiles, recharges, cashouts, admin, settlements.
"""

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipCreditLedger,
    DealershipSettlement,
)
from .services import (
    calculate_total_guarantee,
    calculate_usable_credit_limit,
    calculate_net_exposure,
    calculate_available_recharge_capacity,
    calculate_recharge_fee,
    DealershipRechargeFeeConfig as FeeConfigModel,
)

User = get_user_model()


# =====================================================================
# Dealership Profile
# =====================================================================

class DealershipProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = DealershipProfile
        fields = [
            'id', 'user', 'username', 'email',
            'business_name', 'owner_name', 'phone',
            'governorate', 'address',
            'status', 'active', 'financially_locked',
            'suspended', 'blocked',
            'usage_limit_percent',
            'min_required_guarantee', 'max_allowed_guarantee',
            'single_cashout_limit', 'daily_cashout_limit',
            'monthly_cashout_limit',
            'cashout_enabled', 'recharge_enabled',
            'approved_by', 'approved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'status', 'active', 'financially_locked',
            'suspended', 'blocked',
            'approved_by', 'approved_at',
            'created_at', 'updated_at',
        ]


class DealershipSummarySerializer(serializers.Serializer):
    """Dealership financial summary for mobile use."""
    dealership_id = serializers.CharField(read_only=True)
    business_name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
    financially_locked = serializers.BooleanField(read_only=True)
    recharge_enabled = serializers.BooleanField(read_only=True)
    cashout_enabled = serializers.BooleanField(read_only=True)
    total_verified_guarantee = serializers.CharField(read_only=True)
    usage_limit_percent = serializers.CharField(read_only=True)
    usable_credit_limit = serializers.CharField(read_only=True)
    net_exposure = serializers.CharField(read_only=True)
    available_recharge_capacity = serializers.CharField(read_only=True)
    is_financially_locked = serializers.BooleanField(read_only=True)
    today_recharge_total = serializers.CharField(read_only=True)
    today_cashout_total = serializers.CharField(read_only=True)
    pending_cashouts_count = serializers.IntegerField(read_only=True)
    pending_settlements_count = serializers.IntegerField(read_only=True)
    currency = serializers.CharField(read_only=True, default='IQD')


# =====================================================================
# Fee Config
# =====================================================================

class DealershipRechargeFeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealershipRechargeFeeConfig
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


# =====================================================================
# Recharge Preview
# =====================================================================

class RechargePreviewSerializer(serializers.Serializer):
    """Preview recharge fee calculation."""
    client_id = serializers.UUIDField()
    fee_mode = serializers.ChoiceField(
        choices=[FeeConfigModel.FeeMode.ADDED_ON_TOP, FeeConfigModel.FeeMode.DEDUCTED_FROM_DEPOSIT],
    )
    wallet_credit_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False,
    )
    cash_received_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False,
    )

    def validate(self, data):
        fee_mode = data['fee_mode']
        if fee_mode == FeeConfigModel.FeeMode.ADDED_ON_TOP:
            if 'wallet_credit_amount' not in data or data.get('wallet_credit_amount') is None:
                raise serializers.ValidationError(
                    "wallet_credit_amount is required for added_on_top mode."
                )
        elif fee_mode == FeeConfigModel.FeeMode.DEDUCTED_FROM_DEPOSIT:
            if 'cash_received_amount' not in data or data.get('cash_received_amount') is None:
                raise serializers.ValidationError(
                    "cash_received_amount is required for deducted_from_deposit mode."
                )
        return data


class RechargePreviewResponseSerializer(serializers.Serializer):
    currency = serializers.CharField(default='IQD')
    fee_mode = serializers.CharField()
    fee_percent = serializers.CharField()
    cash_received_amount = serializers.CharField()
    wallet_credit_amount = serializers.CharField()
    dealership_fee_amount = serializers.CharField()
    dealership_exposure_amount = serializers.CharField()
    available_recharge_capacity_before = serializers.CharField()
    available_recharge_capacity_after = serializers.CharField()
    will_lock_dealership = serializers.BooleanField()
    message = serializers.CharField()


# =====================================================================
# Recharge Create
# =====================================================================

class RechargeCreateSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    fee_mode = serializers.ChoiceField(
        choices=[FeeConfigModel.FeeMode.ADDED_ON_TOP, FeeConfigModel.FeeMode.DEDUCTED_FROM_DEPOSIT],
    )
    wallet_credit_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False,
    )
    cash_received_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False,
    )
    proof_file = serializers.FileField(required=False)
    # Optionally accept client-submitted idempotency key
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        fee_mode = data['fee_mode']
        if fee_mode == FeeConfigModel.FeeMode.ADDED_ON_TOP:
            if data.get('wallet_credit_amount') is None:
                raise serializers.ValidationError(
                    "wallet_credit_amount is required for added_on_top mode."
                )
        elif fee_mode == FeeConfigModel.FeeMode.DEDUCTED_FROM_DEPOSIT:
            if data.get('cash_received_amount') is None:
                raise serializers.ValidationError(
                    "cash_received_amount is required for deducted_from_deposit mode."
                )
        return data


class RechargeResponseSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True)
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    currency = serializers.CharField(read_only=True, default='IQD')

    class Meta:
        model = DealershipClientRecharge
        fields = [
            'id', 'dealership', 'dealership_name',
            'client', 'client_name', 'client_username',
            'fee_mode', 'fee_percent',
            'cash_received_amount', 'wallet_credit_amount',
            'dealership_fee_amount', 'dealership_exposure_amount',
            'status', 'receipt_number',
            'wallet_transaction',
            'completed_at', 'created_at',
            'currency',
        ]
        read_only_fields = fields


# =====================================================================
# Cash-out
# =====================================================================

class CashoutPreviewSerializer(serializers.Serializer):
    dealership_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class CashoutPreviewResponseSerializer(serializers.Serializer):
    currency = serializers.CharField(default='IQD')
    amount = serializers.CharField()
    client_wallet_balance_before = serializers.CharField()
    client_wallet_balance_after = serializers.CharField()
    dealership_status = serializers.CharField()
    cashout_enabled = serializers.BooleanField()
    requires_admin_approval = serializers.BooleanField(default=False)
    code_will_expire_in_seconds = serializers.IntegerField()
    message = serializers.CharField()


class CashoutCreateSerializer(serializers.Serializer):
    dealership_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be positive.")
        return value


class CashoutConfirmSerializer(serializers.Serializer):
    confirmation_code = serializers.CharField(max_length=10, min_length=4)


class CashoutResponseSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True)
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    currency = serializers.CharField(read_only=True, default='IQD')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DealershipClientCashout
        fields = [
            'id', 'dealership', 'dealership_name',
            'client', 'client_name', 'client_username',
            'amount', 'status', 'status_display',
            'code_expires_at',
            'confirmed_at',
            'wallet_transaction',
            'created_at', 'completed_at',
            'currency',
        ]
        read_only_fields = fields


# =====================================================================
# Admin Serializers
# =====================================================================

class AdminDealershipListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = DealershipProfile
        fields = [
            'id', 'username', 'email', 'phone_number',
            'business_name', 'owner_name', 'governorate',
            'status', 'active', 'financially_locked',
            'suspended', 'blocked',
            'recharge_enabled', 'cashout_enabled',
            'approved_by', 'approved_at',
            'created_at', 'updated_at',
        ]


class AdminDealershipDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    # Computed financial fields
    total_verified_guarantee = serializers.SerializerMethodField()
    usable_credit_limit = serializers.SerializerMethodField()
    net_exposure = serializers.SerializerMethodField()
    available_recharge_capacity = serializers.SerializerMethodField()

    class Meta:
        model = DealershipProfile
        fields = [
            'id', 'user', 'username', 'email', 'phone_number',
            'business_name', 'owner_name', 'phone',
            'governorate', 'address',
            'status', 'active', 'financially_locked',
            'suspended', 'blocked',
            'usage_limit_percent',
            'min_required_guarantee', 'max_allowed_guarantee',
            'single_cashout_limit', 'daily_cashout_limit',
            'monthly_cashout_limit',
            'cashout_enabled', 'recharge_enabled',
            'approved_by', 'approved_at',
            'total_verified_guarantee',
            'usable_credit_limit',
            'net_exposure',
            'available_recharge_capacity',
            'created_at', 'updated_at',
        ]
        read_only_fields = [f for f in fields if f not in [
            'usage_limit_percent',
            'min_required_guarantee', 'max_allowed_guarantee',
            'single_cashout_limit', 'daily_cashout_limit',
            'monthly_cashout_limit',
            'cashout_enabled', 'recharge_enabled',
        ]]

    def get_total_verified_guarantee(self, obj):
        from .services import calculate_total_guarantee
        return str(calculate_total_guarantee(obj))

    def get_usable_credit_limit(self, obj):
        from .services import calculate_usable_credit_limit
        return str(calculate_usable_credit_limit(obj))

    def get_net_exposure(self, obj):
        from .services import calculate_net_exposure
        return str(calculate_net_exposure(obj))

    def get_available_recharge_capacity(self, obj):
        from .services import calculate_available_recharge_capacity
        return str(calculate_available_recharge_capacity(obj))


class AdminDealershipGuaranteeSerializer(serializers.ModelSerializer):
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    verified_by_name = serializers.CharField(
        source='verified_by.username', read_only=True, default=None,
    )

    class Meta:
        model = DealershipGuarantee
        fields = '__all__'
        read_only_fields = [
            'id', 'dealership', 'total_guarantee_amount',
            'status', 'verified_by', 'verified_at',
            'created_at', 'updated_at',
        ]


class AdminGuaranteeVerifySerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class AdminGuaranteeRejectSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class AdminDealershipApproveSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class AdminDealershipActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class AdminRechargeListSerializer(serializers.ModelSerializer):
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True)

    class Meta:
        model = DealershipClientRecharge
        fields = '__all__'


class AdminCashoutListSerializer(serializers.ModelSerializer):
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_username = serializers.CharField(source='client.username', read_only=True)

    class Meta:
        model = DealershipClientCashout
        fields = '__all__'


class AdminSettlementListSerializer(serializers.ModelSerializer):
    dealership_name = serializers.CharField(source='dealership.business_name', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DealershipSettlement
        fields = '__all__'


class AdminSettlementGenerateSerializer(serializers.Serializer):
    dealership_id = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class AdminSettlementCompleteSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


# =====================================================================
# Client Lookup
# =====================================================================

class ClientLookupSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    wallet_eligible = serializers.BooleanField(read_only=True)
