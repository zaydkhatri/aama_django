# payments/gateways/stripe.py
import stripe
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse

from ..models import PaymentGatewaySettings, Transaction

class StripeGateway:
    """Stripe payment gateway integration."""
    
    def __init__(self):
        """Initialize Stripe API with settings from database."""
        self.gateway_settings = PaymentGatewaySettings.objects.filter(
            gateway='STRIPE', 
            is_active=True
        ).first()
        
        if not self.gateway_settings:
            raise ValueError("Stripe gateway is not configured or not active")
        
        # Initialize Stripe with API key
        stripe.api_key = self.gateway_settings.api_secret
        self.is_test = self.gateway_settings.test_mode
    
    def create_payment_intent(self, order, return_url=None):
        """Create a payment intent for an order."""
        amount_in_cents = int(order.total * 100)  # Convert to cents
        
        try:
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=order.currency.code.lower(),
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number
                },
                description=f"Payment for order {order.order_number}",
                receipt_email=order.user.email
            )
            
            # Record transaction in database
            transaction = Transaction.objects.create(
                order=order,
                payment=order.payments.first(),
                gateway='STRIPE',
                amount=order.total,
                currency=order.currency.code,
                status='INITIATED',
                payment_method='CREDIT_CARD',
                gateway_transaction_id=intent.id,
                gateway_response=intent,
                is_test=self.is_test
            )
            
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'transaction_id': str(transaction.id),
                'payment_intent_id': intent.id
            }
        
        except stripe.error.StripeError as e:
            # Handle Stripe errors
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_checkout_session(self, order, return_url, cancel_url):
        """Create a Stripe Checkout session for an order."""
        line_items = []
        
        # Add order items to line items
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': order.currency.code.lower(),
                    'product_data': {
                        'name': item.product.name,
                        'description': item.product.description[:255] if item.product.description else None,
                        'metadata': {
                            'product_id': str(item.product.id)
                        }
                    },
                    'unit_amount': int(item.price * 100),  # Convert to cents
                },
                'quantity': item.quantity,
            })
        
        # Add shipping and tax as separate line items
        if order.shipping_amount > 0:
            line_items.append({
                'price_data': {
                    'currency': order.currency.code.lower(),
                    'product_data': {
                        'name': 'Shipping',
                    },
                    'unit_amount': int(order.shipping_amount * 100),
                },
                'quantity': 1,
            })
        
        if order.tax_amount > 0:
            line_items.append({
                'price_data': {
                    'currency': order.currency.code.lower(),
                    'product_data': {
                        'name': 'Tax',
                    },
                    'unit_amount': int(order.tax_amount * 100),
                },
                'quantity': 1,
            })
        
        # Apply discount if any
        discounts = []
        if order.discount_amount > 0:
            discounts.append({
                'coupon': {
                    'amount_off': int(order.discount_amount * 100),
                    'currency': order.currency.code.lower(),
                    'name': 'Discount',
                    'duration': 'once',
                }
            })
        
        try:
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                metadata={
                    'order_id': str(order.id),
                    'order_number': order.order_number
                },
                mode='payment',
                success_url=return_url,
                cancel_url=cancel_url,
                discounts=discounts if discounts else None,
                customer_email=order.user.email
            )
            
            # Record transaction in database
            transaction = Transaction.objects.create(
                order=order,
                payment=order.payments.first(),
                gateway='STRIPE',
                amount=order.total,
                currency=order.currency.code,
                status='INITIATED',
                payment_method='CREDIT_CARD',
                gateway_order_id=checkout_session.id,
                gateway_response=checkout_session,
                is_test=self.is_test
            )
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'transaction_id': str(transaction.id)
            }
        
        except stripe.error.StripeError as e:
            # Handle Stripe errors
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, request):
        """Process Stripe webhook events."""
        webhook_secret = self.gateway_settings.webhook_secret
        payload = request.body.decode('utf-8')
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            
            # Create webhook event record
            from ..models import WebhookEvent
            webhook_event = WebhookEvent.objects.create(
                gateway='STRIPE',
                event_type=self._map_event_type(event['type']),
                event_id=event['id'],
                is_test='livemode' not in event or not event['livemode'],
                payload=event
            )
            
            # Process the event
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_success(event, webhook_event)
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failure(event, webhook_event)
            elif event['type'] == 'charge.refunded':
                return self._handle_refund(event, webhook_event)
            else:
                # Mark as processed but no specific handling
                webhook_event.processed = True
                webhook_event.save()
                return HttpResponse(status=200)
        
        except ValueError as e:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=400)
        except Exception as e:
            return HttpResponse(content=str(e), status=500)
    
    def _map_event_type(self, stripe_event_type):
        """Map Stripe event type to internal event type."""
        event_map = {
            'payment_intent.succeeded': 'PAYMENT_INTENT_SUCCEEDED',
            'payment_intent.payment_failed': 'PAYMENT_INTENT_FAILED',
            'charge.succeeded': 'CHARGE_SUCCEEDED',
            'charge.failed': 'CHARGE_FAILED',
            'charge.refunded': 'CHARGE_REFUNDED',
            'checkout.session.completed': 'CHECKOUT_COMPLETED',
        }
        return event_map.get(stripe_event_type, 'OTHER')
    
    def _handle_payment_success(self, event, webhook_event):
        """Handle successful payment event."""
        payment_intent = event['data']['object']
        
        try:
            # Find transaction by payment intent ID
            transaction = Transaction.objects.get(
                gateway='STRIPE',
                gateway_transaction_id=payment_intent['id']
            )
            
            # Update transaction
            transaction.status = 'COMPLETED'
            transaction.gateway_response = payment_intent
            transaction.save()
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment = transaction.payment
            if payment:
                payment.status = 'PAID'
                payment.transaction_id = payment_intent['id']
                payment.save()
            
            return HttpResponse(status=200)
        
        except Transaction.DoesNotExist:
            # If we can't find the transaction, check if it's from checkout session
            metadata = payment_intent.get('metadata', {})
            order_id = metadata.get('order_id')
            
            if order_id:
                from orders.models import Order, Payment
                try:
                    order = Order.objects.get(id=order_id)
                    
                    # Create transaction if not exists
                    transaction = Transaction.objects.create(
                        order=order,
                        payment=order.payments.first(),
                        gateway='STRIPE',
                        amount=Decimal(payment_intent['amount']) / 100,  # Convert cents to dollars
                        currency=payment_intent['currency'].upper(),
                        status='COMPLETED',
                        payment_method='CREDIT_CARD',
                        gateway_transaction_id=payment_intent['id'],
                        gateway_response=payment_intent,
                        is_test=not payment_intent.get('livemode', True)
                    )
                    
                    # Update order payment
                    payment = order.payments.first()
                    if payment:
                        payment.status = 'PAID'
                        payment.transaction_id = payment_intent['id']
                        payment.save()
                    
                    # Link webhook event to transaction
                    webhook_event.transaction = transaction
                    webhook_event.processed = True
                    webhook_event.save()
                    
                    return HttpResponse(status=200)
                
                except Order.DoesNotExist:
                    webhook_event.error_message = f"Order not found: {order_id}"
                    webhook_event.processed = True
                    webhook_event.save()
                    return HttpResponse(status=400)
            
            webhook_event.error_message = f"Transaction not found for payment intent: {payment_intent['id']}"
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=400)
    
    def _handle_payment_failure(self, event, webhook_event):
        """Handle failed payment event."""
        payment_intent = event['data']['object']
        
        try:
            # Find transaction by payment intent ID
            transaction = Transaction.objects.get(
                gateway='STRIPE',
                gateway_transaction_id=payment_intent['id']
            )
            
            # Update transaction
            transaction.status = 'FAILED'
            transaction.gateway_response = payment_intent
            transaction.error_message = payment_intent.get('last_payment_error', {}).get('message', '')
            transaction.save()
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment = transaction.payment
            if payment:
                payment.status = 'FAILED'
                payment.save()
            
            return HttpResponse(status=200)
        
        except Transaction.DoesNotExist:
            webhook_event.error_message = f"Transaction not found for payment intent: {payment_intent['id']}"
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=400)
    
    def _handle_refund(self, event, webhook_event):
        """Handle refund event."""
        charge = event['data']['object']
        
        try:
            # Find transaction by charge ID
            transaction = Transaction.objects.filter(
                gateway='STRIPE',
                gateway_response__contains=charge['id']
            ).first()
            
            if not transaction:
                webhook_event.error_message = f"Transaction not found for charge: {charge['id']}"
                webhook_event.processed = True
                webhook_event.save()
                return HttpResponse(status=400)
            
            # Calculate refund amount
            refund_amount = Decimal(charge['amount_refunded']) / 100  # Convert cents to dollars
            
            # Update transaction
            if refund_amount >= Decimal(charge['amount']) / 100:
                transaction.status = 'REFUNDED'
            else:
                transaction.status = 'PARTIALLY_REFUNDED'
            
            transaction.refund_amount = refund_amount
            transaction.gateway_response = charge
            transaction.save()
            
            # Create refund record
            from ..models import Refund
            refund = Refund.objects.create(
                transaction=transaction,
                amount=refund_amount,
                reason='Refund processed through Stripe',
                status='COMPLETED',
                gateway_refund_id=charge['refunds']['data'][0]['id'] if charge['refunds']['data'] else None,
                gateway_response=charge['refunds']['data'][0] if charge['refunds']['data'] else None
            )
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment = transaction.payment
            if payment:
                if refund_amount >= Decimal(charge['amount']) / 100:
                    payment.status = 'REFUNDED'
                else:
                    payment.status = 'PARTIALLY_REFUNDED'
                payment.save()
            
            return HttpResponse(status=200)
        
        except Exception as e:
            webhook_event.error_message = str(e)
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=500)
    
    def create_refund(self, transaction, amount, reason):
        """Create a refund for a transaction."""
        if transaction.gateway != 'STRIPE':
            raise ValueError("Transaction was not processed by Stripe")
        
        if transaction.status not in ['COMPLETED']:
            raise ValueError("Transaction must be completed to be refunded")
        
        try:
            # Create refund in Stripe
            payment_intent_id = transaction.gateway_transaction_id
            
            # If amount is None, refund full amount
            if amount is None:
                refund = stripe.Refund.create(
                    payment_intent=payment_intent_id,
                    reason='requested_by_customer'
                )
                refund_amount = transaction.amount
            else:
                # Convert amount to cents for Stripe
                amount_in_cents = int(amount * 100)
                refund = stripe.Refund.create(
                    payment_intent=payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer'
                )
                refund_amount = amount
            
            # Create refund record in database
            from ..models import Refund
            refund_record = Refund.objects.create(
                transaction=transaction,
                amount=refund_amount,
                reason=reason,
                status='COMPLETED',
                gateway_refund_id=refund.id,
                gateway_response=refund
            )
            
            # Update transaction status and refund amount
            if refund_amount >= transaction.amount:
                transaction.status = 'REFUNDED'
            else:
                transaction.status = 'PARTIALLY_REFUNDED'
            
            transaction.refund_amount = transaction.refund_amount + refund_amount
            transaction.save()
            
            # Update order payment status
            payment = transaction.payment
            if payment:
                if refund_amount >= transaction.amount:
                    payment.status = 'REFUNDED'
                else:
                    payment.status = 'PARTIALLY_REFUNDED'
                payment.save()
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund_amount,
                'refund_record_id': str(refund_record.id)
            }
        
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }