from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, TechnicianProfile, ClientProfile, AdminProfile,
    DealershipProfile, Wallet, WalletTransaction, OTPVerification,
    TechnicianSkillSet, TechnicianImage
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'governorate', 'is_active', 'date_joined')
    list_filter = ('role', 'governorate', 'gender', 'is_active', 'is_staff', 'is_delete')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'governorate', 'address', 'gender', 'date_of_birth', 'profile_image', 'is_delete')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'governorate', 'address', 'gender', 'date_of_birth')}),
    )


class TechnicianImageInline(admin.TabularInline):
    model = TechnicianImage
    extra = 0
    fields = ('image', 'description', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'is_available', 'approved', 'rate', 'years_of_expertise', 'is_complete', 'created_at')
    list_filter = ('is_available', 'approved', 'is_complete', 'is_delete', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__phone_number', 'job_title', 'about')
    readonly_fields = ('id', 'rate', 'is_complete', 'created_at', 'updated_at', 'last_active', 'is_online')
    inlines = [TechnicianImageInline]
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Professional Info', {'fields': ('job_title', 'about', 'years_of_expertise', 'identification_documents', 'url1', 'url2')}),
        ('Status', {'fields': ('is_available', 'approved', 'is_complete', 'rate', 'last_active', 'is_online')}),
        ('Skills', {'fields': ('skill_sets',)}),
        ('System', {'fields': ('id', 'is_delete', 'created_at', 'updated_at')}),
    )
    
    actions = ['approve_technicians', 'disapprove_technicians', 'mark_available', 'mark_unavailable']
    
    def approve_technicians(self, request, queryset):
        queryset.update(approved=True)
    approve_technicians.short_description = "Approve selected technicians"
    
    def disapprove_technicians(self, request, queryset):
        queryset.update(approved=False)
    disapprove_technicians.short_description = "Disapprove selected technicians"
    
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_available.short_description = "Mark as available"
    
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_unavailable.short_description = "Mark as unavailable"


@admin.register(TechnicianSkillSet)
class TechnicianSkillSetAdmin(admin.ModelAdmin):
    list_display = ('technician', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('technician__user__username', 'technician__user__email')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('categories', 'skills', 'sub_skills')


@admin.register(TechnicianImage)
class TechnicianImageAdmin(admin.ModelAdmin):
    list_display = ('technician', 'description', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('technician__user__username', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_complete', 'is_delete', 'created_at')
    list_filter = ('is_complete', 'is_delete', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__phone_number')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(DealershipProfile)
class DealershipProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'amount_usd', 'exchange_rate', 'description', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'transaction_id')
    list_filter = ()
    search_fields = ('user__username', 'user__email', 'transaction_id')
    readonly_fields = ('transaction_id',)
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'contract', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__username', 'description', 'contract__contract_reference')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'created_at', 'is_used', 'is_expired')
    list_filter = ('created_at', 'is_used')
    search_fields = ('user__username', 'user__email', 'user__phone_number', 'otp_code', 'verification_id')
    readonly_fields = ('created_at', 'verification_id')
    
    def is_expired(self, obj):
        return not obj.is_valid()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
