from django.contrib import admin

from .models import ServiceRequest


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "technician", "title", "status", "is_urgent", "created_at")
    list_filter = ("status", "is_urgent", "governorate")
    search_fields = ("title", "description", "client__user__username", "technician__user__username")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
