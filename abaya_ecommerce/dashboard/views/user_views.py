# dashboard/views/user_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse

from users.models import User, Address
from orders.models import Order
from dashboard.forms import UserFilterForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def user_list(request):
    """Display a list of users with search and filter options."""
    # Initialize filter form
    filter_form = UserFilterForm(request.GET)
    
    # Get all users except superusers (if current user is not a superuser)
    if request.user.is_superuser:
        users = User.objects.all().order_by('-created_at')
    else:
        users = User.objects.exclude(is_superuser=True).order_by('-created_at')
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        # Search filter
        search = filter_form.cleaned_data.get('search')
        if search:
            users = users.filter(
                Q(email__icontains=search) | 
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Role filter
        role = filter_form.cleaned_data.get('role')
        if role:
            users = users.filter(role=role)
        
        # Active status filter
        is_active = filter_form.cleaned_data.get('is_active')
        if is_active:
            users = users.filter(is_active=(is_active == '1'))
        
        # Date joined filters
        date_joined_from = filter_form.cleaned_data.get('date_joined_from')
        if date_joined_from:
            users = users.filter(created_at__date__gte=date_joined_from)
        
        date_joined_to = filter_form.cleaned_data.get('date_joined_to')
        if date_joined_to:
            users = users.filter(created_at__date__lte=date_joined_to)
    
    # Annotate with order count and total spend
    users = users.annotate(
        order_count=Count('orders', distinct=True),
        total_spend=Sum('orders__total')
    )
    
    # Paginate results
    users = paginate_queryset(request, users, 20)
    
    return render(request, 'dashboard/users/list.html', {
        'users': users,
        'filter_form': filter_form,
    })

@staff_member_required
def user_detail(request, uuid):
    """Display detailed information about a user."""
    user = get_object_or_404(User, id=uuid)
    
    # Check if current user has permission to view this user
    if not request.user.is_superuser and user.is_superuser:
        messages.error(request, "You do not have permission to view this user.")
        return redirect('dashboard:user_list')
    
    # Get user addresses
    addresses = Address.objects.filter(user=user)
    
    # Get recent orders
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Calculate statistics
    stats = {
        'order_count': Order.objects.filter(user=user).count(),
        'total_spend': Order.objects.filter(user=user).aggregate(total=Sum('total'))['total'] or 0,
        'average_order_value': Order.objects.filter(user=user).aggregate(avg=Sum('total') / Count('id'))['avg'] or 0,
    }
    
    return render(request, 'dashboard/users/detail.html', {
        'user_obj': user,  # Using user_obj to avoid conflict with request.user
        'addresses': addresses,
        'recent_orders': recent_orders,
        'stats': stats,
    })

@staff_member_required
def user_orders(request, uuid):
    """Display all orders for a specific user."""
    user = get_object_or_404(User, id=uuid)
    
    # Get all orders for this user
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Paginate results
    orders = paginate_queryset(request, orders, 20)
    
    return render(request, 'dashboard/users/orders.html', {
        'user_obj': user,
        'orders': orders,
    })