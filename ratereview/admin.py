from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('technician', 'reviewer', 'rating', 'is_verified', 'is_public', 'helpful_count', 'reported_count', 'created_at')
    list_filter = ('is_public', 'is_verified', 'rating', 'created_at', 'flagged_at')
    search_fields = ('technician__user__username', 'reviewer__username', 'title', 'comment', 'contract__contract_reference')
    readonly_fields = ('id', 'rating', 'helpful_count', 'reported_count', 'flagged_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Review Info', {'fields': ('contract', 'reviewer', 'technician')}),
        ('Ratings', {'fields': ('rating', 'work_quality_rating', 'communication_rating', 'timeliness_rating', 'professionalism_rating')}),
        ('Content', {'fields': ('title', 'comment', 'technician_response')}),
        ('Status', {'fields': ('is_public', 'is_verified')}),
        ('Moderation', {'fields': ('helpful_count', 'reported_count', 'flagged_at')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    actions = ['publish_reviews', 'hide_reviews', 'verify_reviews', 'unverify_reviews']
    
    def publish_reviews(self, request, queryset):
        for review in queryset:
            review.publish()
    publish_reviews.short_description = "Publish selected reviews"
    
    def hide_reviews(self, request, queryset):
        for review in queryset:
            review.hide()
    hide_reviews.short_description = "Hide selected reviews"
    
    def verify_reviews(self, request, queryset):
        queryset.update(is_verified=True)
    verify_reviews.short_description = "Verify selected reviews"
    
    def unverify_reviews(self, request, queryset):
        queryset.update(is_verified=False)
    unverify_reviews.short_description = "Unverify selected reviews"
