from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from tiqani_v3.file_validators import validate_wallet_recharge_receipt_file
from .models import (
    ContractSettlement,
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PlatformEarning,
    PaymentIntent,
    WalletRechargeRequest,
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


class WalletRechargeRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    receipt_file = serializers.FileField(required=True)

    def validate_receipt_file(self, value):
        try:
            validate_wallet_recharge_receipt_file(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class WalletRechargeRequestReviewSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class WalletRechargeRequestRejectSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=True, allow_blank=False, max_length=2000)


class WalletRechargeRequestSerializer(serializers.ModelSerializer):
    receipt_download_url = serializers.SerializerMethodField()
    approved_transaction_id = serializers.UUIDField(source="approved_transaction.id", read_only=True)

    class Meta:
        model = WalletRechargeRequest
        fields = [
            "id",
            "amount",
            "currency",
            "note",
            "status",
            "receipt_download_url",
            "original_filename",
            "file_size",
            "mime_type",
            "reviewed_at",
            "review_note",
            "approved_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_receipt_download_url(self, obj):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if not obj.receipt_file or not actor or not actor.is_authenticated:
            return None
        if actor.is_staff or actor == obj.user:
            path = f"/api/wallet/recharge-requests/{obj.id}/receipt/"
            return request.build_absolute_uri(path) if request else path
        return None


class AdminWalletRechargeRequestSerializer(WalletRechargeRequestSerializer):
    user = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta(WalletRechargeRequestSerializer.Meta):
        fields = [
            "id",
            "user",
            "amount",
            "currency",
            "note",
            "status",
            "receipt_download_url",
            "original_filename",
            "file_size",
            "mime_type",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "approved_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user(self, obj):
        return {
            "id": str(obj.user_id),
            "username": obj.user.username,
            "email": obj.user.email,
            "name": obj.user.get_full_name() or obj.user.username,
        }

    def get_reviewed_by(self, obj):
        if not obj.reviewed_by_id:
            return None
        return {
            "id": str(obj.reviewed_by_id),
            "username": obj.reviewed_by.username,
            "email": obj.reviewed_by.email,
            "name": obj.reviewed_by.get_full_name() or obj.reviewed_by.username,
        }


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
