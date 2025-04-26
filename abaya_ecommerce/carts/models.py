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

    # Add these additional methods to the Cart model

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
    
    # Add these methods to the Cart model in carts/models.py

    def get_total_price_in_currency(self, currency=None):
        """
        Get total price in the specified currency.
        If no currency is provided, it uses the default currency.
        """
        from products.models import Currency
        from core.currency_utils import convert_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            from decimal import Decimal
            return Decimal('0.00')
        
        # Calculate total in default currency
        total = sum(item.get_total_price() for item in self.items.all())
        
        # If no currency specified or same as default, return total
        if not currency or currency.id == default_currency.id:
            return total
        
        # Convert to specified currency
        return convert_price(total, default_currency, currency)

    def get_item_prices_in_currency(self, currency=None):
        """
        Get a list of cart items with prices converted to the specified currency.
        Returns a list of dictionaries with item and converted price information.
        """
        from products.models import Currency
        from core.currency_utils import convert_price, format_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            return []
        
        # Prepare item list
        items_with_prices = []
        
        for item in self.items.all():
            # Get price in default currency
            unit_price = item.product.get_active_price()
            total_price = unit_price * item.quantity
            
            # Convert to specified currency if needed
            if currency and currency.id != default_currency.id:
                unit_price_converted = convert_price(unit_price, default_currency, currency)
                total_price_converted = convert_price(total_price, default_currency, currency)
            else:
                unit_price_converted = unit_price
                total_price_converted = total_price
            
            # Format prices
            currency_to_use = currency or default_currency
            unit_price_display = format_price(unit_price_converted, currency_to_use)
            total_price_display = format_price(total_price_converted, currency_to_use)
            
            # Add to list
            items_with_prices.append({
                'item': item,
                'unit_price': unit_price_converted,
                'total_price': total_price_converted,
                'unit_price_display': unit_price_display,
                'total_price_display': total_price_display
            })
        
        return items_with_prices

    def get_subtotal_in_currency(self, currency=None):
        """Get the cart subtotal in the specified currency."""
        return self.get_total_price_in_currency(currency)

    def get_shipping_in_currency(self, shipping_address=None, currency=None):
        """
        Calculate shipping cost in the specified currency.
        Uses the default shipping calculation and converts the result.
        """
        from decimal import Decimal
        from products.models import Currency
        from core.currency_utils import convert_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            return Decimal('0.00')
        
        # Get cart total in default currency
        cart_total = self.get_total_price()
        
        # Calculate shipping in default currency
        from orders.views import calculate_shipping
        shipping_cost = calculate_shipping(cart_total, shipping_address)
        
        # Convert to specified currency if needed
        if currency and currency.id != default_currency.id:
            shipping_cost = convert_price(shipping_cost, default_currency, currency)
        
        return shipping_cost

    def get_tax_in_currency(self, shipping_address=None, currency=None):
        """
        Calculate tax in the specified currency.
        Uses the default tax calculation and converts the result.
        """
        from decimal import Decimal
        from products.models import Currency
        from core.currency_utils import convert_price
        
        # Get default currency
        try:
            default_currency = Currency.objects.get(is_default=True)
        except Currency.DoesNotExist:
            return Decimal('0.00')
        
        # Get cart total in default currency
        cart_total = self.get_total_price()
        
        # Calculate tax in default currency
        from orders.views import calculate_tax
        tax_amount = calculate_tax(cart_total, shipping_address)
        
        # Convert to specified currency if needed
        if currency and currency.id != default_currency.id:
            tax_amount = convert_price(tax_amount, default_currency, currency)
        
        return tax_amount


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

    # Add these methods to the CartItem model in carts/models.py

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


    # Add these methods to the Cart model in carts/models.py

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
        subtotal = 0
        for item in self.items.all():
            if item.product.sale_price:
                unit_price = item.product.sale_price
            else:
                unit_price = item.product.price
            
            subtotal += unit_price * item.quantity
        
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
        subtotal = 0
        for item in self.items.all():
            if item.product.sale_price:
                unit_price = item.product.sale_price
            else:
                unit_price = item.product.price
            
            subtotal += unit_price * item.quantity
        
        # Include shipping and discounts
        total = subtotal
        
        if self.shipping_cost:
            # Convert shipping cost if needed
            shipping_cost = self.shipping_cost
            if default_currency and selected_currency and default_currency.id != selected_currency.id:
                shipping_cost = convert_price(shipping_cost, default_currency, selected_currency)
            total += shipping_cost
        
        if self.discount_amount:
            # Convert discount if needed
            discount = self.discount_amount
            if default_currency and selected_currency and default_currency.id != selected_currency.id:
                discount = convert_price(discount, default_currency, selected_currency)
            total -= discount
        
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