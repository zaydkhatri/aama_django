# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .models import (
    Order, OrderItem, OrderStatusLog, Coupon, CouponCategory, CouponProduct,
    Payment, Shipment, ShipmentLog, Return, ReturnItem, ReturnLog
)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'size', 'color', 'fabric', 'quantity', 'price', 'total')
    readonly_fields = ('total',)

class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ('status', 'notes', 'created_at', 'created_by')
    fields = ('status', 'notes', 'created_at', 'created_by')
    can_delete = False
    max_num = 0
    
    def has_add_permission(self, request, obj=None):
        return False

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('payment_method', 'amount', 'currency', 'status', 'transaction_id', 'payment_gateway', 'created_at')
    readonly_fields = ('created_at',)

class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0
    fields = ('tracking_number', 'carrier', 'status', 'estimated_delivery', 'actual_delivery')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__email', 'user__name')
    readonly_fields = ('created_at', 'updated_at', 'subtotal', 'total')
    fieldsets = (
        (None, {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        (_('Addresses'), {
            'fields': ('shipping_address', 'billing_address')
        }),
        (_('Amounts'), {
            'fields': ('currency', 'subtotal', 'shipping_amount', 'tax_amount', 'discount_amount', 'total')
        }),
        (_('Additional Info'), {
            'fields': ('coupon', 'notes', 'created_at', 'updated_at')
        }),
    )
    inlines = [OrderItemInline, OrderStatusLogInline, PaymentInline, ShipmentInline]
    
    def save_model(self, request, obj, form, change):
        """Add status log when order status is changed."""
        if change and 'status' in form.changed_data:
            old_obj = Order.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                OrderStatusLog.objects.create(
                    order=obj,
                    status=obj.status,
                    notes=f"Status changed from {old_obj.status} to {obj.status}",
                    created_by=request.user.email
                )
        super().save_model(request, obj, form, change)

class CouponCategoryInline(admin.TabularInline):
    model = CouponCategory
    extra = 1
    fields = ('category_id',)

class CouponProductInline(admin.TabularInline):
    model = CouponProduct
    extra = 1
    fields = ('product_id',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'type', 'value', 'is_active', 'start_date', 'end_date', 'usage_count', 'usage_limit')
    list_filter = ('is_active', 'type', 'start_date', 'end_date')
    search_fields = ('code', 'description')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('code', 'type', 'value', 'is_active')
        }),
        (_('Restrictions'), {
            'fields': ('min_order_amount', 'max_discount_amount', 'start_date', 'end_date', 'usage_limit', 'usage_count')
        }),
        (_('Additional Info'), {
            'fields': ('description', 'created_at', 'updated_at')
        }),
    )
    inlines = [CouponCategoryInline, CouponProductInline]

class ShipmentLogInline(admin.TabularInline):
    model = ShipmentLog
    extra = 0
    fields = ('status', 'location', 'notes', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'tracking_number', 'carrier', 'status', 'estimated_delivery', 'created_at')
    list_filter = ('status', 'carrier', 'created_at')
    search_fields = ('tracking_number', 'order__order_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ShipmentLogInline]
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def save_model(self, request, obj, form, change):
        """Add shipment log when status is changed."""
        if change and 'status' in form.changed_data:
            old_obj = Shipment.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                ShipmentLog.objects.create(
                    shipment=obj,
                    status=obj.status,
                    notes=f"Status changed from {old_obj.status} to {obj.status}"
                )
                
                # If delivered, update order status and shipment delivery date
                if obj.status == 'DELIVERED' and not obj.actual_delivery:
                    from django.utils import timezone
                    obj.actual_delivery = timezone.now()
                    
                    # Update order status if all shipments are delivered
                    order = obj.order
                    if (order.status not in ['DELIVERED', 'COMPLETED'] and 
                        all(s.status == 'DELIVERED' for s in order.shipments.all())):
                        order.status = 'DELIVERED'
                        order.save()
                        OrderStatusLog.objects.create(
                            order=order,
                            status='DELIVERED',
                            notes="Order marked as delivered as all shipments were delivered",
                            created_by="System"
                        )
                
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'payment_method', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('order__order_number', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def save_model(self, request, obj, form, change):
        """Update order payment status when payment status changes."""
        super().save_model(request, obj, form, change)
        if change and 'status' in form.changed_data:
            # Update order payment status based on all payments
            order = obj.order
            payments = order.payments.all()
            
            if all(payment.status == 'PAID' for payment in payments):
                order.payment_status = 'PAID'
            elif any(payment.status == 'PAID' for payment in payments):
                order.payment_status = 'PARTIALLY_PAID'
            elif any(payment.status == 'REFUNDED' for payment in payments):
                order.payment_status = 'REFUNDED'
            else:
                order.payment_status = 'PENDING'
            
            order.save(update_fields=['payment_status'])

class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    fields = ('product', 'size', 'color', 'fabric', 'quantity', 'reason', 'condition')

class ReturnLogInline(admin.TabularInline):
    model = ReturnLog
    extra = 0
    fields = ('status', 'notes', 'created_by', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'order_link', 'user', 'status', 'refund_status', 'refund_amount', 'created_at')
    list_filter = ('status', 'refund_status', 'created_at')
    search_fields = ('return_number', 'order__order_number', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ReturnItemInline, ReturnLogInline]
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def save_model(self, request, obj, form, change):
        """Add return log when status is changed."""
        if change and ('status' in form.changed_data or 'refund_status' in form.changed_data):
            old_obj = Return.objects.get(pk=obj.pk)
            notes = []
            
            if 'status' in form.changed_data and old_obj.status != obj.status:
                notes.append(f"Status changed from {old_obj.status} to {obj.status}")
                
            if 'refund_status' in form.changed_data and old_obj.refund_status != obj.refund_status:
                notes.append(f"Refund status changed from {old_obj.refund_status} to {obj.refund_status}")
            
            if notes:
                ReturnLog.objects.create(
                    return_request=obj,
                    status=obj.status,
                    notes=". ".join(notes),
                    created_by=request.user.email
                )
                
                # If return is completed and refunded, update order status
                if obj.status == 'COMPLETED' and obj.refund_status == 'COMPLETED':
                    order = obj.order
                    if order.status not in ['REFUNDED', 'CANCELLED']:
                        order.status = 'REFUNDED'
                        order.payment_status = 'REFUNDED'
                        order.save(update_fields=['status', 'payment_status'])
                        OrderStatusLog.objects.create(
                            order=order,
                            status='REFUNDED',
                            notes="Order marked as refunded due to completed return and refund",
                            created_by="System"
                        )
                
        super().save_model(request, obj, form, change)