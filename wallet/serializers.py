from decimal import Decimal
from rest_framework import serializers
from .models import (
    ContractSettlement,
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PlatformEarning,
    PaymentIntent,
    WithdrawalRequest,
    Wallet,
    WalletTransaction,
)


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("user_id", "balance", "transaction_id", "updated_at")


class WalletBalanceSerializer(serializers.Serializer):
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    reserved_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = "__all__"


class PlatformFeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformFeeConfig
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ContractPaymentBreakdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractPaymentBreakdown
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PlatformEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformEarning
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "paid_at")


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = "__all__"
        read_only_fields = (
            "id", "created_at", "updated_at", "reviewed_at",
            "paid_at", "admin_note", "failure_code", "failure_message",
        )


class WithdrawalRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    requested_method = serializers.CharField(required=False, allow_blank=True, max_length=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class SettlementEligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True)


class ContractSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractSettlement
        fields = "__all__"
        read_only_fields = (
            "id", "created_at", "updated_at", "initiated_at",
            "completed_at", "failed_at", "status",
        )


class SettlementCreateSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(required=False, allow_null=True, max_length=64)


class AdminWithdrawalActionSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    simulate_failure = serializers.BooleanField(required=False, default=False)
