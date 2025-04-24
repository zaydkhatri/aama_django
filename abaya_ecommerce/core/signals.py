# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import EmailLog

@receiver(post_save, sender=EmailLog)
def update_email_status(sender, instance, created, **kwargs):
    """Handle email status updates and tracking."""
    if created:
        # If the email is already marked as sent, no need to update
        if instance.status == 'SENT' and not instance.sent_at:
            instance.sent_at = timezone.now()
            instance.save(update_fields=['sent_at'])