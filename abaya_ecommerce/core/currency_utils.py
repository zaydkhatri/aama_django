# core/currency_utils.py
from products.models import Currency

def get_selected_currency(request):
    """
    Get the currently selected currency from session or use default.
    """
    currency_code = request.session.get('currency_code')
    
    # If no currency is selected or the selected currency doesn't exist, use default
    if not currency_code:
        try:
            default_currency = Currency.objects.get(is_default=True)
            request.session['currency_code'] = default_currency.code
            return default_currency
        except Currency.DoesNotExist:
            # If no default currency, create INR as default
            default_currency = Currency.objects.create(
                code='INR',
                name='Indian Rupee',
                symbol='₹',
                exchange_rate=1.0,
                is_default=True,
                is_active=True
            )
            request.session['currency_code'] = default_currency.code
            return default_currency
    
    # Get the selected currency
    try:
        return Currency.objects.get(code=currency_code, is_active=True)
    except Currency.DoesNotExist:
        # If selected currency doesn't exist or is inactive, use default
        try:
            default_currency = Currency.objects.get(is_default=True)
            request.session['currency_code'] = default_currency.code
            return default_currency
        except Currency.DoesNotExist:
            # Fallback to INR if everything fails
            return Currency.objects.create(
                code='INR',
                name='Indian Rupee',
                symbol='₹',
                exchange_rate=1.0,
                is_default=True,
                is_active=True
            )

def convert_price(price, from_currency, to_currency):
    """
    Convert price from one currency to another using exchange rates.
    
    Args:
        price: Price in the source currency
        from_currency: Source Currency object or code
        to_currency: Target Currency object or code
    
    Returns:
        Converted price value in the target currency
    """
    if price is None:
        return None
    
    # Convert currency codes to Currency objects if needed
    if isinstance(from_currency, str):
        try:
            from_currency = Currency.objects.get(code=from_currency, is_active=True)
        except Currency.DoesNotExist:
            from_currency = Currency.objects.get(is_default=True)
    
    if isinstance(to_currency, str):
        try:
            to_currency = Currency.objects.get(code=to_currency, is_active=True)
        except Currency.DoesNotExist:
            to_currency = Currency.objects.get(is_default=True)
    
    # Base currency (usually the default currency) has exchange_rate of 1.0
    # Convert price to base currency, then to target currency
    base_price = price / from_currency.exchange_rate
    converted_price = base_price * to_currency.exchange_rate
    
    # Round to 2 decimal places
    return round(converted_price, 2)

def format_price(price, currency):
    """
    Format price with currency symbol.
    
    Args:
        price: Price value
        currency: Currency object or code
    
    Returns:
        Formatted price string with currency symbol
    """
    if price is None:
        return None
    
    # Convert currency code to Currency object if needed
    if isinstance(currency, str):
        try:
            currency = Currency.objects.get(code=currency, is_active=True)
        except Currency.DoesNotExist:
            currency = Currency.objects.get(is_default=True)
    
    return f"{currency.symbol}{price:,.2f}"

# Add this function to core/currency_utils.py

def get_selected_currency_from_request():
    """
    Get the currently selected currency from the request.
    Falls back to default currency if no currency is selected or if the selected currency doesn't exist.
    To be used within model methods.
    """
    from products.models import Currency
    from core.middleware import get_current_request
    
    # Get default currency
    try:
        default_currency = Currency.objects.get(is_default=True)
    except Currency.DoesNotExist:
        # Create a default currency if none exists
        default_currency = Currency.objects.create(
            code='INR',
            name='Indian Rupee',
            symbol='₹',
            exchange_rate=1.0,
            is_default=True,
            is_active=True
        )
    
    # Try to get the selected currency from the request
    try:
        request = get_current_request()
        if request and request.session.get('currency_code'):
            try:
                return Currency.objects.get(
                    code=request.session['currency_code'],
                    is_active=True
                )
            except Currency.DoesNotExist:
                return default_currency
    except:
        pass
    
    return default_currency