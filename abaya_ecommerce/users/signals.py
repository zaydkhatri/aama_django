# users/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import User, NotificationPreference, Session

@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences for new users."""
    if created:
        NotificationPreference.objects.get_or_create(user=instance)

@receiver(post_save, sender=Session)
def update_user_last_login(sender, instance, created, **kwargs):
    """Update user's last login time when a new session is created."""
    if created:
        user = instance.user
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

@receiver(pre_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """Ensure all user data is properly deleted."""
    # This is handled by CASCADE delete, but we could add additional cleanup here if needed
    pass