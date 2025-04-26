# carts/models.py
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product, Currency

User = get_user_model()

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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

    # Currency display methods
    def shipping_cost_display(self):
        """Get the formatted shipping cost with currency symbol."""
        if not self.shipping_cost:
            return "Free"
            
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Convert shipping cost if needed
        shipping_cost = self.shipping_cost
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            shipping_cost = convert_price(shipping_cost, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(shipping_cost, selected_currency)

    def discount_display(self):
        """Get the formatted discount amount with currency symbol."""
        if not self.discount_amount:
            return "-"
            
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Convert discount amount if needed
        discount = self.discount_amount
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            discount = convert_price(discount, default_currency, selected_currency)
        
        # Format with currency symbol
        return "- " + format_price(discount, selected_currency)

    def get_subtotal_display(self):
        """Get the formatted subtotal with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Calculate subtotal in default currency
        subtotal = self.get_total_price()
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            subtotal = convert_price(subtotal, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(subtotal, selected_currency)

    def get_total_display(self):
        """Get the formatted total (subtotal + shipping - discounts) with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Calculate subtotal in default currency
        subtotal = self.get_total_price()
        
        # Include shipping and discounts
        total = subtotal + self.shipping_cost - self.discount_amount
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            total = convert_price(total, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(total, selected_currency)


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

    def get_unit_price_display(self):
        """Get the formatted unit price with currency symbol."""
        return self.product.get_price_display()

    def get_total_price_display(self):
        """Get the formatted total price (unit price × quantity) with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Get the unit price in the default currency
        if self.product.sale_price:
            unit_price = self.product.sale_price
        else:
            unit_price = self.product.price
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            unit_price = convert_price(unit_price, default_currency, selected_currency)
        
        # Calculate total
        total = unit_price * self.quantity
        
        # Format with currency symbol
        return format_price(total, selected_currency)


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
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
        
    # Add similar currency display methods as Cart model
    def shipping_cost_display(self):
        """Get the formatted shipping cost with currency symbol."""
        if not self.shipping_cost:
            return "Free"
            
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Convert shipping cost if needed
        shipping_cost = self.shipping_cost
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            shipping_cost = convert_price(shipping_cost, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(shipping_cost, selected_currency)

    def discount_display(self):
        """Get the formatted discount amount with currency symbol."""
        if not self.discount_amount:
            return "-"
            
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Convert discount amount if needed
        discount = self.discount_amount
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            discount = convert_price(discount, default_currency, selected_currency)
        
        # Format with currency symbol
        return "- " + format_price(discount, selected_currency)

    def get_subtotal_display(self):
        """Get the formatted subtotal with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Calculate subtotal in default currency
        subtotal = self.get_total_price()
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            subtotal = convert_price(subtotal, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(subtotal, selected_currency)

    def get_total_display(self):
        """Get the formatted total (subtotal + shipping - discounts) with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Calculate subtotal in default currency
        subtotal = self.get_total_price()
        
        # Include shipping and discounts
        total = subtotal + self.shipping_cost - self.discount_amount
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            total = convert_price(total, default_currency, selected_currency)
        
        # Format with currency symbol
        return format_price(total, selected_currency)


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
        
    # Add similar currency display methods as CartItem model
    def get_unit_price_display(self):
        """Get the formatted unit price with currency symbol."""
        return self.product.get_price_display()

    def get_total_price_display(self):
        """Get the formatted total price (unit price × quantity) with currency symbol."""
        # Get the default currency and the selected currency
        from products.models import Currency
        from core.middleware import get_current_request
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            default_currency = None
        
        # Try to get the selected currency
        selected_currency = None
        try:
            request = get_current_request()
            if request and request.session.get('currency_code'):
                try:
                    selected_currency = Currency.objects.get(
                        code=request.session['currency_code'],
                        is_active=True
                    )
                except Currency.DoesNotExist:
                    selected_currency = default_currency
            else:
                selected_currency = default_currency
        except:
            selected_currency = default_currency
        
        # Get the unit price in the default currency
        if self.product.sale_price:
            unit_price = self.product.sale_price
        else:
            unit_price = self.product.price
        
        # Convert to selected currency if needed
        if default_currency and selected_currency and default_currency.id != selected_currency.id:
            unit_price = convert_price(unit_price, default_currency, selected_currency)
        
        # Calculate total
        total = unit_price * self.quantity
        
        # Format with currency symbol
        return format_price(total, selected_currency)