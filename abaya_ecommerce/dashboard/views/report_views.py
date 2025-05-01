# dashboard/views/report_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from django.http import JsonResponse

from orders.models import Order, OrderItem
from products.models import Product, Category, ProductView
from users.models import User
from dashboard.utils import staff_member_required

@staff_member_required
def product_report(request):
    """Generate and display product performance reports."""
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    try:
        start_datetime = timezone.datetime.strptime(start_date, '%Y-%m-%d')
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.datetime.strptime(end_date, '%Y-%m-%d')
        end_datetime = timezone.make_aware(end_datetime.replace(hour=23, minute=59, second=59))
    except (ValueError, TypeError):
        # Handle invalid dates
        start_datetime = timezone.now() - timezone.timedelta(days=30)
        end_datetime = timezone.now()
    
    # Get category filter
    category_id = request.GET.get('category')
    
    # Base query for order items in the date range
    order_items = OrderItem.objects.filter(
        order__created_at__gte=start_datetime,
        order__created_at__lte=end_datetime,
        order__status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
    )
    
    # Apply category filter if provided
    if category_id:
        order_items = order_items.filter(product__categories__id=category_id)
    
    # Get top selling products
    top_selling_products = order_items.values(
        'product_id', 'product__name', 'product__sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price')),
        order_count=Count('order', distinct=True)
    ).order_by('-total_quantity')[:20]
    
    # Get products with the highest revenue
    highest_revenue_products = order_items.values(
        'product_id', 'product__name', 'product__sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price')),
        order_count=Count('order', distinct=True)
    ).order_by('-total_revenue')[:20]
    
    # Get most viewed products
    most_viewed_products = ProductView.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    ).values(
        'product_id', 'product__name', 'product__sku'
    ).annotate(
        view_count=Count('id')
    ).order_by('-view_count')[:20]
    
    # Get categories data
    categories_data = order_items.values(
        'product__categories__id', 'product__categories__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price')),
        product_count=Count('product_id', distinct=True)
    ).order_by('-total_revenue')
    
    # Get all categories for filter dropdown
    all_categories = Category.objects.filter(is_active=True)
    
    return render(request, 'dashboard/reports/products.html', {
        'top_selling_products': top_selling_products,
        'highest_revenue_products': highest_revenue_products,
        'most_viewed_products': most_viewed_products,
        'categories_data': categories_data,
        'all_categories': all_categories,
        'start_date': start_date,
        'end_date': end_date,
        'selected_category': category_id,
    })

@staff_member_required
def customer_report(request):
    """Generate and display customer reports."""
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    try:
        start_datetime = timezone.datetime.strptime(start_date, '%Y-%m-%d')
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.datetime.strptime(end_date, '%Y-%m-%d')
        end_datetime = timezone.make_aware(end_datetime.replace(hour=23, minute=59, second=59))
    except (ValueError, TypeError):
        # Handle invalid dates
        start_datetime = timezone.now() - timezone.timedelta(days=30)
        end_datetime = timezone.now()
    
    # Get orders in the date range
    orders = Order.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    )
    
    # Get top customers by order count
    top_customers_by_orders = orders.values(
        'user_id', 'user__email', 'user__name'
    ).annotate(
        order_count=Count('id'),
        total_spend=Sum('total')
    ).order_by('-order_count')[:20]
    
    # Get top customers by total spend
    top_customers_by_spend = orders.values(
        'user_id', 'user__email', 'user__name'
    ).annotate(
        order_count=Count('id'),
        total_spend=Sum('total')
    ).order_by('-total_spend')[:20]
    
    # Get new customers trend
    if request.GET.get('period') == 'monthly':
        new_customers_trend = User.objects.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
    elif request.GET.get('period') == 'weekly':
        new_customers_trend = User.objects.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('week')
    else:  # daily
        new_customers_trend = User.objects.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
    
    # Calculate overall statistics
    stats = {
        'total_customers': User.objects.filter(created_at__lte=end_datetime).count(),
        'new_customers': User.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime).count(),
        'active_customers': orders.values('user_id').distinct().count(),
        'average_order_value': orders.aggregate(avg=Avg('total'))['avg'] or 0,
    }
    
    return render(request, 'dashboard/reports/customers.html', {
        'top_customers_by_orders': top_customers_by_orders,
        'top_customers_by_spend': top_customers_by_spend,
        'new_customers_trend': list(new_customers_trend),
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'period': request.GET.get('period', 'daily'),
    })