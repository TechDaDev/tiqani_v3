from django.contrib import admin
from .models import Category, Skill, SubSkill


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0
    fields = ('name', 'description', 'is_active', 'order')
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'is_featured', 'order', 'skill_count', 'created_at')
    list_filter = ('is_active', 'is_featured', 'parent', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'skill_count', 'technician_count', 'created_at', 'updated_at')
    inlines = [SkillInline]
    
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'description', 'icon', 'parent')}),
        ('Status & Display', {'fields': ('is_active', 'is_featured', 'order')}),
        ('Statistics', {'fields': ('skill_count', 'technician_count')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    actions = ['activate_categories', 'deactivate_categories', 'mark_featured', 'unmark_featured']
    
    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)
    activate_categories.short_description = "Activate selected categories"
    
    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_categories.short_description = "Deactivate selected categories"
    
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_featured.short_description = "Mark as featured"
    
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)
    unmark_featured.short_description = "Remove featured status"


class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 0
    fields = ('name', 'description', 'difficulty_level', 'is_active', 'order')
    show_change_link = True


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'order', 'technician_count', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    readonly_fields = ('id', 'technician_count', 'created_at', 'updated_at')
    inlines = [SubSkillInline]
    
    fieldsets = (
        ('Basic Info', {'fields': ('category', 'name', 'description')}),
        ('Status & Display', {'fields': ('is_active', 'order')}),
        ('Statistics', {'fields': ('technician_count',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    actions = ['activate_skills', 'deactivate_skills']
    
    def activate_skills(self, request, queryset):
        queryset.update(is_active=True)
    activate_skills.short_description = "Activate selected skills"
    
    def deactivate_skills(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_skills.short_description = "Deactivate selected skills"


@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill', 'difficulty_level', 'is_active', 'order', 'technician_count', 'created_at')
    list_filter = ('is_active', 'difficulty_level', 'skill__category', 'created_at')
    search_fields = ('name', 'description', 'skill__name', 'skill__category__name')
    readonly_fields = ('id', 'full_path', 'technician_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {'fields': ('skill', 'name', 'description')}),
        ('Status & Display', {'fields': ('is_active', 'difficulty_level', 'order')}),
        ('Hierarchy', {'fields': ('full_path',)}),
        ('Statistics', {'fields': ('technician_count',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    actions = ['activate_subskills', 'deactivate_subskills']
    
    def activate_subskills(self, request, queryset):
        queryset.update(is_active=True)
    activate_subskills.short_description = "Activate selected sub-skills"
    
    def deactivate_subskills(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_subskills.short_description = "Deactivate selected sub-skills"
