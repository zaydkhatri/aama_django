# dashboard/views/dashboard_views.py
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay
from django.utils import timezone

from orders.models import Order
from products.models import Product, ProductView
from users.models import User
from dashboard.utils import staff_member_required, log_admin_activity

@staff_member_required
def dashboard_home(request):
    """Display the main dashboard with key metrics and charts."""
    # Get date range for filtering (default to last 30 days)
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)
    
    # Sales metrics
    sales_metrics = {
        'total_revenue': Order.objects.filter(
            created_at__gte=start_date,
            status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
        ).aggregate(total=Sum('total'))['total'] or 0,
        
        'order_count': Order.objects.filter(
            created_at__gte=start_date
        ).count(),
        
        'average_order_value': Order.objects.filter(
            created_at__gte=start_date,
            status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
        ).aggregate(avg=Avg('total'))['avg'] or 0,
        
        'pending_orders': Order.objects.filter(
            status='PENDING'
        ).count(),
    }
    
    # Sales trend (daily)
    sales_trend = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        revenue=Sum('total'),
        count=Count('id')
    ).order_by('day')
    
    # Customer metrics
    customer_metrics = {
        'total_customers': User.objects.count(),
        
        'new_customers': User.objects.filter(
            created_at__gte=start_date
        ).count(),
        
        'active_customers': Order.objects.filter(
            created_at__gte=start_date
        ).values('user_id').distinct().count(),
    }
    
    # Product metrics
    product_metrics = {
        'total_products': Product.objects.filter(
            is_active=True
        ).count(),
        
        'out_of_stock': 0,  # Would normally count products with inventory = 0
        
        'product_views': ProductView.objects.filter(
            created_at__gte=start_date
        ).count(),
    }
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    # Top selling products
    top_products = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
    ).values(
        'items__product__id',
        'items__product__name',
        'items__product__sku'
    ).annotate(
        quantity=Sum('items__quantity'),
        revenue=Sum('items__total')
    ).order_by('-quantity')[:5]
    
    # Log admin visit to dashboard
    log_admin_activity(
        request.user,
        'OTHER',
        'Dashboard',
        None,
        "Viewed admin dashboard",
        request
    )
    
    return render(request, 'dashboard/home.html', {
        'sales_metrics': sales_metrics,
        'customer_metrics': customer_metrics,
        'product_metrics': product_metrics,
        'sales_trend': list(sales_trend),
        'recent_orders': recent_orders,
        'top_products': top_products,
        'days': days,
    })