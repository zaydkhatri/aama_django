from django.shortcuts import render

# Create your views here.
# orders/views.py
import uuid
import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

from .models import (
    Order, OrderItem, OrderStatusLog, Coupon, Payment, Shipment,
    Return, ReturnItem, ReturnLog
)
from .forms import (
    CheckoutForm, CouponForm, ReturnForm, ReturnItemForm, OrderFilterForm
)
from carts.models import Cart, CartItem, GuestCart, GuestCartItem
from products.models import Product, Currency
from users.models import User, Address

def generate_order_number():
    """Generate a unique order number."""
    prefix = timezone.now().strftime('%Y%m')
    random_part = get_random_string(length=6, allowed_chars='0123456789')
    return f"{prefix}-{random_part}"

def generate_return_number():
    """Generate a unique return number."""
    prefix = 'R' + timezone.now().strftime('%Y%m')
    random_part = get_random_string(length=6, allowed_chars='0123456789')
    return f"{prefix}-{random_part}"

def get_or_create_user_address(user, form_data, address_type):
    """Create or retrieve user address based on form data."""
    if form_data['address_choice'] == 'existing':
        # Use existing address
        address_id = form_data['existing_address']
        return get_object_or_404(Address, id=address_id, user=user)
    else:
        # Create new address
        address = Address(
            user=user,
            address_line1=form_data['address_line1'],
            address_line2=form_data['address_line2'],
            city=form_data['city'],
            state=form_data['state'],
            postal_code=form_data['postal_code'],
            country=form_data['country'],
            phone_number=form_data['phone'],
            address_type=address_type,
            is_default=form_data['save_address']
        )
        address.save()
        return address

def apply_coupon(request, code, cart_total):
    """Apply a coupon to the cart total."""
    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)
        now = timezone.now()
        
        # Check validity
        if not coupon.is_valid:
            messages.error(request, 'This coupon is no longer valid.')
            return None, cart_total
        
        # Check minimum order amount
        if coupon.min_order_amount and cart_total < coupon.min_order_amount:
            messages.error(
                request, 
                f'Your order total must be at least {coupon.min_order_amount} to use this coupon.'
            )
            return None, cart_total
        
        # Calculate discount
        discount = coupon.calculate_discount(cart_total)
        
        if discount <= 0:
            messages.error(request, 'This coupon cannot be applied to your order.')
            return None, cart_total
        
        messages.success(
            request, 
            f'Coupon {coupon.code} applied! You saved {discount} on your order.'
        )
        return coupon, cart_total - discount
    
    except Coupon.DoesNotExist:
        messages.error(request, 'Invalid coupon code.')
        return None, cart_total

def calculate_tax(cart_total, shipping_address):
    """Calculate tax based on shipping address."""
    # In a real-world scenario, this would include tax calculation logic
    # based on shipping location, product types, etc.
    # For now, we'll use a simple percentage
    tax_rate = Decimal('0.18')  # 18% GST in India
    
    # You might have different tax rates for different states in India
    if shipping_address.state.upper() in ['KARNATAKA', 'DELHI', 'MAHARASHTRA']:
        tax_rate = Decimal('0.18')
    elif shipping_address.state.upper() in ['GUJARAT', 'TAMIL NADU']:
        tax_rate = Decimal('0.15')
    
    return (cart_total * tax_rate).quantize(Decimal('0.01'))

def calculate_shipping(cart_total, shipping_address):
    """Calculate shipping fee based on cart total and shipping address."""
    # In a real-world scenario, this would include complex shipping calculation
    # based on weight, dimensions, distance, and shipping carrier rates
    # For now, we'll use a simple logic
    
    if cart_total >= Decimal('2000.00'):
        return Decimal('0.00')  # Free shipping for orders above 2000
    
    base_shipping = Decimal('100.00')
    
    # Additional shipping for remote areas
    remote_states = ['ASSAM', 'ARUNACHAL PRADESH', 'MANIPUR', 'MEGHALAYA', 
                    'MIZORAM', 'NAGALAND', 'SIKKIM', 'TRIPURA', 'ANDAMAN AND NICOBAR']
    if shipping_address.state.upper() in remote_states:
        base_shipping += Decimal('50.00')
    
    return base_shipping

@login_required
def checkout(request):
    """Checkout page to collect shipping, billing, and payment information."""
    user = request.user
    cart, created = Cart.objects.get_or_create(user=user)
    
    # Redirect to cart if empty
    if cart.items.count() == 0:
        messages.error(request, 'Your cart is empty. Please add items before checkout.')
        return redirect('cart_detail')
    
    # Get default currency
    default_currency = Currency.objects.filter(is_default=True).first()
    if not default_currency:
        default_currency = Currency.objects.create(
            code='INR',
            name='Indian Rupee',
            symbol='₹',
            exchange_rate=Decimal('1.0'),
            is_default=True
        )
    
    # Initialize amounts
    cart_total = cart.get_total_price()
    discount = Decimal('0.00')
    coupon = None
    
    # Check for applied coupon in session
    coupon_code = request.session.get('coupon_code')
    if coupon_code:
        coupon, cart_total = apply_coupon(request, coupon_code, cart_total)
        if coupon:
            discount = cart.get_total_price() - cart_total
    
    # Handle form submission
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=user)
        
        if form.is_valid():
            # Process the order
            try:
                with transaction.atomic():
                    # Get or create addresses
                    shipping_data = {
                        'address_choice': form.cleaned_data['shipping_address_choice'],
                        'existing_address': form.cleaned_data['existing_shipping_address'],
                        'address_line1': form.cleaned_data['shipping_address_line1'],
                        'address_line2': form.cleaned_data['shipping_address_line2'],
                        'city': form.cleaned_data['shipping_city'],
                        'state': form.cleaned_data['shipping_state'],
                        'postal_code': form.cleaned_data['shipping_postal_code'],
                        'country': form.cleaned_data['shipping_country'],
                        'phone': form.cleaned_data['shipping_phone'],
                        'save_address': form.cleaned_data['save_shipping_address']
                    }
                    shipping_address = get_or_create_user_address(user, shipping_data, 'SHIPPING')
                    
                    if form.cleaned_data['billing_same_as_shipping']:
                        billing_address = shipping_address
                    else:
                        billing_data = {
                            'address_choice': form.cleaned_data['billing_address_choice'],
                            'existing_address': form.cleaned_data['existing_billing_address'],
                            'address_line1': form.cleaned_data['billing_address_line1'],
                            'address_line2': form.cleaned_data['billing_address_line2'],
                            'city': form.cleaned_data['billing_city'],
                            'state': form.cleaned_data['billing_state'],
                            'postal_code': form.cleaned_data['billing_postal_code'],
                            'country': form.cleaned_data['billing_country'],
                            'phone': form.cleaned_data['billing_phone'],
                            'save_address': form.cleaned_data['save_billing_address']
                        }
                        billing_address = get_or_create_user_address(user, billing_data, 'BILLING')
                    
                    # Calculate final amounts
                    shipping_amount = calculate_shipping(cart_total, shipping_address)
                    tax_amount = calculate_tax(cart_total, shipping_address)
                    total_amount = cart_total + shipping_amount + tax_amount
                    
                    # Create the order
                    order = Order.objects.create(
                        user=user,
                        order_number=generate_order_number(),
                        currency=default_currency,
                        shipping_address=shipping_address,
                        billing_address=billing_address,
                        subtotal=cart.get_total_price(),
                        shipping_amount=shipping_amount,
                        tax_amount=tax_amount,
                        discount_amount=discount,
                        total=total_amount,
                        coupon=coupon,
                        notes=form.cleaned_data['notes'],
                        status='PENDING',
                        payment_status='PENDING'
                    )
                    
                    # Add order status log
                    OrderStatusLog.objects.create(
                        order=order,
                        status='PENDING',
                        notes='Order created'
                    )
                    
                    # Add order items
                    for cart_item in cart.items.all():
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            price=cart_item.product.get_active_price(),
                            total=cart_item.get_total_price()
                        )
                    
                    # Create payment record
                    payment_method = form.cleaned_data['payment_method']
                    Payment.objects.create(
                        order=order,
                        payment_method=payment_method,
                        amount=total_amount,
                        currency=default_currency.code,
                        status='PENDING'
                    )
                    
                    # Clear cart
                    cart.clear()
                    
                    # Clear coupon from session
                    if 'coupon_code' in request.session:
                        del request.session['coupon_code']
                    
                    # Update coupon usage if used
                    if coupon:
                        coupon.usage_count += 1
                        coupon.save()
                    
                    # Send order confirmation email
                    send_order_confirmation_email(order)
                    
                    # Redirect to payment page
                    return redirect('order_payment', order_number=order.order_number)
            
            except Exception as e:
                messages.error(request, f'An error occurred while processing your order: {str(e)}')
    else:
        form = CheckoutForm(user=user)
    
    # Calculate totals for display
    shipping_estimate = calculate_shipping(cart_total, user.addresses.filter(is_default=True).first() if user.addresses.exists() else None) if cart_total > 0 else Decimal('0.00')
    tax_estimate = calculate_tax(cart_total, user.addresses.filter(is_default=True).first() if user.addresses.exists() else None) if cart_total > 0 else Decimal('0.00')
    total_estimate = cart_total + shipping_estimate + tax_estimate
    
    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'cart_total': cart_total,
        'discount': discount,
        'shipping_estimate': shipping_estimate,
        'tax_estimate': tax_estimate,
        'total_estimate': total_estimate,
        'coupon_form': CouponForm(),
        'applied_coupon': coupon
    })

@login_required
def apply_coupon_view(request):
    """Apply a coupon code to the order."""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            # Store in session
            request.session['coupon_code'] = code
            
            # Redirect back to checkout
            return redirect('checkout')
    
    # If not POST or form invalid, redirect to checkout
    return redirect('checkout')

@login_required
def remove_coupon(request):
    """Remove an applied coupon."""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
        messages.success(request, 'Coupon removed successfully.')
    
    return redirect('checkout')

@login_required
def order_payment(request, order_number):
    """Process payment for an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payments.first()
    
    # If already paid, redirect to success page
    if order.payment_status == 'PAID':
        return redirect('order_success', order_number=order_number)
    
    # Process payment based on method
    if payment.payment_method == 'COD':
        # For COD, just mark as processing
        payment.status = 'PENDING'
        payment.save()
        
        order.status = 'PROCESSING'
        order.save()
        
        OrderStatusLog.objects.create(
            order=order,
            status='PROCESSING',
            notes='Order confirmed with Cash on Delivery payment method'
        )
        
        return redirect('order_success', order_number=order_number)
    
    # For online payments
    payment_context = {
        'order': order,
        'payment': payment
    }
    
    # Different templates/processing for different payment methods
    if payment.payment_method in ['CREDIT_CARD', 'DEBIT_CARD']:
        return render(request, 'orders/payments/card_payment.html', payment_context)
    elif payment.payment_method == 'UPI':
        return render(request, 'orders/payments/upi_payment.html', payment_context)
    elif payment.payment_method == 'NET_BANKING':
        return render(request, 'orders/payments/netbanking_payment.html', payment_context)
    elif payment.payment_method == 'WALLET':
        return render(request, 'orders/payments/wallet_payment.html', payment_context)
    else:
        return render(request, 'orders/payments/generic_payment.html', payment_context)

@login_required
def process_payment(request, order_number):
    """Process a payment submission."""
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payments.first()
    
    # In a real implementation, you would process the payment through a payment gateway
    # and handle the response accordingly
    
    # For demonstration, we'll simulate a successful payment
    transaction_id = f"TX-{order_number}-{get_random_string(8).upper()}"
    
    # Update payment
    payment.status = 'PAID'
    payment.transaction_id = transaction_id
    payment.save()
    
    # Update order
    order.payment_status = 'PAID'
    order.status = 'PROCESSING'
    order.save()
    
    # Add order status log
    OrderStatusLog.objects.create(
        order=order,
        status='PROCESSING',
        notes=f'Payment received. Transaction ID: {transaction_id}'
    )
    
    # Create a shipment
    Shipment.objects.create(
        order=order,
        status='PROCESSING',
        estimated_delivery=timezone.now() + datetime.timedelta(days=5)
    )
    
    # Redirect to success page
    return redirect('order_success', order_number=order_number)

@login_required
def order_success(request, order_number):
    """Display order success page after checkout."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    return render(request, 'orders/order_success.html', {
        'order': order
    })

@login_required
def order_detail(request, order_number):
    """Display order details."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    return render(request, 'orders/order_detail.html', {
        'order': order
    })

@login_required
def order_history(request):
    """Display order history for a user."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter orders
    form = OrderFilterForm(request.GET)
    if form.is_valid():
        status = form.cleaned_data.get('status')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        order_number = form.cleaned_data.get('order_number')
        
        if status:
            orders = orders.filter(status=status)
        
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        
        if order_number:
            orders = orders.filter(order_number__icontains=order_number)
    
    # Paginate orders
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    return render(request, 'orders/order_history.html', {
        'orders': orders,
        'form': form
    })

@login_required
def order_invoice(request, order_number):
    """Generate and display order invoice."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    return render(request, 'orders/order_invoice.html', {
        'order': order
    })

@login_required
def order_tracking(request, order_number):
    """Display order tracking information."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    shipments = order.shipments.all()
    
    return render(request, 'orders/order_tracking.html', {
        'order': order,
        'shipments': shipments
    })

@login_required
def order_cancel(request, order_number):
    """Cancel an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order can be cancelled
    if not order.can_be_cancelled:
        messages.error(request, 'This order cannot be cancelled at this stage.')
        return redirect('order_detail', order_number=order_number)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Update order status
            order.status = 'CANCELLED'
            order.save()
            
            # Add order status log
            OrderStatusLog.objects.create(
                order=order,
                status='CANCELLED',
                notes=f'Order cancelled by customer. Reason: {request.POST.get("reason", "No reason provided")}'
            )
            
            # If payment was made, initiate refund
            if order.payment_status == 'PAID':
                order.payment_status = 'REFUNDED'
                order.save()
                
                # Create refund record
                Payment.objects.create(
                    order=order,
                    payment_method=order.payments.first().payment_method,
                    amount=order.total,
                    currency=order.currency.code,
                    status='REFUNDED',
                    notes='Refund initiated due to order cancellation'
                )
            
            # Send cancellation email
            send_order_cancellation_email(order)
            
            messages.success(request, 'Your order has been cancelled successfully.')
            return redirect('order_history')
    
    return render(request, 'orders/order_cancel.html', {
        'order': order
    })

@login_required
def request_return(request, order_number):
    """Request a return for an order."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order is eligible for return
    if order.status not in ['DELIVERED', 'COMPLETED']:
        messages.error(request, 'This order is not eligible for return.')
        return redirect('order_detail', order_number=order_number)
    
    # Check if return already exists
    if Return.objects.filter(order=order).exists():
        messages.error(request, 'A return request already exists for this order.')
        return redirect('order_detail', order_number=order_number)
    
    if request.method == 'POST':
        form = ReturnForm(request.POST)
        
        if form.is_valid():
            with transaction.atomic():
                # Create return request
                return_request = Return.objects.create(
                    order=order,
                    user=request.user,
                    return_number=generate_return_number(),
                    reason=form.cleaned_data['reason'],
                    refund_amount=order.total,  # Full refund by default
                    status='REQUESTED',
                    refund_status='PENDING'
                )
                
                # Add return items
                for order_item in order.items.all():
                    quantity = int(request.POST.get(f'item_{order_item.id}_quantity', 0))
                    reason = request.POST.get(f'item_{order_item.id}_reason', '')
                    
                    if quantity > 0:
                        ReturnItem.objects.create(
                            return_request=return_request,
                            product=order_item.product,
                            quantity=quantity,
                            reason=reason
                        )
                
                # Add return log
                ReturnLog.objects.create(
                    return_request=return_request,
                    status='REQUESTED',
                    notes='Return requested by customer'
                )
                
                # Send return request email
                send_return_request_email(return_request)
                
                messages.success(request, 'Your return request has been submitted successfully.')
                return redirect('return_detail', return_number=return_request.return_number)
    else:
        form = ReturnForm()
    
    return render(request, 'orders/request_return.html', {
        'order': order,
        'form': form
    })

@login_required
def return_detail(request, return_number):
    """Display return request details."""
    return_request = get_object_or_404(Return, return_number=return_number, user=request.user)
    
    return render(request, 'orders/return_detail.html', {
        'return_request': return_request
    })

@login_required
def return_history(request):
    """Display return history for a user."""
    returns = Return.objects.filter(user=request.user).order_by('-created_at')
    
    # Paginate returns
    paginator = Paginator(returns, 10)  # Show 10 returns per page
    page = request.GET.get('page')
    try:
        returns = paginator.page(page)
    except PageNotAnInteger:
        returns = paginator.page(1)
    except EmptyPage:
        returns = paginator.page(paginator.num_pages)
    
    return render(request, 'orders/return_history.html', {
        'returns': returns
    })

def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    subject = f'Order Confirmation - {order.order_number}'
    context = {
        'order': order,
        'user': order.user
    }
    html_message = render_to_string('orders/emails/order_confirmation.html', context)
    plain_message = render_to_string('orders/emails/order_confirmation_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_order_cancellation_email(order):
    """Send order cancellation email to customer."""
    subject = f'Order Cancellation - {order.order_number}'
    context = {
        'order': order,
        'user': order.user
    }
    html_message = render_to_string('orders/emails/order_cancellation.html', context)
    plain_message = render_to_string('orders/emails/order_cancellation_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message,
        fail_silently=False
    )

def send_return_request_email(return_request):
    """Send return request confirmation email to customer."""
    subject = f'Return Request Confirmation - {return_request.return_number}'
    context = {
        'return_request': return_request,
        'user': return_request.user,
        'order': return_request.order
    }
    html_message = render_to_string('orders/emails/return_request.html', context)
    plain_message = render_to_string('orders/emails/return_request_plain.html', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [return_request.user.email],
        html_message=html_message,
        fail_silently=False
    )