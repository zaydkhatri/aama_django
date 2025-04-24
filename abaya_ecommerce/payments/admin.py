from django.contrib import admin

# Register your models here.
# payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    PaymentMethod, PaymentGatewaySettings, Transaction, WebhookEvent, Refund
)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'display_info', 'is_default', 'created_at')
    list_filter = ('type', 'is_default', 'created_at')
    search_fields = ('user__email', 'card_last_four', 'upi_id', 'wallet_provider')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'type', 'is_default')
        }),
        (_('Card Details'), {
            'fields': ('card_last_four', 'card_brand', 'card_exp_month', 'card_exp_year'),
            'classes': ('collapse',),
        }),
        (_('Other Payment Methods'), {
            'fields': ('upi_id', 'wallet_provider'),
            'classes': ('collapse',),
        }),
        (_('Security'), {
            'fields': ('tokenized_data',),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def display_info(self, obj):
        if obj.type in ['CREDIT_CARD', 'DEBIT_CARD'] and obj.card_last_four:
            return f"{obj.card_brand} ending in {obj.card_last_four}"
        elif obj.type == 'UPI' and obj.upi_id:
            return obj.upi_id
        elif obj.type == 'WALLET' and obj.wallet_provider:
            return obj.wallet_provider
        return "-"
    display_info.short_description = 'Details'


@admin.register(PaymentGatewaySettings)
class PaymentGatewaySettingsAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'gateway', 'is_active', 'test_mode', 'created_at')
    list_filter = ('is_active', 'test_mode', 'gateway', 'created_at')
    search_fields = ('display_name', 'gateway', 'merchant_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('gateway', 'display_name', 'description', 'is_active', 'test_mode')
        }),
        (_('API Credentials'), {
            'fields': ('api_key', 'api_secret', 'merchant_id', 'webhook_secret'),
            'classes': ('collapse',),
        }),
        (_('Additional Settings'), {
            'fields': ('additional_settings', 'payment_methods'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('amount', 'reason', 'status', 'gateway_refund_id', 'created_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'gateway', 'amount', 'currency', 'status', 'payment_method', 'is_test', 'created_at')
    list_filter = ('status', 'gateway', 'is_test', 'created_at')
    search_fields = ('order__order_number', 'gateway_transaction_id', 'gateway_order_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RefundInline]
    fieldsets = (
        (None, {
            'fields': ('order', 'payment', 'gateway', 'amount', 'currency', 'status', 'payment_method', 'is_test')
        }),
        (_('Gateway Information'), {
            'fields': ('gateway_transaction_id', 'gateway_order_id', 'gateway_response'),
            'classes': ('collapse',),
        }),
        (_('Additional Information'), {
            'fields': ('error_message', 'refund_amount', 'ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def order_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'gateway', 'event_type', 'is_test', 'processed', 'created_at')
    list_filter = ('gateway', 'event_type', 'is_test', 'processed', 'created_at')
    search_fields = ('event_id', 'payload')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('gateway', 'event_type', 'event_id', 'is_test', 'processed', 'transaction')
        }),
        (_('Payload and Error'), {
            'fields': ('payload', 'error_message'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('transaction_link', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction__gateway_transaction_id', 'gateway_refund_id', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('transaction', 'amount', 'reason', 'status')
        }),
        (_('Gateway Information'), {
            'fields': ('gateway_refund_id', 'gateway_response', 'error_message'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def transaction_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:payments_transaction_change', args=[obj.transaction.id])
        return format_html('<a href="{}">{}</a>', url, obj.transaction.gateway_transaction_id or obj.transaction.id)
    transaction_link.short_description = 'Transaction'