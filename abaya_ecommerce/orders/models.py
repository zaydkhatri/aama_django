from django.db import models

# Create your models here.
# orders/models.py
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from products.models import Product, Currency

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    
    shipping_address = models.ForeignKey('users.Address', on_delete=models.PROTECT, related_name='shipping_orders')
    billing_address = models.ForeignKey('users.Address', on_delete=models.PROTECT, related_name='billing_orders')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.order_number
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('order_detail', kwargs={'order_number': self.order_number})
    
    @property
    def is_paid(self):
        return self.payment_status == 'PAID'
    
    @property
    def is_cancelled(self):
        return self.status == 'CANCELLED'
    
    @property
    def is_completed(self):
        return self.status == 'COMPLETED'
    
    @property
    def can_be_cancelled(self):
        return self.status in ['PENDING', 'PROCESSING']
    
    def calculate_subtotal(self):
        """Calculate order subtotal from order items."""
        return sum(item.total for item in self.items.all())
    
    def calculate_total(self):
        """Calculate order total including tax, shipping, and discounts."""
        return self.subtotal + self.shipping_amount + self.tax_amount - self.discount_amount
    
    def update_totals(self):
        """Update order totals based on current items, tax, shipping, and discounts."""
        self.subtotal = self.calculate_subtotal()
        self.total = self.calculate_total()
        self.save(update_fields=['subtotal', 'total'])


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Update total before saving
        self.total = self.quantity * self.price
        super().save(*args, **kwargs)
        
        # Update order totals
        self.order.update_totals()


class OrderStatusLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=20, choices=Order.ORDER_STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)  # User ID or system
    
    class Meta:
        verbose_name = 'Order Status Log'
        verbose_name_plural = 'Order Status Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Status change to {self.status} for order {self.order.order_number}"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if now < self.start_date or now > self.end_date:
            return False
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        
        return True
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount based on coupon type and value."""
        if not self.is_valid:
            return Decimal('0.00')
        
        if self.min_order_amount and order_amount < self.min_order_amount:
            return Decimal('0.00')
        
        if self.type == 'PERCENTAGE':
            discount = order_amount * (self.value / Decimal('100.00'))
        else:  # FIXED
            discount = self.value
        
        # Apply maximum discount if set
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount
        
        return discount


class CouponCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='categories')
    category_id = models.UUIDField()
    
    class Meta:
        verbose_name = 'Coupon Category'
        verbose_name_plural = 'Coupon Categories'
        unique_together = ('coupon', 'category_id')
    
    def __str__(self):
        return f"Coupon {self.coupon.code} - Category {self.category_id}"


class CouponProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='products')
    product_id = models.UUIDField()
    
    class Meta:
        verbose_name = 'Coupon Product'
        verbose_name_plural = 'Coupon Products'
        unique_together = ('coupon', 'product_id')
    
    def __str__(self):
        return f"Coupon {self.coupon.code} - Product {self.product_id}"


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('UPI', 'UPI'),
        ('NET_BANKING', 'Net Banking'),
        ('WALLET', 'Wallet'),
        ('COD', 'Cash on Delivery'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)  # Currency code
    status = models.CharField(max_length=20, choices=Order.PAYMENT_STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_gateway = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment of {self.amount} {self.currency} for order {self.order.order_number}"


class Shipment(models.Model):
    SHIPMENT_STATUS_CHOICES = (
        ('PROCESSING', 'Processing'),
        ('READY_FOR_PICKUP', 'Ready for Pickup'),
        ('PICKED_UP', 'Picked Up'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('FAILED_DELIVERY', 'Failed Delivery'),
        ('RETURNED', 'Returned'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    carrier = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS_CHOICES, default='PROCESSING')
    estimated_delivery = models.DateTimeField(blank=True, null=True)
    actual_delivery = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Shipment'
        verbose_name_plural = 'Shipments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Shipment for order {self.order.order_number}"


class ShipmentLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=Shipment.SHIPMENT_STATUS_CHOICES)
    location = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Shipment Log'
        verbose_name_plural = 'Shipment Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Status change to {self.status} for shipment of order {self.shipment.order.order_number}"


class Return(models.Model):
    RETURN_STATUS_CHOICES = (
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('RECEIVED', 'Received'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    REFUND_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='returns')
    return_number = models.CharField(max_length=50, unique=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='REQUESTED')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Return'
        verbose_name_plural = 'Returns'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Return {self.return_number} for order {self.order.order_number}"


class ReturnItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='return_items')
    quantity = models.PositiveIntegerField()
    reason = models.TextField(blank=True, null=True)
    condition = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Return Item'
        verbose_name_plural = 'Return Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in return {self.return_request.return_number}"


class ReturnLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=Return.RETURN_STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)  # User ID or system
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Return Log'
        verbose_name_plural = 'Return Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Status change to {self.status} for return {self.return_request.return_number}"