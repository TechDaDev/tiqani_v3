from django.contrib import admin
from .models import (
    Contract,
    ContractStage,
    TimeExtensionRequest,
    ContractVersion,
    ContractSignature,
    ContractDocument,
    PlatformAttestation,
    ContractAuditEvent,
)


class ContractStageInline(admin.TabularInline):
    model = ContractStage
    extra = 0
    fields = ('stage_number', 'stage_description', 'amount', 'deadline', 'is_approved_by_client', 'completed_at')
    readonly_fields = ('completed_at',)


class TimeExtensionRequestInline(admin.TabularInline):
    model = TimeExtensionRequest
    extra = 0
    fields = ('requested_days', 'reason', 'status', 'responded_at')
    readonly_fields = ('responded_at',)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('contract_reference', 'client', 'technician', 'status', 'agreed_amount', 'stage_number', 'client_accepted', 'technician_accepted', 'created_at')
    list_filter = ('status', 'client_accepted', 'technician_accepted', 'is_delete', 'created_at')
    search_fields = ('contract_reference', 'client__user__username', 'technician__user__username', 'work_description')
    readonly_fields = ('id', 'contract_reference', 'escrow_amount', 'total_paid', 'created_at', 'updated_at')
    inlines = [ContractStageInline, TimeExtensionRequestInline]
    
    fieldsets = (
        ('Parties', {'fields': ('client', 'technician')}),
        ('Contract Details', {'fields': ('contract_reference', 'work_description', 'start_date', 'duration_days', 'contract_duration', 'stage_number')}),
        ('Financial', {'fields': ('agreed_amount', 'amount_usd', 'escrow_amount', 'total_paid')}),
        ('Status', {'fields': ('status', 'client_accepted', 'technician_accepted')}),
        ('System', {'fields': ('id', 'is_delete', 'created_at', 'updated_at')}),
    )
    
    actions = ['mark_completed', 'cancel_contracts']
    
    def mark_completed(self, request, queryset):
        for contract in queryset:
            try:
                contract.mark_completed()
            except Exception as e:
                self.message_user(request, f"Error completing {contract.contract_reference}: {str(e)}", level='error')
    mark_completed.short_description = "Mark selected contracts as completed"
    
    def cancel_contracts(self, request, queryset):
        for contract in queryset:
            try:
                contract.cancel(reason="Admin cancellation")
            except Exception as e:
                self.message_user(request, f"Error cancelling {contract.contract_reference}: {str(e)}", level='error')
    cancel_contracts.short_description = "Cancel selected contracts"


@admin.register(ContractStage)
class ContractStageAdmin(admin.ModelAdmin):
    list_display = ('contract', 'stage_number', 'amount', 'deadline', 'is_approved_by_client', 'completed_at')
    list_filter = ('is_approved_by_client', 'completed_at', 'deadline')
    search_fields = ('contract__contract_reference', 'stage_description')
    readonly_fields = ('completed_at',)
    
    fieldsets = (
        ('Contract', {'fields': ('contract', 'stage_number')}),
        ('Details', {'fields': ('stage_description', 'amount', 'deadline')}),
        ('Status', {'fields': ('is_approved_by_client', 'completed_at', 'transaction')}),
    )


@admin.register(TimeExtensionRequest)
class TimeExtensionRequestAdmin(admin.ModelAdmin):
    list_display = ('contract', 'requested_days', 'status', 'created_at', 'responded_at')
    list_filter = ('status', 'created_at', 'responded_at')
    search_fields = ('contract__contract_reference', 'reason', 'client_response')
    readonly_fields = ('created_at', 'responded_at', 'updated_at')
    
    fieldsets = (
        ('Request', {'fields': ('contract', 'requested_by', 'requested_days', 'reason')}),
        ('Response', {'fields': ('status', 'client_response', 'responded_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    actions = ['approve_requests', 'deny_requests']
    
    def approve_requests(self, request, queryset):
        for ext_request in queryset.filter(status='pending'):
            try:
                ext_request.approve()
            except Exception as e:
                self.message_user(request, f"Error approving extension: {str(e)}", level='error')
    approve_requests.short_description = "Approve selected extension requests"
    
    def deny_requests(self, request, queryset):
        for ext_request in queryset.filter(status='pending'):
            try:
                ext_request.reject("Denied by admin")
            except Exception as e:
                self.message_user(request, f"Error denying extension: {str(e)}", level='error')
    deny_requests.short_description = "Deny selected extension requests"


# ──────────────────────────────────────────────
#  Phase 19: Electronic Contracts
# ──────────────────────────────────────────────


@admin.register(ContractVersion)
class ContractVersionAdmin(admin.ModelAdmin):
    list_display = ('contract', 'version_number', 'is_frozen', 'frozen_at', 'canonical_snapshot_hash')
    list_filter = ('is_frozen', 'frozen_at')
    search_fields = ('contract__contract_reference', 'canonical_snapshot_hash')
    readonly_fields = ('id', 'contract', 'version_number', 'canonical_snapshot', 'canonical_snapshot_hash',
                       'is_frozen', 'frozen_at', 'frozen_by', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # versions are created programmatically

    def has_delete_permission(self, request, obj=None):
        return False  # immutable — no deletion


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    list_display = ('contract_version', 'signer_role', 'signer', 'signed_at', 'signature_hash_short')
    list_filter = ('signer_role', 'signed_at')
    search_fields = ('contract_version__contract__contract_reference', 'signer__username', 'signature_hash')
    readonly_fields = ('id', 'contract_version', 'signer', 'signer_role', 'otp_verification',
                       'signed_at', 'signature_hash', 'ip_address', 'user_agent', 'created_at', 'updated_at')

    def signature_hash_short(self, obj):
        return obj.signature_hash[:20] + "..." if obj.signature_hash else "-"
    signature_hash_short.short_description = "Signature Hash"

    def has_add_permission(self, request):
        return False  # signatures are created via OTP flow

    def has_delete_permission(self, request, obj=None):
        return False  # immutable


@admin.register(ContractDocument)
class ContractDocumentAdmin(admin.ModelAdmin):
    list_display = ('contract_version', 'kind', 'sha256_short', 'file_size', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('contract_version__contract__contract_reference', 'sha256')
    readonly_fields = ('id', 'contract_version', 'kind', 'file', 'sha256', 'mime_type', 'file_size',
                       'created_by', 'created_at', 'updated_at')

    def sha256_short(self, obj):
        return obj.sha256[:20] + "..." if obj.sha256 else "-"
    sha256_short.short_description = "SHA-256"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of final signed documents
        if obj and obj.kind == 'signed_pdf':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PlatformAttestation)
class PlatformAttestationAdmin(admin.ModelAdmin):
    list_display = ('verification_code', 'contract_version', 'attestation_hash_short', 'created_at')
    search_fields = ('verification_code', 'contract_version__contract__contract_reference')
    readonly_fields = ('id', 'contract_version', 'verification_code', 'attestation_hash',
                       'payload', 'created_at', 'updated_at')

    def attestation_hash_short(self, obj):
        return obj.attestation_hash[:20] + "..." if obj.attestation_hash else "-"
    attestation_hash_short.short_description = "Attestation Hash"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContractAuditEvent)
class ContractAuditEventAdmin(admin.ModelAdmin):
    list_display = ('contract', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('contract__contract_reference', 'event_type', 'actor__username')
    readonly_fields = ('id', 'contract', 'event_type', 'actor', 'payload', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
