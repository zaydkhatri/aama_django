# payments/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import Transaction, Refund

@receiver(post_save, sender=Transaction)
def send_transaction_notification(sender, instance, created, **kwargs):
    """Send email notification when a transaction is created or updated."""
    if created:
        # Send transaction initiated notification
        if instance.order and instance.order.user:
            subject = f'Payment Initiated for Order #{instance.order.order_number}'
            context = {
                'transaction': instance,
                'order': instance.order,
                'user': instance.order.user
            }
            html_message = render_to_string('payments/emails/transaction_initiated.html', context)
            plain_message = render_to_string('payments/emails/transaction_initiated_plain.html', context)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.order.user.email],
                html_message=html_message,
                fail_silently=True
            )
    else:
        # Check if status has changed
        try:
            old_instance = Transaction.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Send transaction status update notification
                if instance.order and instance.order.user:
                    subject = f'Payment Update for Order #{instance.order.order_number}'
                    context = {
                        'transaction': instance,
                        'order': instance.order,
                        'user': instance.order.user,
                        'old_status': old_instance.status,
                        'new_status': instance.status
                    }
                    html_message = render_to_string('payments/emails/transaction_update.html', context)
                    plain_message = render_to_string('payments/emails/transaction_update_plain.html', context)
                    
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.order.user.email],
                        html_message=html_message,
                        fail_silently=True
                    )
        except Transaction.DoesNotExist:
            pass

@receiver(post_save, sender=Refund)
def send_refund_notification(sender, instance, created, **kwargs):
    """Send email notification when a refund is created or updated."""
    if created:
        # Send refund initiated notification
        if instance.transaction and instance.transaction.order and instance.transaction.order.user:
            subject = f'Refund Initiated for Order #{instance.transaction.order.order_number}'
            context = {
                'refund': instance,
                'transaction': instance.transaction,
                'order': instance.transaction.order,
                'user': instance.transaction.order.user
            }
            html_message = render_to_string('payments/emails/refund_initiated.html', context)
            plain_message = render_to_string('payments/emails/refund_initiated_plain.html', context)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.transaction.order.user.email],
                html_message=html_message,
                fail_silently=True
            )
    else:
        # Check if status has changed
        try:
            old_instance = Refund.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Send refund status update notification
                if instance.transaction and instance.transaction.order and instance.transaction.order.user:
                    subject = f'Refund Update for Order #{instance.transaction.order.order_number}'
                    context = {
                        'refund': instance,
                        'transaction': instance.transaction,
                        'order': instance.transaction.order,
                        'user': instance.transaction.order.user,
                        'old_status': old_instance.status,
                        'new_status': instance.status
                    }
                    html_message = render_to_string('payments/emails/refund_update.html', context)
                    plain_message = render_to_string('payments/emails/refund_update_plain.html', context)
                    
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.transaction.order.user.email],
                        html_message=html_message,
                        fail_silently=True
                    )
        except Refund.DoesNotExist:
            pass