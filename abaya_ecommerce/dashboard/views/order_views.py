from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.template.loader import render_to_string
import csv
import datetime

from orders.models import (
    Order, OrderItem, OrderStatusLog, Return, ReturnItem, ReturnLog, 
    Shipment, ShipmentLog, Payment
)
from dashboard.forms import OrderEditForm, OrderStatusForm, ReturnStatusForm
from dashboard.models import DashboardActivity


@login_required
def order_list(request):
    """List all orders with search and filter functionality"""
    # Get filter parameters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    orders = Order.objects.all().select_related('user')
    
    # Apply filters
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) | 
            Q(user__email__icontains=search) | 
            Q(user__name__icontains=search) | 
            Q(user__phone__icontains=search)
        )
    
    if status:
        orders = orders.filter(status=status)
    
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    if date_from:
        try:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    
    # Order by created date (newest first)
    orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    # Calculate totals
    all_orders = Order.objects.all()
    total_orders = all_orders.count()
    total_revenue = all_orders.aggregate(total=Sum('total'))['total'] or 0
    
    pending_orders = all_orders.filter(status='PENDING').count()
    processing_orders = all_orders.filter(status='PROCESSING').count()
    shipped_orders = all_orders.filter(status='SHIPPED').count()
    delivered_orders = all_orders.filter(status='DELIVERED').count()
    cancelled_orders = all_orders.filter(status='CANCELLED').count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        
        'status_choices': Order.ORDER_STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        
        'filters': {
            'search': search,
            'status': status,
            'payment_status': payment_status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    # Export functionality
    if request.GET.get('export') == 'csv':
        return export_orders_csv(request, all_orders)
    
    return render(request, 'dashboard/orders/list.html', context)


@login_required
def order_detail(request, pk):
    """Display order details"""
    order = get_object_or_404(Order, pk=pk)
    
    # Get order items with product details
    order_items = order.items.all().select_related('product')
    
    # Get status history
    status_logs = OrderStatusLog.objects.filter(order=order).order_by('-created_at')
    
    # Get payment history
    payments = Payment.objects.filter(order=order).order_by('-created_at')
    
    # Get shipments
    shipments = Shipment.objects.filter(order=order).order_by('-created_at')
    
    # Get related returns
    returns = Return.objects.filter(order=order).order_by('-created_at')
    
    context = {
        'order': order,
        'order_items': order_items,
        'status_logs': status_logs,
        'payments': payments,
        'shipments': shipments,
        'returns': returns,
        'status_form': OrderStatusForm(initial={'status': order.status}),
    }
    
    return render(request, 'dashboard/orders/detail.html', context)


@login_required
def order_edit(request, pk):
    """Edit order details"""
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        form = OrderEditForm(request.POST, instance=order)
        if form.is_valid():
            # Track changes for activity log
            changed_fields = []
            for field in form.changed_data:
                orig_value = getattr(order, field) if hasattr(order, field) else None
                changed_fields.append({
                    'field': field,
                    'old': str(orig_value),
                    'new': str(form.cleaned_data.get(field))
                })
            
            # Update status log if status changed
            if 'status' in form.changed_data:
                OrderStatusLog.objects.create(
                    order=order,
                    status=form.cleaned_data['status'],
                    notes=f"Status changed from {order.status} to {form.cleaned_data['status']} by admin",
                    created_by=request.user.email
                )
            
            # Save the form
            updated_order = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated order',
                entity_type='Order',
                entity_id=str(order.id),
                details={
                    'order_number': order.order_number,
                    'changes': changed_fields
                }
            )
            
            messages.success(request, f'Order {order.order_number} updated successfully.')
            return redirect('dashboard:order_detail', pk=order.id)
    else:
        form = OrderEditForm(instance=order)
    
    context = {
        'form': form,
        'order': order,
        'title': f'Edit Order: {order.order_number}'
    }
    
    return render(request, 'dashboard/orders/edit.html', context)


@login_required
def update_order_status(request, pk):
    """Update order status"""
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        form = OrderStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            notes = form.cleaned_data['notes']
            
            # Don't update if status hasn't changed
            if new_status == order.status:
                messages.info(request, f'Order status is already {order.get_status_display()}.')
                return redirect('dashboard:order_detail', pk=order.id)
            
            # Update order status
            old_status = order.status
            order.status = new_status
            order.save(update_fields=['status'])
            
            # Create status log
            OrderStatusLog.objects.create(
                order=order,
                status=new_status,
                notes=notes or f"Status changed from {old_status} to {new_status} by admin",
                created_by=request.user.email
            )
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated order status',
                entity_type='Order',
                entity_id=str(order.id),
                details={
                    'order_number': order.order_number,
                    'old_status': old_status,
                    'new_status': new_status,
                    'notes': notes
                }
            )
            
            # Create shipment if status changed to SHIPPED
            if new_status == 'SHIPPED' and old_status != 'SHIPPED':
                # Check if a shipment already exists
                if not Shipment.objects.filter(order=order).exists():
                    shipment = Shipment.objects.create(
                        order=order,
                        status='IN_TRANSIT',
                        estimated_delivery=timezone.now() + datetime.timedelta(days=5)
                    )
                    
                    # Create shipment log
                    ShipmentLog.objects.create(
                        shipment=shipment,
                        status='IN_TRANSIT',
                        notes="Shipment created automatically when order marked as shipped"
                    )
            
            messages.success(request, f'Order status updated to {order.get_status_display()}.')
            
            # Send status update email
            # This would be handled by signals in orders/signals.py
            
            return redirect('dashboard:order_detail', pk=order.id)
    
    messages.error(request, 'Invalid form submission.')
    return redirect('dashboard:order_detail', pk=order.id)


@login_required
def order_invoice(request, pk):
    """Generate order invoice"""
    order = get_object_or_404(Order, pk=pk)
    
    context = {
        'order': order,
        'order_items': order.items.all().select_related('product'),
        'company_name': 'Abaya Elegance',
        'company_address': '123 Fashion Street, Dubai, UAE',
        'company_email': 'support@abayaelegance.com',
        'company_phone': '+971 123 4567'
    }
    
    # If it's a PDF request
    if request.GET.get('format') == 'pdf':
        # Generate PDF using a library like WeasyPrint or xhtml2pdf
        # For simplicity, we'll return HTML for this example
        html = render_to_string('dashboard/orders/invoice_pdf.html', context)
        
        # In a real implementation, convert HTML to PDF
        # pdf = generate_pdf(html)
        # response = HttpResponse(pdf, content_type='application/pdf')
        # response['Content-Disposition'] = f'attachment; filename="Invoice-{order.order_number}.pdf"'
        # return response
        
        # For now, return HTML with a download hint
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="Invoice-{order.order_number}.html"'
        return response
    
    # Regular HTML view
    return render(request, 'dashboard/orders/invoice.html', context)


@login_required
def return_list(request):
    """List all returns with search and filter functionality"""
    # Get filter parameters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    refund_status = request.GET.get('refund_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    returns = Return.objects.all().select_related('order', 'user')
    
    # Apply filters
    if search:
        returns = returns.filter(
            Q(return_number__icontains=search) | 
            Q(order__order_number__icontains=search) | 
            Q(user__email__icontains=search) | 
            Q(user__name__icontains=search)
        )
    
    if status:
        returns = returns.filter(status=status)
    
    if refund_status:
        returns = returns.filter(refund_status=refund_status)
    
    if date_from:
        try:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            returns = returns.filter(created_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            returns = returns.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    
    # Order by created date (newest first)
    returns = returns.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(returns, 20)
    page = request.GET.get('page')
    try:
        returns = paginator.page(page)
    except PageNotAnInteger:
        returns = paginator.page(1)
    except EmptyPage:
        returns = paginator.page(paginator.num_pages)
    
    context = {
        'returns': returns,
        'status_choices': Return.RETURN_STATUS_CHOICES,
        'refund_status_choices': Return.REFUND_STATUS_CHOICES,
        'filters': {
            'search': search,
            'status': status,
            'refund_status': refund_status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'dashboard/orders/return_list.html', context)


@login_required
def return_detail(request, pk):
    """Display return details"""
    return_obj = get_object_or_404(Return, pk=pk)
    
    # Get return items with product details
    return_items = return_obj.items.all().select_related('product')
    
    # Get status history
    status_logs = ReturnLog.objects.filter(return_request=return_obj).order_by('-created_at')
    
    context = {
        'return': return_obj,
        'return_items': return_items,
        'status_logs': status_logs,
        'status_form': ReturnStatusForm(initial={
            'status': return_obj.status,
            'refund_status': return_obj.refund_status
        }),
    }
    
    return render(request, 'dashboard/orders/return_detail.html', context)


@login_required
def update_return_status(request, pk):
    """Update return status"""
    return_obj = get_object_or_404(Return, pk=pk)
    
    if request.method == 'POST':
        form = ReturnStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            new_refund_status = form.cleaned_data['refund_status']
            notes = form.cleaned_data['notes']
            
            # Check if anything changed
            status_changed = new_status != return_obj.status
            refund_status_changed = new_refund_status != return_obj.refund_status
            
            if not status_changed and not refund_status_changed:
                messages.info(request, 'No status changes were made.')
                return redirect('dashboard:return_detail', pk=return_obj.id)
            
            # Update return status
            old_status = return_obj.status
            old_refund_status = return_obj.refund_status
            
            return_obj.status = new_status
            return_obj.refund_status = new_refund_status
            return_obj.save(update_fields=['status', 'refund_status'])
            
            # Create status log
            log_notes = notes or "Status updated by admin"
            if status_changed:
                log_notes += f" - Status changed from {old_status} to {new_status}"
            if refund_status_changed:
                log_notes += f" - Refund status changed from {old_refund_status} to {new_refund_status}"
                
            ReturnLog.objects.create(
                return_request=return_obj,
                status=new_status,
                notes=log_notes,
                created_by=request.user.email
            )
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated return status',
                entity_type='Return',
                entity_id=str(return_obj.id),
                details={
                    'return_number': return_obj.return_number,
                    'old_status': old_status,
                    'new_status': new_status,
                    'old_refund_status': old_refund_status,
                    'new_refund_status': new_refund_status,
                    'notes': notes
                }
            )
            
            # Update order if needed
            order = return_obj.order
            if new_status == 'COMPLETED' and new_refund_status == 'COMPLETED':
                # Mark order as refunded
                if order.status not in ['REFUNDED', 'CANCELLED']:
                    order.status = 'REFUNDED'
                    order.payment_status = 'REFUNDED'
                    order.save(update_fields=['status', 'payment_status'])
                    
                    # Create order status log
                    OrderStatusLog.objects.create(
                        order=order,
                        status='REFUNDED',
                        notes=f"Order marked as refunded due to completed return {return_obj.return_number}",
                        created_by=request.user.email
                    )
            
            messages.success(request, 'Return status updated successfully.')
            return redirect('dashboard:return_detail', pk=return_obj.id)
    
    messages.error(request, 'Invalid form submission.')
    return redirect('dashboard:return_detail', pk=return_obj.id)


def export_orders_csv(request, orders):
    """Export orders as CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    
    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Email', 'Phone', 
        'Status', 'Payment Status', 'Subtotal', 'Shipping', 
        'Tax', 'Discount', 'Total', 'Items'
    ])
    
    # Write data rows
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.user.name,
            order.user.email,
            order.user.phone or 'N/A',
            order.get_status_display(),
            order.get_payment_status_display(),
            order.subtotal,
            order.shipping_amount,
            order.tax_amount,
            order.discount_amount,
            order.total,
            order.items.count()
        ])
    
    return response