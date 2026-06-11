from decimal import Decimal
from rest_framework import serializers
from .models import (
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
        read_only_fields = ("id", "created_at", "updated_at", "reviewed_at", "paid_at", "admin_note")


class WithdrawalRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    requested_method = serializers.CharField(required=False, allow_blank=True, max_length=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
