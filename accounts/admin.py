from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q

from .models import (
    CustomUser, 
    TechnicianProfile, 
    ClientProfile, 
    AdminProfile,
    Wallet,
    WalletTransaction,
    OTPVerification,
    TechnicianSkillSet,
    TechnicianImage
)


# --- Inline Admins ---

class TechnicianProfileInline(admin.StackedInline):
    model = TechnicianProfile
    can_delete = False
    verbose_name_plural = 'Technician Profile'
    fk_name = 'user'
    fields = (
        'is_available', 'approved', 'is_complete',
        'job_title', 'about', 'years_of_expertise', 'rate',
        'identification_documents', 'github', 'linkedin',
        'last_active'
    )
    readonly_fields = ('rate', 'is_complete', 'last_active')


class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    can_delete = False
    verbose_name_plural = 'Client Profile'
    fk_name = 'user'
    fields = ('is_complete',)
    readonly_fields = ('is_complete',)


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = 'Admin Profile'
    fk_name = 'user'
    fields = ('role', 'notes', 'last_login_ip')
    readonly_fields = ('last_login_ip',)


class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    verbose_name_plural = 'Wallet'
    fields = ('balance', 'transaction_id')
    readonly_fields = ('transaction_id',)


class OTPVerificationInline(admin.TabularInline):
    model = OTPVerification
    extra = 0
    can_delete = False
    fields = ('otp_code', 'verification_id', 'is_used', 'created_at')
    readonly_fields = ('otp_code', 'verification_id', 'is_used', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False


class TechnicianImageInline(admin.TabularInline):
    model = TechnicianImage
    extra = 1
    fields = ('image', 'description', 'created_at')
    readonly_fields = ('created_at',)


# --- Main Admin Classes ---

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'role', 'full_name_display', 
        'phone_number', 'governorate', 'is_active', 
        'profile_status', 'created_at'
    )
    list_filter = (
        'role', 'is_active', 'is_staff', 'is_superuser', 
        'governorate', 'gender', 'created_at'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'gender', 'date_of_birth')
        }),
        ('Location', {
            'fields': ('governorate', 'address')
        }),
        ('Profile', {
            'fields': ('role', 'profile_image')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('is_delete',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'first_name', 'last_name'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        """Dynamically show inlines based on user role"""
        if not obj:
            return []
        
        inlines = [WalletInline, OTPVerificationInline]
        
        if obj.role == 'technician':
            inlines.insert(0, TechnicianProfileInline)
        elif obj.role == 'client':
            inlines.insert(0, ClientProfileInline)
        elif obj.role == 'admin':
            inlines.insert(0, AdminProfileInline)
        
        return [inline(self.model, self.admin_site) for inline in inlines]

    def full_name_display(self, obj):
        return obj.get_full_name() or '-'
    full_name_display.short_description = 'Full Name'

    def profile_status(self, obj):
        """Show profile completion status"""
        if obj.role == 'technician' and hasattr(obj, 'technician_profile'):
            is_complete = obj.technician_profile.is_complete
            color = 'green' if is_complete else 'orange'
            text = '✓ Complete' if is_complete else '⚠ Incomplete'
        elif obj.role == 'client' and hasattr(obj, 'client_profile'):
            is_complete = obj.client_profile.is_complete
            color = 'green' if is_complete else 'orange'
            text = '✓ Complete' if is_complete else '⚠ Incomplete'
        elif obj.role == 'admin' and hasattr(obj, 'admin_profile'):
            return format_html('<span style="color: blue;">{}</span>', '● Admin')
        else:
            return format_html('<span style="color: red;">{}</span>', '✗ No Profile')
        
        return format_html('<span style="color: {};">{}</span>', color, text)
    profile_status.short_description = 'Profile Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'technician_profile', 
            'client_profile', 
            'admin_profile'
        )


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'job_title', 'is_available', 
        'approved', 'is_complete', 'incomplete_fields_display', 'rate', 'years_of_expertise',
        'online_status', 'created_at'
    )
    list_filter = (
        'is_available', 'approved', 'is_complete', 
        'rate', 'created_at'
    )
    search_fields = (
        'user__username', 'user__email', 
        'user__first_name', 'user__last_name', 
        'job_title', 'about'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Link', {
            'fields': ('user',)
        }),
        ('Professional Info', {
            'fields': ('job_title', 'about', 'years_of_expertise')
        }),
        ('Status', {
            'fields': ('is_available', 'approved', 'is_complete', 'incomplete_fields_list')
        }),
        ('Rating & Activity', {
            'fields': ('rate', 'last_active')
        }),
        ('Documents & Links', {
            'fields': ('identification_documents', 'github', 'linkedin')
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('rate', 'is_complete', 'incomplete_fields_list', 'created_at', 'updated_at')
    inlines = [TechnicianImageInline]

    def user_display(self, obj):
        return f"{obj.user.get_full_name()} (@{obj.user.username})"
    user_display.short_description = 'User'

    def incomplete_fields_display(self, obj):
        """Show count of incomplete fields in list view."""
        missing = obj.get_missing_fields()
        if not missing:
            return mark_safe('<span style="color: green;">✓ Complete</span>')
        count = len(missing)
        return format_html('<span style="color: orange;">{} missing</span>', count)
    incomplete_fields_display.short_description = 'Incomplete Fields'

    def incomplete_fields_list(self, obj):
        """Show list of incomplete fields in detail view."""
        missing = obj.get_missing_fields()
        if not missing:
            return mark_safe('<span style="color: green;">✓ All required fields completed</span>')
        fields_html = '<br>'.join([f'• {field}' for field in missing])
        return format_html('<span style="color: red;">{}</span>', fields_html)
    incomplete_fields_list.short_description = 'Missing Required Fields'

    def online_status(self, obj):
        if obj.is_online:
            return format_html('<span style="color: green;">{}</span>', '● Online')
        return format_html('<span style="color: gray;">{}</span>', '○ Offline')
    online_status.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    actions = ['approve_technicians', 'reject_technicians', 'mark_available', 'mark_unavailable', 'recalculate_completion']

    def approve_technicians(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f'{updated} technician(s) approved successfully.')
    approve_technicians.short_description = 'Approve selected technicians'

    def reject_technicians(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f'{updated} technician(s) rejected.')
    reject_technicians.short_description = 'Reject selected technicians'

    def mark_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} technician(s) marked as available.')
    mark_available.short_description = 'Mark as available'

    def mark_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} technician(s) marked as unavailable.')
    mark_unavailable.short_description = 'Mark as unavailable'

    def recalculate_completion(self, request, queryset):
        """Recalculate is_complete status for selected profiles."""
        count = 0
        for profile in queryset:
            profile.save()  # Triggers completion calculation in save() hook
            count += 1
        self.message_user(request, f'{count} profile completion status(es) recalculated.')
    recalculate_completion.short_description = 'Recalculate profile completion status'


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'user_email', 'user_phone', 
        'is_complete', 'incomplete_fields_display', 'age_display', 'created_at'
    )
    list_filter = ('is_complete', 'created_at')
    search_fields = (
        'user__username', 'user__email', 
        'user__first_name', 'user__last_name', 
        'user__phone_number'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Link', {
            'fields': ('user',)
        }),
        ('Profile Status', {
            'fields': ('is_complete', 'incomplete_fields_list')
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('is_complete', 'incomplete_fields_list', 'created_at', 'updated_at')

    def user_display(self, obj):
        return f"{obj.user.get_full_name()} (@{obj.user.username})"
    user_display.short_description = 'User'

    def incomplete_fields_display(self, obj):
        """Show count of incomplete fields in list view."""
        missing = obj.get_missing_fields()
        if not missing:
            return mark_safe('<span style="color: green;">✓ Complete</span>')
        count = len(missing)
        return format_html('<span style="color: orange;">{} missing</span>', count)
    incomplete_fields_display.short_description = 'Incomplete Fields'

    def incomplete_fields_list(self, obj):
        """Show list of incomplete fields in detail view."""
        missing = obj.get_missing_fields()
        if not missing:
            return mark_safe('<span style="color: green;">✓ All required fields completed</span>')
        fields_html = '<br>'.join([f'• {field}' for field in missing])
        return format_html('<span style="color: red;">{}</span>', fields_html)
    incomplete_fields_list.short_description = 'Missing Required Fields'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def user_phone(self, obj):
        return obj.user.phone_number or '-'
    user_phone.short_description = 'Phone'

    def age_display(self, obj):
        age = obj.user.age
        if age:
            color = 'green' if age >= 18 else 'red'
            return format_html('<span style="color: {};">{} years</span>', color, age)
        return '-'
    age_display.short_description = 'Age'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    actions = ['recalculate_completion']

    def recalculate_completion(self, request, queryset):
        """Recalculate is_complete status for selected profiles."""
        count = 0
        for profile in queryset:
            profile.save()  # Triggers completion calculation in save() hook
            count += 1
        self.message_user(request, f'{count} profile completion status(es) recalculated.')
    recalculate_completion.short_description = 'Recalculate profile completion status'


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'role', 'user_is_staff', 
        'last_login_ip', 'created_at'
    )
    list_filter = ('role', 'created_at')
    search_fields = (
        'user__username', 'user__email', 
        'notes', 'last_login_ip'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Link', {
            'fields': ('user',)
        }),
        ('Admin Info', {
            'fields': ('role', 'notes')
        }),
        ('Activity', {
            'fields': ('last_login_ip',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('last_login_ip', 'created_at', 'updated_at')

    def user_display(self, obj):
        return f"{obj.user.get_full_name()} (@{obj.user.username})"
    user_display.short_description = 'User'

    def user_is_staff(self, obj):
        if obj.user.is_staff:
            return format_html('<span style="color: green;">{}</span>', '✓ Staff')
        return format_html('<span style="color: red;">{}</span>', '✗ Not Staff')
    user_is_staff.short_description = 'Staff Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'balance', 'transaction_id', 
        'transaction_count'
    )
    list_filter = ('balance',)
    search_fields = (
        'user__username', 'user__email', 
        'transaction_id'
    )
    ordering = ('-balance',)
    
    fieldsets = (
        ('Wallet Info', {
            'fields': ('user', 'balance', 'transaction_id')
        }),
    )
    
    readonly_fields = ('transaction_id',)

    def user_display(self, obj):
        return f"{obj.user.get_full_name()} (@{obj.user.username})"
    user_display.short_description = 'User'

    def transaction_count(self, obj):
        count = obj.transactions.count()
        url = reverse("admin:accounts_wallettransaction_changelist")
        return format_html('<a href="{}?wallet__id__exact={}">{} transactions</a>', url, obj.id, count)
    transaction_count.short_description = 'Transactions'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').annotate(
            trans_count=Count('transactions')
        )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'wallet_display', 'transaction_type', 'amount', 
        'amount_usd', 'contract_link', 'created_at'
    )
    list_filter = ('transaction_type', 'created_at')
    search_fields = (
        'wallet__user__username', 'wallet__user__email',
        'description', 'transaction_type'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('wallet', 'transaction_type', 'description')
        }),
        ('Amounts', {
            'fields': ('amount', 'amount_usd', 'exchange_rate')
        }),
        ('Related', {
            'fields': ('contract',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def wallet_display(self, obj):
        return f"{obj.wallet.user.username} - {obj.wallet.transaction_id}"
    wallet_display.short_description = 'Wallet'

    def contract_link(self, obj):
        if obj.contract:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:contract_contract_change', args=[obj.contract.id]),
                str(obj.contract.id)[:8]
            )
        return '-'
    contract_link.short_description = 'Contract'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('wallet__user', 'contract')


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'otp_code', 'is_used', 
        'is_valid_status', 'created_at'
    )
    list_filter = ('is_used', 'created_at')
    search_fields = (
        'user__username', 'user__email', 
        'otp_code', 'verification_id'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('OTP Info', {
            'fields': ('user', 'otp_code', 'verification_id')
        }),
        ('Status', {
            'fields': ('is_used',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.email})"
    user_display.short_description = 'User'

    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">{}</span>', '✓ Valid')
        return format_html('<span style="color: red;">{}</span>', '✗ Expired/Used')
    is_valid_status.short_description = 'Valid'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(TechnicianSkillSet)
class TechnicianSkillSetAdmin(admin.ModelAdmin):
    list_display = (
        'id_display', 'technician_display', 
        'category_count', 'skill_count', 'subskill_count',
        'created_at'
    )
    list_filter = ('created_at',)
    search_fields = (
        'technician__user__username', 
        'technician__user__first_name', 
        'technician__user__last_name'
    )
    ordering = ('-created_at',)
    
    filter_horizontal = ('categories', 'skills', 'sub_skills')
    
    fieldsets = (
        ('Technician', {
            'fields': ('technician',)
        }),
        ('Skills', {
            'fields': ('categories', 'skills', 'sub_skills')
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def id_display(self, obj):
        return str(obj.id)[:8] + '...'
    id_display.short_description = 'ID'

    def technician_display(self, obj):
        return f"{obj.technician.user.get_full_name()} (@{obj.technician.user.username})"
    technician_display.short_description = 'Technician'

    def category_count(self, obj):
        return obj.categories.count()
    category_count.short_description = 'Categories'

    def skill_count(self, obj):
        return obj.skills.count()
    skill_count.short_description = 'Skills'

    def subskill_count(self, obj):
        return obj.sub_skills.count()
    subskill_count.short_description = 'Sub-Skills'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('technician__user').prefetch_related(
            'categories', 'skills', 'sub_skills'
        )


@admin.register(TechnicianImage)
class TechnicianImageAdmin(admin.ModelAdmin):
    list_display = (
        'id_display', 'technician_display', 
        'image_preview', 'description', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = (
        'technician__user__username', 
        'description'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Image Info', {
            'fields': ('technician', 'image', 'description')
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'is_delete'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def id_display(self, obj):
        return str(obj.id)[:8] + '...'
    id_display.short_description = 'ID'

    def technician_display(self, obj):
        return f"{obj.technician.user.username}"
    technician_display.short_description = 'Technician'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('technician__user')
