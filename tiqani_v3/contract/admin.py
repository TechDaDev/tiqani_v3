from django.contrib import admin
from .models import Contract, ContractStage, TimeExtensionRequest


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
    list_filter = ('status', 'client_accepted', 'technician_accepted', 'is_deleted', 'created_at')
    search_fields = ('contract_reference', 'client__user__username', 'technician__user__username', 'work_description')
    readonly_fields = ('id', 'contract_reference', 'escrow_amount', 'total_paid', 'created_at', 'updated_at')
    inlines = [ContractStageInline, TimeExtensionRequestInline]
    
    fieldsets = (
        ('Parties', {'fields': ('client', 'technician')}),
        ('Contract Details', {'fields': ('contract_reference', 'work_description', 'contract_duration', 'stage_number')}),
        ('Financial', {'fields': ('agreed_amount', 'amount_usd', 'exchange_rate', 'escrow_amount', 'total_paid')}),
        ('Status', {'fields': ('status', 'client_accepted', 'technician_accepted')}),
        ('System', {'fields': ('id', 'is_deleted', 'created_at', 'updated_at')}),
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
