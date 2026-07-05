from django.contrib import admin

from .models import (
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PlatformEarning,
    PaymentIntent,
    WalletRechargeRequest,
    WithdrawalRequest,
)


@admin.register(PlatformFeeConfig)
class PlatformFeeConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "technician_commission_rate", "client_service_fee_rate", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(ContractPaymentBreakdown)
class ContractPaymentBreakdownAdmin(admin.ModelAdmin):
    list_display = ("contract", "contract_amount", "total_platform_fee", "client_total_amount", "technician_net_amount")
    search_fields = ("contract__contract_reference",)


@admin.register(PlatformEarning)
class PlatformEarningAdmin(admin.ModelAdmin):
    list_display = ("contract", "earning_type", "amount", "status", "created_at")
    list_filter = ("earning_type", "status")
    search_fields = ("contract__contract_reference",)


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("id", "contract", "user", "amount", "purpose", "provider", "status", "paid_at")
    list_filter = ("status", "purpose", "provider")
    search_fields = ("contract__contract_reference", "user__username")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("user__username",)


@admin.register(WalletRechargeRequest)
class WalletRechargeRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "status", "created_at", "reviewed_at")
    list_filter = ("status", "currency")
    search_fields = ("user__username", "user__email", "original_filename", "review_note")
    readonly_fields = (
        "original_filename",
        "file_size",
        "mime_type",
        "approved_transaction",
        "created_at",
        "updated_at",
    )
