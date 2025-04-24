from django.shortcuts import render

# Create your views here.
# payments/views.py
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings

from .models import (
    PaymentMethod, PaymentGatewaySettings, Transaction, Refund
)
from .gateways.factory import PaymentGatewayFactory
from .forms import PaymentMethodForm, RefundForm

from orders.models import Order, Payment

@login_required
def payment_methods(request):
    """List and manage payment methods for a user."""
    methods = PaymentMethod.objects.filter(user=request.user)
    
    # Handle form submission for adding new payment method
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            method = form.save(commit=False)
            method.user = request.user
            method.save()
            messages.success(request, 'Payment method added successfully.')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'payments/payment_methods.html', {
        'methods': methods,
        'form': form
    })

@login_required
def add_payment_method(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.user = request.user
            
            # Set as default if requested or if it's the first payment method
            if form.cleaned_data.get('is_default') or not PaymentMethod.objects.filter(user=request.user).exists():
                # Set all other payment methods as non-default
                PaymentMethod.objects.filter(user=request.user).update(is_default=False)
                payment_method.is_default = True
                
            payment_method.save()
            messages.success(request, 'Payment method added successfully.')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'payments/payment_method_form.html', {
        'form': form
    })

@login_required
def edit_payment_method(request, uuid):
    payment_method = get_object_or_404(PaymentMethod, id=uuid, user=request.user)
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            # If setting as default, update other payment methods
            if form.cleaned_data.get('is_default') and not payment_method.is_default:
                PaymentMethod.objects.filter(user=request.user).update(is_default=False)
                payment_method.is_default = True
            
            form.save()
            messages.success(request, 'Payment method updated successfully.')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm(instance=payment_method)
    
    return render(request, 'payments/payment_method_form.html', {
        'form': form,
        'payment_method': payment_method
    })


@login_required
def delete_payment_method(request, uuid):
    """Delete a payment method."""
    method = get_object_or_404(PaymentMethod, id=uuid, user=request.user)
    
    if request.method == 'POST':
        method.delete()
        messages.success(request, 'Payment method deleted successfully.')
        return redirect('payment_methods')
    
    return render(request, 'payments/delete_payment_method.html', {
        'method': method
    })

@login_required
def set_default_payment_method(request, uuid):
    """Set a payment method as default."""
    method = get_object_or_404(PaymentMethod, id=uuid, user=request.user)
    
    if request.method == 'POST':
        method.is_default = True
        method.save()
        messages.success(request, 'Default payment method updated.')
        return redirect('payment_methods')
    
    return render(request, 'payments/set_default_payment_method.html', {
        'method': method
    })

@login_required
def process_payment(request, order_number):
    """Process payment for an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # If already paid, redirect to success page
    if order.payment_status == 'PAID':
        messages.info(request, 'This order has already been paid.')
        return redirect('order_success', order_number=order_number)
    
    # Get available payment gateways
    available_gateways = PaymentGatewayFactory.get_available_gateways()
    
    if not available_gateways:
        messages.error(request, 'No payment gateways are currently available. Please contact support.')
        return redirect('checkout')
    
    # Get payment method from request or use the first available gateway
    gateway_id = request.POST.get('gateway', available_gateways[0]['id'])
    
    # Generate return URLs
    success_url = request.build_absolute_uri(
        reverse('payment_success', kwargs={'order_number': order_number})
    )
    cancel_url = request.build_absolute_uri(
        reverse('payment_cancel', kwargs={'order_number': order_number})
    )
    webhook_url = request.build_absolute_uri(
        reverse('payment_webhook', kwargs={'gateway': gateway_id.lower()})
    )
    
    try:
        # Get payment gateway
        gateway = PaymentGatewayFactory.get_gateway(gateway_id)
        
        # Process payment based on gateway
        if gateway_id == 'STRIPE':
            # Create checkout session for Stripe
            result = gateway.create_checkout_session(order, success_url, cancel_url)
            
            if result['success']:
                return redirect(result['checkout_url'])
            else:
                messages.error(request, f"Payment error: {result.get('error', 'Unknown error')}")
                return redirect('checkout')
        
        elif gateway_id == 'RAZORPAY':
            # Create order for Razorpay
            result = gateway.create_order(order, success_url)
            
            if result['success']:
                return render(request, 'payments/razorpay_checkout.html', {
                    'order': order,
                    'payment_options': result['payment_options'],
                    'callback_url': success_url
                })
            else:
                messages.error(request, f"Payment error: {result.get('error', 'Unknown error')}")
                return redirect('checkout')
        
        elif gateway_id == 'PAYPAL':
            # Create PayPal payment
            result = gateway.create_payment(order, success_url, cancel_url)
            
            if result['success']:
                return redirect(result['approval_url'])
            else:
                messages.error(request, f"Payment error: {result.get('error', 'Unknown error')}")
                return redirect('checkout')
        
        else:
            messages.error(request, f"Unsupported payment gateway: {gateway_id}")
            return redirect('checkout')
    
    except Exception as e:
        messages.error(request, f"Payment processing error: {str(e)}")
        return redirect('checkout')

@login_required
def payment_success(request, order_number):
    """Handle successful payment completion."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Process gateway-specific parameters
    gateway_id = request.GET.get('gateway', 'STRIPE')
    
    try:
        # Verify payment based on gateway
        if gateway_id == 'STRIPE':
            # Stripe handles this through webhooks, just show success page
            pass
        
        elif gateway_id == 'RAZORPAY':
            # Verify Razorpay payment
            payment_id = request.GET.get('razorpay_payment_id')
            order_id = request.GET.get('razorpay_order_id')
            signature = request.GET.get('razorpay_signature')
            
            if payment_id and order_id and signature:
                gateway = PaymentGatewayFactory.get_gateway('RAZORPAY')
                result = gateway.verify_payment(payment_id, order_id, signature)
                
                if not result['success']:
                    messages.error(request, f"Payment verification failed: {result.get('error', 'Unknown error')}")
                    return redirect('checkout')
        
        elif gateway_id == 'PAYPAL':
            # Verify PayPal payment
            payment_id = request.GET.get('paymentId')
            payer_id = request.GET.get('PayerID')
            
            if payment_id and payer_id:
                gateway = PaymentGatewayFactory.get_gateway('PAYPAL')
                result = gateway.execute_payment(payment_id, payer_id)
                
                if not result['success']:
                    messages.error(request, f"Payment execution failed: {result.get('error', 'Unknown error')}")
                    return redirect('checkout')
        
        # Get transaction details
        transaction = Transaction.objects.filter(
            order=order,
            status__in=['COMPLETED', 'PROCESSING']
        ).first()
        
        # Update order status if needed
        if transaction and order.payment_status != 'PAID':
            # Get related payment
            payment = order.payments.first()
            if payment:
                payment.status = 'PAID'
                payment.transaction_id = transaction.gateway_transaction_id
                payment.save()
            
            order.payment_status = 'PAID'
            order.status = 'PROCESSING'
            order.save()
            
            from orders.models import OrderStatusLog
            OrderStatusLog.objects.create(
                order=order,
                status='PROCESSING',
                notes='Payment completed successfully'
            )
        
        messages.success(request, 'Payment completed successfully! Your order is now being processed.')
        return redirect('order_detail', order_number=order_number)
    
    except Exception as e:
        messages.error(request, f"Error processing payment confirmation: {str(e)}")
        return redirect('order_detail', order_number=order_number)

@login_required
def payment_cancel(request, order_number):
    """Handle canceled payment."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    messages.warning(request, 'Payment was canceled. Please try again or choose a different payment method.')
    return redirect('order_detail', order_number=order_number)

@csrf_exempt
def payment_webhook(request, gateway):
    """Handle payment gateway webhooks."""
    if request.method != 'POST':
        return HttpResponse(status=405)  # Method Not Allowed
    
    try:
        # Process webhook based on gateway
        if gateway.upper() == 'STRIPE':
            stripe_gateway = PaymentGatewayFactory.get_gateway('STRIPE')
            return stripe_gateway.process_webhook(request)
        
        elif gateway.upper() == 'RAZORPAY':
            razorpay_gateway = PaymentGatewayFactory.get_gateway('RAZORPAY')
            return razorpay_gateway.process_webhook(request)
        
        elif gateway.upper() == 'PAYPAL':
            paypal_gateway = PaymentGatewayFactory.get_gateway('PAYPAL')
            return paypal_gateway.process_webhook(request)
        
        else:
            return HttpResponse(status=400)  # Bad Request
    
    except Exception as e:
        return HttpResponse(content=str(e), status=500)  # Internal Server Error

@login_required
def payment_options(request, order_number):
    """Display payment options for an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # If already paid, redirect to success page
    if order.payment_status == 'PAID':
        messages.info(request, 'This order has already been paid.')
        return redirect('order_success', order_number=order_number)
    
    # Get available payment gateways
    available_gateways = PaymentGatewayFactory.get_available_gateways()
    
    # Get saved payment methods for the user
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    return render(request, 'payments/payment_options.html', {
        'order': order,
        'available_gateways': available_gateways,
        'payment_methods': payment_methods
    })

@login_required
def refund_request(request, order_number):
    """Request a refund for an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order is eligible for refund
    if order.payment_status != 'PAID' or order.status in ['REFUNDED', 'CANCELLED']:
        messages.error(request, 'This order is not eligible for a refund.')
        return redirect('order_detail', order_number=order_number)
    
    # Get transaction for the order
    transaction = Transaction.objects.filter(
        order=order,
        status='COMPLETED'
    ).first()
    
    if not transaction:
        messages.error(request, 'No completed payment found for this order.')
        return redirect('order_detail', order_number=order_number)
    
    if request.method == 'POST':
        form = RefundForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            
            try:
                # Process refund based on gateway
                gateway = PaymentGatewayFactory.get_gateway(transaction.gateway)
                result = gateway.create_refund(transaction, None, reason)  # Full refund
                
                if result['success']:
                    messages.success(request, 'Refund request submitted successfully.')
                    return redirect('order_detail', order_number=order_number)
                else:
                    messages.error(request, f"Refund request failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                messages.error(request, f"Error processing refund: {str(e)}")
    else:
        form = RefundForm()
    
    return render(request, 'payments/refund_request.html', {
        'order': order,
        'form': form
    })

@login_required
def transaction_history(request):
    """Display transaction history for the user."""
    transactions = Transaction.objects.filter(
        order__user=request.user
    ).select_related('order').order_by('-created_at')
    
    return render(request, 'payments/transaction_history.html', {
        'transactions': transactions
    })

@login_required
def transaction_detail(request, uuid):
    """Display details of a transaction."""
    transaction = get_object_or_404(
        Transaction,
        id=uuid,
        order__user=request.user
    )
    
    # Get refunds for the transaction
    refunds = Refund.objects.filter(transaction=transaction)
    
    return render(request, 'payments/transaction_detail.html', {
        'transaction': transaction,
        'refunds': refunds
    })