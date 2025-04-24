# carts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Cart, Wishlist

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_cart_and_wishlist(sender, instance, created, **kwargs):
    """Create cart and wishlist for new users."""
    if created:
        Cart.objects.get_or_create(user=instance)
        Wishlist.objects.get_or_create(user=instance)