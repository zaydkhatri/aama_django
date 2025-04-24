from django.contrib import admin

# Register your models here.
# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Address, Session, NotificationPreference

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

class SessionInline(admin.TabularInline):
    model = Session
    extra = 0
    readonly_fields = ('token', 'user_agent', 'ip_address', 'expires_at', 'created_at', 'updated_at')
    can_delete = True

class NotificationPreferenceInline(admin.StackedInline):
    model = NotificationPreference
    can_delete = False

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'phone', 'role', 'is_active', 'is_email_verified', 'created_at')
    list_filter = ('is_active', 'is_email_verified', 'role', 'created_at')
    search_fields = ('email', 'name', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('name', 'phone')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'role')}),
        (_('Account status'), {'fields': ('is_email_verified', 'login_attempts', 'last_login_attempt', 'last_login')}),
        (_('Verification tokens'), {'fields': ('email_verification_token', 'email_verification_expiry', 
                                              'password_reset_token', 'password_reset_expiry')}),
        (_('Important dates'), {'fields': ('created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    inlines = [AddressInline, NotificationPreferenceInline, SessionInline]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Only superusers can see admin users
        if not request.user.is_superuser:
            queryset = queryset.exclude(role='ADMIN', is_superuser=True)
        return queryset

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_line1', 'city', 'state', 'country', 'address_type', 'is_default')
    list_filter = ('address_type', 'is_default', 'country', 'state', 'city')
    search_fields = ('user__email', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
    raw_id_fields = ('user',)