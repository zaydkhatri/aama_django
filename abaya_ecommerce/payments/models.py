from django.db import models

# Create your models here.
# payments/models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class PaymentMethod(models.Model):
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)  # Last 4 digits for cards
    card_brand = models.CharField(max_length=20, blank=True, null=True)  # Visa, Mastercard, etc.
    card_exp_month = models.CharField(max_length=2, blank=True, null=True)
    card_exp_year = models.CharField(max_length=4, blank=True, null=True)
    upi_id = models.CharField(max_length=50, blank=True, null=True)  # For UPI payments
    wallet_provider = models.CharField(max_length=50, blank=True, null=True)  # For wallet payments
    tokenized_data = models.TextField(blank=True, null=True)  # Encrypted payment info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        if self.type in ['CREDIT_CARD', 'DEBIT_CARD'] and self.card_last_four:
            return f"{self.get_type_display()} ending in {self.card_last_four}"
        elif self.type == 'UPI' and self.upi_id:
            return f"UPI: {self.upi_id}"
        elif self.type == 'WALLET' and self.wallet_provider:
            return f"{self.wallet_provider} Wallet"
        else:
            return self.get_type_display()
    
    def save(self, *args, **kwargs):
        # If this payment method is being set as default, unset default flag for other methods of this user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class PaymentGatewaySettings(models.Model):
    GATEWAY_CHOICES = (
        ('STRIPE', 'Stripe'),
        ('RAZORPAY', 'Razorpay'),
        ('PAYPAL', 'PayPal'),
        ('PAYU', 'PayU'),
        ('PAYUMONEY', 'PayUmoney'),
        ('INSTAMOJO', 'Instamojo'),
        ('CASHFREE', 'Cashfree'),
        ('PAYTM', 'Paytm'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, unique=True)
    is_active = models.BooleanField(default=False)
    display_name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    merchant_id = models.CharField(max_length=255, blank=True, null=True)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    test_mode = models.BooleanField(default=True)
    additional_settings = models.JSONField(blank=True, null=True)
    payment_methods = models.JSONField(blank=True, null=True, 
                                      help_text=_('List of supported payment methods as JSON'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Gateway Setting'
        verbose_name_plural = 'Payment Gateway Settings'
    
    def __str__(self):
        return f"{self.display_name} ({'Test' if self.test_mode else 'Live'})"


class Transaction(models.Model):
    STATUS_CHOICES = (
        ('INITIATED', 'Initiated'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='transactions')
    payment = models.ForeignKey('orders.Payment', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    gateway = models.CharField(max_length=20, choices=PaymentGatewaySettings.GATEWAY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)  # Currency code
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    payment_method = models.CharField(max_length=50)
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_order_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_test = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.gateway} transaction for order {self.order.order_number} - {self.status}"


class WebhookEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ('PAYMENT_INTENT_SUCCEEDED', 'Payment Intent Succeeded'),
        ('PAYMENT_INTENT_FAILED', 'Payment Intent Failed'),
        ('CHARGE_SUCCEEDED', 'Charge Succeeded'),
        ('CHARGE_FAILED', 'Charge Failed'),
        ('CHARGE_REFUNDED', 'Charge Refunded'),
        ('CHECKOUT_COMPLETED', 'Checkout Completed'),
        ('CHECKOUT_FAILED', 'Checkout Failed'),
        ('OTHER', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gateway = models.CharField(max_length=20, choices=PaymentGatewaySettings.GATEWAY_CHOICES)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, default='OTHER')
    event_id = models.CharField(max_length=255)
    is_test = models.BooleanField(default=True)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Webhook Event'
        verbose_name_plural = 'Webhook Events'
        ordering = ['-created_at']
        unique_together = ('gateway', 'event_id')
    
    def __str__(self):
        return f"{self.gateway} webhook: {self.event_type} ({self.event_id})"


class Refund(models.Model):
    STATUS_CHOICES = (
        ('INITIATED', 'Initiated'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    gateway_refund_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund of {self.amount} for transaction {self.transaction.id}"