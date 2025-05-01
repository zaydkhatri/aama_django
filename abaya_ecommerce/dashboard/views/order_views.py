# dashboard/views/order_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderItem, OrderStatusLog, Payment, Shipment, ShipmentLog
from dashboard.forms import OrderStatusForm, OrderFilterForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def order_list(request):
    """Display a list of orders with search and filter options."""
    # Initialize filter form
    filter_form = OrderFilterForm(request.GET)
    
    # Get all orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        # Search filter
        search = filter_form.cleaned_data.get('search')
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search) | 
                Q(user__email__icontains=search) |
                Q(user__name__icontains=search)
            )
        
        # Status filter
        status = filter_form.cleaned_data.get('status')
        if status:
            orders = orders.filter(status=status)
        
        # Payment status filter
        payment_status = filter_form.cleaned_data.get('payment_status')
        if payment_status:
            orders = orders.filter(payment_status=payment_status)
        
        # Date range filters
        date_from = filter_form.cleaned_data.get('date_from')
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        
        date_to = filter_form.cleaned_data.get('date_to')
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
    
    # Paginate results
    orders = paginate_queryset(request, orders, 20)
    
    return render(request, 'dashboard/orders/list.html', {
        'orders': orders,
        'filter_form': filter_form,
    })

@staff_member_required
def order_detail(request, order_number):
    """Display detailed information about an order."""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Get order items
    order_items = order.items.all().select_related('product')
    
    # Get order status logs
    status_logs = order.status_logs.all().order_by('-created_at')
    
    # Get payments
    payments = order.payments.all().order_by('-created_at')
    
    # Get shipments
    shipments = order.shipments.all().order_by('-created_at')
    
    # Prepare order status form
    status_form = OrderStatusForm(initial={'status': order.status})
    
    # Add default images to products in order items
    for item in order_items:
        item.product.default_image = item.product.get_default_image()
    
    return render(request, 'dashboard/orders/detail.html', {
        'order': order,
        'order_items': order_items,
        'status_logs': status_logs,
        'payments': payments,
        'shipments': shipments,
        'status_form': status_form,
    })

@staff_member_required
def order_update_status(request, order_number):
    """Update the status of an order."""
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        form = OrderStatusForm(request.POST)
        if form.is_valid():
            old_status = order.status
            new_status = form.cleaned_data['status']
            notes = form.cleaned_data['notes'] or f"Status changed from {old_status} to {new_status}"
            
            # Update order status
            order.status = new_status
            order.save()
            
            # Create status log
            OrderStatusLog.objects.create(
                order=order,
                status=new_status,
                notes=notes,
                created_by=request.user.email
            )
            
            # Handle special status cases
            if new_status == 'SHIPPED' and old_status != 'SHIPPED':
                # Create shipment if none exists
                if not order.shipments.exists():
                    shipment = Shipment.objects.create(
                        order=order,
                        status='PICKED_UP',
                        estimated_delivery=timezone.now() + timezone.timedelta(days=3)
                    )
                    ShipmentLog.objects.create(
                        shipment=shipment,
                        status='PICKED_UP',
                        notes=f"Order marked as shipped"
                    )
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Order',
                order.id,
                f"Updated order status from {old_status} to {new_status}",
                request
            )
            
            messages.success(request, f"Order status has been updated to {new_status}.")
            return redirect('dashboard:order_detail', order_number=order_number)
    
    # If there's a problem, redirect back to order detail
    messages.error(request, "There was a problem updating the order status.")
    return redirect('dashboard:order_detail', order_number=order_number)

@staff_member_required
def sales_report(request):
    """Generate and display sales reports."""
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get period filter (daily, weekly, monthly)
    period = request.GET.get('period', 'daily')
    
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
    
    # Query completed orders in the date range
    orders = Order.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime,
        status__in=['COMPLETED', 'DELIVERED', 'SHIPPED']
    )
    
    # Calculate total sales and order count
    sales_data = {
        'total_sales': orders.aggregate(total=Sum('total'))['total'] or 0,
        'total_orders': orders.count(),
        'average_order_value': orders.aggregate(avg=Sum('total') / Count('id'))['avg'] or 0,
    }
    
    # Get top selling products
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum(F('quantity') * F('price'))
    ).order_by('-total_quantity')[:10]
    
    # Generate time-series data based on selected period
    if period == 'daily':
        time_series = orders.values('created_at__date').annotate(
            date=F('created_at__date'),
            total=Sum('total'),
            count=Count('id')
        ).order_by('date')
    elif period == 'weekly':
        time_series = orders.extra(
            select={'week': "EXTRACT(WEEK FROM created_at)"}
        ).values('week').annotate(
            total=Sum('total'),
            count=Count('id')
        ).order_by('week')
    else:  # monthly
        time_series = orders.extra(
            select={'month': "EXTRACT(MONTH FROM created_at)"}
        ).values('month').annotate(
            total=Sum('total'),
            count=Count('id')
        ).order_by('month')
    
    return render(request, 'dashboard/reports/sales.html', {
        'sales_data': sales_data,
        'top_products': top_products,
        'time_series': list(time_series),
        'start_date': start_date,
        'end_date': end_date,
        'period': period,
    })