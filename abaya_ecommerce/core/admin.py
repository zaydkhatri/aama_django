from django.contrib import admin

# Register your models here.
# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Setting, EmailTemplate, EmailLog, ActivityLog

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('group_key', 'get_value_preview', 'type', 'is_public', 'updated_at')
    list_filter = ('group', 'type', 'is_public', 'updated_at')
    search_fields = ('group', 'key', 'value')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('group', 'key', 'value', 'type', 'is_public')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def group_key(self, obj):
        return f"{obj.group}.{obj.key}"
    group_key.short_description = 'Setting'
    
    def get_value_preview(self, obj):
        if obj.type == 'HTML':
            return format_html('<span title="{}">{}</span>', obj.value, obj.value[:50] + '...' if len(obj.value) > 50 else obj.value)
        else:
            return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    get_value_preview.short_description = 'Value'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'subject', 'html_content', 'text_content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'is_active')
        }),
        (_('Content'), {
            'fields': ('html_content', 'text_content'),
        }),
        (_('Variables'), {
            'fields': ('variables',),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'status', 'template_name', 'sent_at', 'created_at')
    list_filter = ('status', 'sent_at', 'created_at')
    search_fields = ('recipient', 'subject', 'body', 'user__email')
    readonly_fields = ('template', 'recipient', 'subject', 'body', 'user', 'status', 
                      'error_message', 'sent_at', 'opened_at', 'clicked_at', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('template', 'recipient', 'subject', 'status')
        }),
        (_('Content'), {
            'fields': ('body',),
            'classes': ('collapse',),
        }),
        (_('Tracking'), {
            'fields': ('user', 'sent_at', 'opened_at', 'clicked_at'),
        }),
        (_('Error'), {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    def template_name(self, obj):
        return obj.template.name if obj.template else '-'
    template_name.short_description = 'Template'
    
    def has_add_permission(self, request):
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'entity_type', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__email', 'action', 'entity_id', 'details', 'ip_address')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id', 'details', 
                      'ip_address', 'user_agent', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'action', 'created_at')
        }),
        (_('Entity'), {
            'fields': ('entity_type', 'entity_id'),
        }),
        (_('Details'), {
            'fields': ('details',),
            'classes': ('collapse',),
        }),
        (_('Client Information'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        return False