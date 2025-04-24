from django.db import models

# Create your models here.
# carts/models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product, Currency

User = get_user_model()

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())
    
    def clear(self):
        self.items.all().delete()
        self.save()


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart"
    
    def get_total_price(self):
        return self.product.get_active_price() * self.quantity
    
    def update_quantity(self, quantity):
        self.quantity = quantity
        self.save()


class Wishlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
    
    def __str__(self):
        return f"Wishlist for {self.user.email}"
    
    def get_item_count(self):
        return self.items.count()


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ('wishlist', 'product')
    
    def __str__(self):
        return f"{self.product.name} in wishlist"


class GuestCart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=255, unique=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Guest Cart'
        verbose_name_plural = 'Guest Carts'
    
    def __str__(self):
        return f"Guest cart {self.id}"
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())
    
    def clear(self):
        self.items.all().delete()
        self.save()


class GuestCartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(GuestCart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Guest Cart Item'
        verbose_name_plural = 'Guest Cart Items'
        unique_together = ('cart', 'product')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in guest cart"
    
    def get_total_price(self):
        return self.product.get_active_price() * self.quantity
    
    def update_quantity(self, quantity):
        self.quantity = quantity
        self.save()