from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Sum, Avg, F, Q, DateTimeField
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
import csv
import datetime
import json
from decimal import Decimal

from orders.models import Order, OrderItem
from products.models import Product, Category
from users.models import User
from dashboard.forms import DateRangeFilterForm


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


@login_required
def sales_report(request):
    """Display sales reports and analytics"""
    # Get date range from form or use defaults
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    
    # Initialize form with current values
    form = DateRangeFilterForm(initial={
        'start_date': start_date,
        'end_date': end_date
    })
    
    # Filter orders by date range
    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Calculate sales metrics
    total_sales = orders.aggregate(total=Sum('total'))['total'] or 0
    total_orders = orders.count()
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Sales by status
    sales_by_status = orders.values('status').annotate(
        count=Count('id'),
        total=Sum('total')
    ).order_by('status')
    
    # Sales by payment method
    sales_by_payment = orders.filter(payments__isnull=False).values(
        'payments__payment_method'
    ).annotate(
        count=Count('id', distinct=True),
        total=Sum('total')
    ).order_by('payments__payment_method')
    
    # Top selling products
    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values(
        'product__id', 'product__name', 'product__sku'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-quantity_sold')[:10]
    
    # Top categories
    top_categories = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values(
        'product__categories__id', 'product__categories__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-revenue')[:10]
    
    # Prepare context
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'sales_by_status': sales_by_status,
        'sales_by_payment': sales_by_payment,
        'top_products': top_products,
        'top_categories': top_categories
    }
    
    # Export if requested
    if request.GET.get('export') == 'csv':
        return export_sales_report(request, orders, start_date, end_date)
    
    return render(request, 'dashboard/reports/sales.html', context)


@login_required
def product_report(request):
    """Display product performance reports"""
    # Get date range from form or use defaults
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    
    # Initialize form with current values
    form = DateRangeFilterForm(initial={
        'start_date': start_date,
        'end_date': end_date
    })
    
    # Filter order items by date range
    order_items = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    )
    
    # Product performance metrics
    product_stats = order_items.values(
        'product__id', 'product__name', 'product__sku'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity')),
        order_count=Count('order', distinct=True)
    ).order_by('-revenue')
    
    # Best selling products
    best_selling_products = order_items.values(
        'product__id', 'product__name', 'product__sku'
    ).annotate(
        quantity_sold=Sum('quantity')
    ).order_by('-quantity_sold')[:10]
    
    # Most profitable products
    most_profitable_products = order_items.values(
        'product__id', 'product__name', 'product__sku'
    ).annotate(
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-revenue')[:10]
    
    # Category performance
    category_stats = order_items.values(
        'product__categories__id', 'product__categories__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity')),
        order_count=Count('order', distinct=True)
    ).order_by('-revenue')
    
    # Low stock products
    low_stock_products = Product.objects.filter(
        is_active=True
    ).order_by('id')[:10]  # This would typically be filtered by stock level
    
    # Prepare context
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'product_stats': product_stats[:20],  # Limit to top 20
        'best_selling_products': best_selling_products,
        'most_profitable_products': most_profitable_products,
        'category_stats': category_stats[:10],  # Limit to top 10
        'low_stock_products': low_stock_products
    }
    
    # Export if requested
    if request.GET.get('export') == 'csv':
        return export_product_report(request, product_stats, start_date, end_date)
    
    return render(request, 'dashboard/reports/products.html', context)


@login_required
def customer_report(request):
    """Display customer analytics and reports"""
    # Get date range from form or use defaults
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - datetime.timedelta(days=90)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        start_date = today - datetime.timedelta(days=90)
        end_date = today
    
    # Initialize form with current values
    form = DateRangeFilterForm(initial={
        'start_date': start_date,
        'end_date': end_date
    })
    
    # Customer metrics
    total_customers = User.objects.filter(role='CUSTOMER').count()
    new_customers = User.objects.filter(
        role='CUSTOMER',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()
    
    # Active customers (placed an order in the date range)
    active_customers = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values('user_id').distinct().count()
    
    # Top customers by order count
    top_customers_by_orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values(
        'user__id', 'user__name', 'user__email'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total')
    ).order_by('-order_count')[:10]
    
    # Top customers by revenue
    top_customers_by_revenue = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values(
        'user__id', 'user__name', 'user__email'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total')
    ).order_by('-total_spent')[:10]
    
    # Customer retention metrics
    repeat_customers = User.objects.filter(
        orders__created_at__date__gte=start_date,
        orders__created_at__date__lte=end_date
    ).annotate(
        order_count=Count('orders')
    ).filter(order_count__gt=1).count()
    
    # Average order value per customer
    customer_aov = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values('user_id').annotate(
        avg_order=Avg('total')
    ).aggregate(overall_avg=Avg('avg_order'))['overall_avg'] or 0
    
    # Prepare context
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'total_customers': total_customers,
        'new_customers': new_customers,
        'active_customers': active_customers,
        'repeat_customers': repeat_customers,
        'customer_aov': customer_aov,
        'top_customers_by_orders': top_customers_by_orders,
        'top_customers_by_revenue': top_customers_by_revenue
    }
    
    # Export if requested
    if request.GET.get('export') == 'csv':
        return export_customer_report(request, 
                                     top_customers_by_revenue, 
                                     start_date, 
                                     end_date)
    
    return render(request, 'dashboard/reports/customers.html', context)


@login_required
def export_sales_report(request, orders=None, start_date=None, end_date=None):
    """Export sales report as CSV"""
    # If orders is not provided, get it from the request parameters
    if orders is None:
        # Get date range
        try:
            start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Use defaults on error
            today = timezone.now().date()
            start_date = today - datetime.timedelta(days=30)
            end_date = today
        
        # Filter orders
        orders = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
    
    # Create HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_to_{end_date}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Status', 'Payment Status',
        'Subtotal', 'Shipping', 'Tax', 'Discount', 'Total'
    ])
    
    # Write data rows
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.user.email,
            order.get_status_display(),
            order.get_payment_status_display(),
            order.subtotal,
            order.shipping_amount,
            order.tax_amount,
            order.discount_amount,
            order.total
        ])
    
    return response


@login_required
def export_product_report(request, product_stats=None, start_date=None, end_date=None):
    """Export product report as CSV"""
    # If product_stats is not provided, get it from the database
    if product_stats is None:
        # Get date range
        try:
            start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Use defaults on error
            today = timezone.now().date()
            start_date = today - datetime.timedelta(days=30)
            end_date = today
        
        # Get product stats
        product_stats = OrderItem.objects.filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum(F('price') * F('quantity')),
            order_count=Count('order', distinct=True)
        ).order_by('-revenue')
    
    # Create HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="product_report_{start_date}_to_{end_date}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'Product ID', 'Product Name', 'SKU', 'Quantity Sold', 'Revenue', 'Order Count'
    ])
    
    # Write data rows
    for product in product_stats:
        writer.writerow([
            product['product__id'],
            product['product__name'],
            product['product__sku'],
            product['quantity_sold'],
            product['revenue'],
            product['order_count']
        ])
    
    return response


@login_required
def export_customer_report(request, customer_stats=None, start_date=None, end_date=None):
    """Export customer report as CSV"""
    # If customer_stats is not provided, get it from the database
    if customer_stats is None:
        # Get date range
        try:
            start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Use defaults on error
            today = timezone.now().date()
            start_date = today - datetime.timedelta(days=90)
            end_date = today
        
        # Get customer stats
        customer_stats = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values(
            'user__id', 'user__name', 'user__email'
        ).annotate(
            order_count=Count('id'),
            total_spent=Sum('total')
        ).order_by('-total_spent')
    
    # Create HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="customer_report_{start_date}_to_{end_date}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'Customer ID', 'Name', 'Email', 'Orders', 'Total Spent', 'Average Order Value'
    ])
    
    # Write data rows
    for customer in customer_stats:
        # Calculate average order value
        aov = customer['total_spent'] / customer['order_count'] if customer['order_count'] > 0 else 0
        
        writer.writerow([
            customer['user__id'],
            customer['user__name'],
            customer['user__email'],
            customer['order_count'],
            customer['total_spent'],
            aov
        ])
    
    return response


# AJAX chart data endpoints

@login_required
def orders_chart_data(request):
    """Get order data for charts"""
    # Get date range
    try:
        start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    
    # Determine appropriate grouping based on date range
    date_diff = (end_date - start_date).days
    
    if date_diff <= 31:
        # Group by day for a month or less
        trunc_func = TruncDate('created_at')
        date_format = '%Y-%m-%d'
    elif date_diff <= 90:
        # Group by week for a quarter or less
        trunc_func = TruncWeek('created_at')
        date_format = 'Week %W, %Y'
    else:
        # Group by month for longer periods
        trunc_func = TruncMonth('created_at')
        date_format = '%b %Y'
    
    # Get orders by date
    orders_by_date = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).annotate(
        date=trunc_func
    ).values('date').annotate(
        count=Count('id'),
        total=Sum('total')
    ).order_by('date')
    
    # Format the data for the chart
    labels = []
    order_counts = []
    order_totals = []
    
    for entry in orders_by_date:
        if isinstance(entry['date'], datetime.datetime):
            labels.append(entry['date'].strftime(date_format))
        else:
            # Handle case where the date might be a string or date
            labels.append(str(entry['date']))
        
        order_counts.append(entry['count'])
        order_totals.append(float(entry['total']))
    
    # Get orders by status
    orders_by_status = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    status_labels = [o.get_status_display() for o in orders_by_status]
    status_counts = [o['count'] for o in orders_by_status]
    
    data = {
        'time_series': {
            'labels': labels,
            'order_counts': order_counts,
            'order_totals': order_totals
        },
        'status_breakdown': {
            'labels': status_labels,
            'counts': status_counts
        }
    }
    
    return JsonResponse(data)


@login_required
def sales_chart_data(request):
    """Get sales data for charts"""
    # Get date range
    try:
        start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    
    # Determine appropriate grouping based on date range
    date_diff = (end_date - start_date).days
    
    if date_diff <= 31:
        # Group by day for a month or less
        trunc_func = TruncDate('created_at')
        date_format = '%Y-%m-%d'
    elif date_diff <= 90:
        # Group by week for a quarter or less
        trunc_func = TruncWeek('created_at')
        date_format = 'Week %W, %Y'
    else:
        # Group by month for longer periods
        trunc_func = TruncMonth('created_at')
        date_format = '%b %Y'
    
    # Get sales by date
    sales_by_date = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).annotate(
        date=trunc_func
    ).values('date').annotate(
        total=Sum('total'),
        subtotal=Sum('subtotal'),
        shipping=Sum('shipping_amount'),
        tax=Sum('tax_amount'),
        discount=Sum('discount_amount')
    ).order_by('date')
    
    # Format the data for the chart
    labels = []
    totals = []
    subtotals = []
    shipping = []
    tax = []
    discount = []
    
    for entry in sales_by_date:
        if isinstance(entry['date'], datetime.datetime):
            labels.append(entry['date'].strftime(date_format))
        else:
            # Handle case where the date might be a string or date
            labels.append(str(entry['date']))
        
        totals.append(float(entry['total']))
        subtotals.append(float(entry['subtotal']))
        shipping.append(float(entry['shipping']))
        tax.append(float(entry['tax']))
        discount.append(float(entry['discount']))
    
    # Get sales by payment method
    sales_by_payment = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        payments__isnull=False
    ).values(
        'payments__payment_method'
    ).annotate(
        total=Sum('total')
    ).order_by('payments__payment_method')
    
    payment_labels = []
    payment_totals = []
    
    for entry in sales_by_payment:
        method = entry['payments__payment_method']
        # Get display name for payment method
        for choice in Order.get_payment_method_choices():
            if choice[0] == method:
                method = choice[1]
                break
        
        payment_labels.append(method)
        payment_totals.append(float(entry['total']))
    
    data = {
        'time_series': {
            'labels': labels,
            'totals': totals,
            'subtotals': subtotals,
            'shipping': shipping,
            'tax': tax,
            'discount': discount
        },
        'payment_breakdown': {
            'labels': payment_labels,
            'totals': payment_totals
        }
    }
    
    return JsonResponse(data)


@login_required
def products_chart_data(request):
    """Get product data for charts"""
    # Get date range
    try:
        start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Use defaults on error
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    
    # Top products by quantity
    top_products_qty = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values(
        'product__name'
    ).annotate(
        quantity=Sum('quantity')
    ).order_by('-quantity')[:10]
    
    product_labels_qty = [p['product__name'] for p in top_products_qty]
    product_quantities = [p['quantity'] for p in top_products_qty]
    
    # Top products by revenue
    top_products_rev = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values(
        'product__name'
    ).annotate(
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-revenue')[:10]
    
    product_labels_rev = [p['product__name'] for p in top_products_rev]
    product_revenues = [float(p['revenue']) for p in top_products_rev]
    
    # Top categories
    top_categories = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date,
        product__categories__isnull=False
    ).values(
        'product__categories__name'
    ).annotate(
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-revenue')[:10]
    
    category_labels = [c['product__categories__name'] for c in top_categories]
    category_revenues = [float(c['revenue']) for c in top_categories]
    
    data = {
        'top_products_quantity': {
            'labels': product_labels_qty,
            'quantities': product_quantities
        },
        'top_products_revenue': {
            'labels': product_labels_rev,
            'revenues': product_revenues
        },
        'top_categories': {
            'labels': category_labels,
            'revenues': category_revenues
        }
    }
    
    return JsonResponse(data)