# Update core/templatetags/currency_filters.py with this implementation

from django import template
from core.currency_utils import convert_price, format_price
from django.core.cache import cache

register = template.Library()

@register.filter(name='convert_currency')
def convert_currency_filter(price, to_currency=None):
    """
    Convert price to the selected currency.
    Usage: {{ product.price|convert_currency }}
    """
    if not price:
        return 0
    
    # If no currency specified, use the selected currency from context
    if not to_currency:
        from core.middleware import get_current_request
        request = get_current_request()
        if request:
            from core.currency_utils import get_selected_currency
            to_currency = get_selected_currency(request)
    
    # Get the default currency (prices are stored in this currency)
    from products.models import Currency
    try:
        default_currency = Currency.objects.get(is_default=True)
    except Currency.DoesNotExist:
        return price
    
    # Convert the price
    return convert_price(price, default_currency, to_currency)

@register.filter(name='format_currency')
def format_currency_filter(price, currency=None):
    """
    Format price with the selected currency symbol.
    Usage: {{ product.price|convert_currency|format_currency }}
    or: {{ product.price|format_currency:currency }}
    """
    if not price:
        return ''
    
    # If no currency specified, use the selected currency from context
    if not currency:
        from core.middleware import get_current_request
        request = get_current_request()
        if request:
            from core.currency_utils import get_selected_currency
            currency = get_selected_currency(request)
    
    return format_price(price, currency)

@register.filter(name='currency')
def currency_filter(price, currency=None):
    """
    Convert and format price in one step.
    Usage: {{ product.price|currency }}
    """
    if not price:
        return ''
    
    # If no currency specified, use the selected currency from context
    if not currency:
        from core.middleware import get_current_request
        request = get_current_request()
        if request:
            from core.currency_utils import get_selected_currency
            currency = get_selected_currency(request)
    
    # Get the default currency (prices are stored in this currency)
    from products.models import Currency
    try:
        default_currency = Currency.objects.get(is_default=True)
    except Currency.DoesNotExist:
        return format_price(price, currency)
    
    # Convert and format the price
    converted_price = convert_price(price, default_currency, currency)
    return format_price(converted_price, currency)