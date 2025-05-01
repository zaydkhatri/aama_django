from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from products.models import Product, Category
from orders.models import Order, OrderItem
from users.models import User
from dashboard.models import DashboardActivity, DashboardSettings
from dashboard.forms import DashboardLoginForm

def dashboard_login(request):
    """Dashboard login view"""
    # Redirect if already logged in
    if request.user.is_authenticated and (request.user.is_admin() or request.user.is_staff_member()):
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = DashboardLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if user is admin or staff
                if user.is_admin() or user.is_staff_member():
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.name}!')
                    
                    # Redirect to next page if specified
                    next_page = request.GET.get('next')
                    if next_page:
                        return redirect(next_page)
                    return redirect('dashboard:home')
                else:
                    messages.error(request, 'You do not have permission to access the dashboard.')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = DashboardLoginForm()
    
    return render(request, 'dashboard/login.html', {'form': form})


@login_required
def dashboard_logout(request):
    """Dashboard logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('dashboard:login')


@login_required
def dashboard_home(request):
    """Dashboard home view with summary statistics"""
    # Date ranges
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Order statistics
    total_orders = Order.objects.count()
    recent_orders = Order.objects.order_by('-created_at')[:10]
    orders_today = Order.objects.filter(created_at__gte=today).count()
    orders_week = Order.objects.filter(created_at__gte=week_ago).count()
    orders_month = Order.objects.filter(created_at__gte=month_ago).count()
    
    # Revenue statistics
    total_revenue = Order.objects.aggregate(total=Sum('total'))['total'] or 0
    revenue_today = Order.objects.filter(created_at__gte=today).aggregate(total=Sum('total'))['total'] or 0
    revenue_week = Order.objects.filter(created_at__gte=week_ago).aggregate(total=Sum('total'))['total'] or 0
    revenue_month = Order.objects.filter(created_at__gte=month_ago).aggregate(total=Sum('total'))['total'] or 0
    
    # Product statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    top_selling_products = OrderItem.objects.values('product__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:10]
    
    # Category statistics
    total_categories = Category.objects.count()
    
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_week = User.objects.filter(created_at__gte=week_ago).count()
    new_users_month = User.objects.filter(created_at__gte=month_ago).count()
    
    # Order status breakdowns
    order_status_counts = Order.objects.values('status').annotate(count=Count('id'))
    payment_status_counts = Order.objects.values('payment_status').annotate(count=Count('id'))
    
    # Recent activities
    recent_activities = DashboardActivity.objects.all()[:15]
    
    context = {
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'orders_today': orders_today,
        'orders_week': orders_week,
        'orders_month': orders_month,
        
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
        
        'total_products': total_products,
        'active_products': active_products,
        'top_selling_products': top_selling_products,
        
        'total_categories': total_categories,
        
        'total_users': total_users,
        'active_users': active_users,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        
        'order_status_counts': order_status_counts,
        'payment_status_counts': payment_status_counts,
        
        'recent_activities': recent_activities,
    }
    
    return render(request, 'dashboard/index.html', context)


@login_required
def admin_profile(request):
    """Dashboard admin profile view"""
    user = request.user
    activities = DashboardActivity.objects.filter(user=user).order_by('-created_at')[:20]
    
    return render(request, 'dashboard/profile.html', {
        'user': user,
        'activities': activities
    })


@login_required
def dashboard_settings(request):
    """Dashboard settings view"""
    if request.method == 'POST':
        # Process settings update
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                # Update or create setting
                obj, created = DashboardSettings.objects.update_or_create(
                    key=setting_key,
                    defaults={'value': value}
                )
        
        messages.success(request, 'Settings updated successfully.')
        return redirect('dashboard:settings')
    
    # Get all dashboard settings
    settings = DashboardSettings.objects.all()
    
    return render(request, 'dashboard/settings.html', {
        'settings': settings
    })


@login_required
def activity_log(request):
    """Dashboard activity log view"""
    # Get filter parameters
    user_id = request.GET.get('user_id')
    action = request.GET.get('action')
    entity_type = request.GET.get('entity_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    activities = DashboardActivity.objects.all()
    
    # Apply filters
    if user_id:
        activities = activities.filter(user_id=user_id)
    
    if action:
        activities = activities.filter(action__icontains=action)
    
    if entity_type:
        activities = activities.filter(entity_type=entity_type)
    
    if date_from:
        activities = activities.filter(created_at__gte=date_from)
    
    if date_to:
        activities = activities.filter(created_at__lte=date_to)
    
    # Pagination
    paginator = Paginator(activities.order_by('-created_at'), 25)
    page = request.GET.get('page')
    activities = paginator.get_page(page)
    
    # Get all admin/staff users for filter dropdown
    admin_users = User.objects.filter(role__in=['ADMIN', 'STAFF'])
    
    # Get unique entity types for filter dropdown
    entity_types = DashboardActivity.objects.values_list('entity_type', flat=True).distinct()
    
    context = {
        'activities': activities,
        'admin_users': admin_users,
        'entity_types': entity_types,
        'filters': {
            'user_id': user_id,
            'action': action,
            'entity_type': entity_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'dashboard/activities.html', context)