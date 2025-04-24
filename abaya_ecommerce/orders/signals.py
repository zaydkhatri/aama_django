# orders/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import (
    Order, OrderItem, OrderStatusLog, Payment, Shipment,
    ShipmentLog, Return, ReturnLog
)

@receiver(post_save, sender=Order)
def create_order_status_log(sender, instance, created, **kwargs):
    """Create an initial status log when a new order is created."""
    if created:
        OrderStatusLog.objects.create(
            order=instance,
            status=instance.status,
            notes='Order created'
        )

@receiver(pre_save, sender=Order)
def log_order_status_change(sender, instance, **kwargs):
    """Log when order status changes."""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                OrderStatusLog.objects.create(
                    order=instance,
                    status=instance.status,
                    notes=f'Status changed from {old_instance.status} to {instance.status}'
                )
                
                # Send notification email if status is changed to shipped or delivered
                if instance.status == 'SHIPPED' and old_instance.status != 'SHIPPED':
                    send_order_shipped_email(instance)
                elif instance.status == 'DELIVERED' and old_instance.status != 'DELIVERED':
                    send_order_delivered_email(instance)
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Payment)
def update_order_payment_status(sender, instance, created, **kwargs):
    """Update order payment status when payment status changes."""
    order = instance.order
    
    # Check all payments for this order
    payments = Payment.objects.filter(order=order)
    
    if all(p.status == 'PAID' for p in payments):
        order.payment_status = 'PAID'
    elif any(p.status == 'PAID' for p in payments):
        order.payment_status = 'PARTIALLY_PAID'
    elif any(p.status == 'REFUNDED' for p in payments):
        order.payment_status = 'REFUNDED'
    else:
        order.payment_status = 'PENDING'
    
    # Update order and create status log if necessary
    if order.payment_status != order.payment_status or created:
        old_status = order.payment_status
        order.payment_status = order.payment_status
        order.save(update_fields=['payment_status'])
        
        if old_status != order.payment_status:
            OrderStatusLog.objects.create(
                order=order,
                status=order.status,
                notes=f'Payment status changed to {order.payment_status}'
            )
            
            # If payment is completed, update order status to processing
            if order.payment_status == 'PAID' and order.status == 'PENDING':
                order.status = 'PROCESSING'
                order.save(update_fields=['status'])
                
                OrderStatusLog.objects.create(
                    order=order,
                    status='PROCESSING',
                    notes='Order status updated to processing after payment received'
                )

@receiver(post_save, sender=Shipment)
def create_shipment_log(sender, instance, created, **kwargs):
    """Create an initial shipment log when a new shipment is created."""
    if created:
        ShipmentLog.objects.create(
            shipment=instance,
            status=instance.status,
            notes='Shipment created'
        )

@receiver(pre_save, sender=Shipment)
def log_shipment_status_change(sender, instance, **kwargs):
    """Log when shipment status changes and update order status if needed."""
    if instance.pk:
        try:
            old_instance = Shipment.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                ShipmentLog.objects.create(
                    shipment=instance,
                    status=instance.status,
                    notes=f'Status changed from {old_instance.status} to {instance.status}'
                )
                
                # If delivered, update order status and shipment delivery date
                if instance.status == 'DELIVERED' and not instance.actual_delivery:
                    instance.actual_delivery = timezone.now()
                    
                    # Update order status if all shipments are delivered
                    order = instance.order
                    if (order.status not in ['DELIVERED', 'COMPLETED'] and 
                        all(s.status == 'DELIVERED' for s in order.shipments.all())):
                        order.status = 'DELIVERED'
                        order.save(update_fields=['status'])
                        OrderStatusLog.objects.create(
                            order=order,
                            status='DELIVERED',
                            notes="Order marked as delivered as all shipments were delivered"
                        )
                        
                        # Send delivery notification
                        send_order_delivered_email(order)
        except Shipment.DoesNotExist:
            pass

@receiver(post_save, sender=Return)
def create_return_log(sender, instance, created, **kwargs):
    """Create an initial return log when a new return is created."""
    if created:
        ReturnLog.objects.create(
            return_request=instance,
            status=instance.status,
            notes='Return request created'
        )

@receiver(pre_save, sender=Return)
def log_return_status_change(sender, instance, **kwargs):
    """Log when return status changes and update order if needed."""
    if instance.pk:
        try:
            old_instance = Return.objects.get(pk=instance.pk)
            status_changed = old_instance.status != instance.status
            refund_status_changed = old_instance.refund_status != instance.refund_status
            
            if status_changed or refund_status_changed:
                notes = []
                
                if status_changed:
                    notes.append(f"Status changed from {old_instance.status} to {instance.status}")
                
                if refund_status_changed:
                    notes.append(f"Refund status changed from {old_instance.refund_status} to {instance.refund_status}")
                
                ReturnLog.objects.create(
                    return_request=instance,
                    status=instance.status,
                    notes=". ".join(notes)
                )
                
                # If return is completed and refunded, update order status
                if instance.status == 'COMPLETED' and instance.refund_status == 'COMPLETED':
                    order = instance.order
                    if order.status not in ['REFUNDED', 'CANCELLED']:
                        order.status = 'REFUNDED'
                        order.payment_status = 'REFUNDED'
                        order.save(update_fields=['status', 'payment_status'])
                        OrderStatusLog.objects.create(
                            order=order,
                            status='REFUNDED',
                            notes="Order marked as refunded due to completed return and refund"
                        )
                
                # Send notification emails based on status changes
                if status_changed:
                    if instance.status == 'APPROVED':
                        send_return_approved_email(instance)
                    elif instance.status == 'REJECTED':
                        send_return_rejected_email(instance)
                    elif instance.status == 'COMPLETED':
                        send_return_completed_email(instance)
        except Return.DoesNotExist:
            pass

# Email sending functions
def send_order_shipped_email(order):
    """Send notification when order is shipped."""
    subject = f'Your Order {order.order_number} Has Been Shipped'
    context = {
        'order': order,
        'user': order.user,
        'shipments': order.shipments.all()
    }
    html_message = render_to_string('orders/emails/order_shipped.html', context)
    plain_message = render_to_string('orders/emails/order_shipped_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_order_delivered_email(order):
    """Send notification when order is delivered."""
    subject = f'Your Order {order.order_number} Has Been Delivered'
    context = {
        'order': order,
        'user': order.user
    }
    html_message = render_to_string('orders/emails/order_delivered.html', context)
    plain_message = render_to_string('orders/emails/order_delivered_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_return_approved_email(return_request):
    """Send notification when return is approved."""
    subject = f'Your Return Request {return_request.return_number} Has Been Approved'
    context = {
        'return_request': return_request,
        'user': return_request.user,
        'order': return_request.order
    }
    html_message = render_to_string('orders/emails/return_approved.html', context)
    plain_message = render_to_string('orders/emails/return_approved_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [return_request.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_return_rejected_email(return_request):
    """Send notification when return is rejected."""
    subject = f'Your Return Request {return_request.return_number} Has Been Rejected'
    context = {
        'return_request': return_request,
        'user': return_request.user,
        'order': return_request.order
    }
    html_message = render_to_string('orders/emails/return_rejected.html', context)
    plain_message = render_to_string('orders/emails/return_rejected_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [return_request.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_return_completed_email(return_request):
    """Send notification when return is completed."""
    subject = f'Your Return Request {return_request.return_number} Has Been Completed'
    context = {
        'return_request': return_request,
        'user': return_request.user,
        'order': return_request.order
    }
    html_message = render_to_string('orders/emails/return_completed.html', context)
    plain_message = render_to_string('orders/emails/return_completed_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [return_request.user.email],
        html_message=html_message,
        fail_silently=False
    )