# from django.contrib import admin

# # Register your models here.

from django.contrib import admin
from .models import DashboardActivity, DashboardSettings

@admin.register(DashboardActivity)
class DashboardActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'entity_type', 'entity_id', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__email', 'action', 'entity_id')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id', 'ip_address', 'details', 'created_at')
    
    def has_add_permission(self, request):
        return False

@admin.register(DashboardSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'is_public', 'updated_at')
    list_filter = ('is_public', 'updated_at')
    search_fields = ('key', 'value', 'description')