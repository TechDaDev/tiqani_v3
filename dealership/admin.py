"""
Django admin configuration for dealership models.
"""

from django.contrib import admin

from .models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipCreditLedger,
    DealershipSettlement,
)


@admin.register(DealershipProfile)
class DealershipProfileAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 'user', 'status', 'active',
        'financially_locked', 'suspended', 'blocked',
        'approved_at',
    ]
    list_filter = ['status', 'active', 'financially_locked', 'suspended', 'blocked', 'governorate']
    search_fields = ['business_name', 'owner_name', 'user__username', 'user__email']
    readonly_fields = ['approved_at', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(DealershipGuarantee)
class DealershipGuaranteeAdmin(admin.ModelAdmin):
    list_display = [
        'dealership', 'total_guarantee_amount', 'status',
        'verified_by', 'verified_at', 'expires_at',
    ]
    list_filter = ['status']
    search_fields = ['dealership__business_name', 'notes']
    readonly_fields = ['total_guarantee_amount', 'verified_at', 'created_at', 'updated_at']


@admin.register(DealershipRechargeFeeConfig)
class DealershipRechargeFeeConfigAdmin(admin.ModelAdmin):
    list_display = ['fee_percent', 'default_fee_mode', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'default_fee_mode']


@admin.register(DealershipClientRecharge)
class DealershipClientRechargeAdmin(admin.ModelAdmin):
    list_display = [
        'dealership', 'client', 'wallet_credit_amount',
        'status', 'receipt_number', 'completed_at',
    ]
    list_filter = ['status', 'fee_mode']
    search_fields = ['dealership__business_name', 'client__username', 'receipt_number']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(DealershipClientCashout)
class DealershipClientCashoutAdmin(admin.ModelAdmin):
    list_display = [
        'dealership', 'client', 'amount', 'status',
        'confirmed_at', 'completed_at',
    ]
    list_filter = ['status']
    search_fields = ['dealership__business_name', 'client__username']
    readonly_fields = ['created_at', 'completed_at', 'cancelled_at']


@admin.register(DealershipCreditLedger)
class DealershipCreditLedgerAdmin(admin.ModelAdmin):
    list_display = [
        'dealership', 'transaction_type', 'amount',
        'balance_after', 'created_at',
    ]
    list_filter = ['transaction_type']
    search_fields = ['dealership__business_name', 'notes']
    readonly_fields = ['created_at']


@admin.register(DealershipSettlement)
class DealershipSettlementAdmin(admin.ModelAdmin):
    list_display = [
        'dealership', 'period_start', 'period_end',
        'net_amount', 'direction', 'status', 'settled_at',
    ]
    list_filter = ['status', 'direction']
    search_fields = ['dealership__business_name', 'notes']
    readonly_fields = ['created_at', 'settled_at']
