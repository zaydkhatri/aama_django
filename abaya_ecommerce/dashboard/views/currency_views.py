# dashboard/views/currency_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse

from products.models import Currency
from dashboard.forms import CurrencyForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def currency_list(request):
    """Display a list of currencies."""
    # Get all currencies
    currencies = Currency.objects.all().order_by('-is_default', 'code')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        currencies = currencies.filter(
            Q(code__icontains=search_query) | 
            Q(name__icontains=search_query)
        )
    
    # Paginate results
    currencies = paginate_queryset(request, currencies, 20)
    
    return render(request, 'dashboard/currencies/list.html', {
        'currencies': currencies,
        'search_query': search_query,
    })

@staff_member_required
def currency_create(request):
    """Create a new currency."""
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            currency = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'Currency',
                currency.id,
                f"Created currency '{currency.name} ({currency.code})'",
                request
            )
            
            messages.success(request, f"Currency '{currency.name} ({currency.code})' has been created successfully.")
            return redirect('dashboard:currency_list')
    else:
        form = CurrencyForm()
    
    return render(request, 'dashboard/currencies/form.html', {
        'form': form,
        'title': 'Create Currency',
    })

@staff_member_required
def currency_edit(request, uuid):
    """Edit an existing currency."""
    currency = get_object_or_404(Currency, id=uuid)
    
    if request.method == 'POST':
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            currency = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Currency',
                currency.id,
                f"Updated currency '{currency.name} ({currency.code})'",
                request
            )
            
            messages.success(request, f"Currency '{currency.name} ({currency.code})' has been updated successfully.")
            return redirect('dashboard:currency_list')
    else:
        form = CurrencyForm(instance=currency)
    
    return render(request, 'dashboard/currencies/form.html', {
        'form': form,
        'currency': currency,
        'title': f"Edit Currency: {currency.code}",
    })

@staff_member_required
def currency_delete(request, uuid):
    """Delete a currency."""
    currency = get_object_or_404(Currency, id=uuid)
    
    # Prevent deletion of default currency
    if currency.is_default:
        messages.error(request, "You cannot delete the default currency.")
        return redirect('dashboard:currency_list')
    
    if request.method == 'POST':
        # Get currency details for logging before deletion
        currency_name = currency.name
        currency_code = currency.code
        currency_id = str(currency.id)
        
        # Delete the currency
        currency.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Currency',
            currency_id,
            f"Deleted currency '{currency_name} ({currency_code})'",
            request
        )
        
        messages.success(request, f"Currency '{currency_name} ({currency_code})' has been deleted successfully.")
        return redirect('dashboard:currency_list')
    
    return render(request, 'dashboard/currencies/delete.html', {
        'currency': currency,
    })