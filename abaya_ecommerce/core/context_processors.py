# core/context_processors.py
from products.models import Currency
from core.currency_utils import get_selected_currency

def currency_processor(request):
    """
    Context processor to add currency information to all templates.
    """
    # Get all active currencies for the currency selector
    currencies = Currency.objects.filter(is_active=True).order_by('-is_default', 'code')
    
    # Get the currently selected currency
    selected_currency = get_selected_currency(request)
    
    return {
        'currencies': currencies,
        'selected_currency': selected_currency,
    }