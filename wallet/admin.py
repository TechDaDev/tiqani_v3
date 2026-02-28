from django.contrib import admin

from .models import Wallet, WalletTransaction, PlatformWallet, PlatformWalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'transaction_id')
    search_fields = ('user__username', 'user__email', 'transaction_id')
    ordering = ('-balance',)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'contract', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__username', 'wallet__user__email', 'description')
    ordering = ('-created_at',)


@admin.register(PlatformWallet)
class PlatformWalletAdmin(admin.ModelAdmin):
    list_display = (
        'key', 'currency', 'balance', 'total_fees_collected',
        'total_client_fees', 'total_technician_fees', 'updated_at'
    )
    readonly_fields = (
        'key', 'currency', 'balance', 'total_fees_collected',
        'total_client_fees', 'total_technician_fees', 'created_at', 'updated_at'
    )


@admin.register(PlatformWalletTransaction)
class PlatformWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('platform_wallet', 'source_type', 'amount', 'balance_after', 'contract', 'source_user', 'created_at')
    list_filter = ('source_type', 'created_at')
    search_fields = ('description', 'contract__contract_reference', 'source_user__username')
    ordering = ('-created_at',)
