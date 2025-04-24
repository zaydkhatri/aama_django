# payments/gateways/razorpay.py
import razorpay
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse

from ..models import PaymentGatewaySettings, Transaction

class RazorpayGateway:
    """Razorpay payment gateway integration."""
    
    def __init__(self):
        """Initialize Razorpay API with settings from database."""
        self.gateway_settings = PaymentGatewaySettings.objects.filter(
            gateway='RAZORPAY', 
            is_active=True
        ).first()
        
        if not self.gateway_settings:
            raise ValueError("Razorpay gateway is not configured or not active")
        
        # Initialize Razorpay client
        self.client = razorpay.Client(
            auth=(self.gateway_settings.api_key, self.gateway_settings.api_secret)
        )
        self.is_test = self.gateway_settings.test_mode
    
    def create_order(self, order, return_url=None):
        """Create a Razorpay order for payment."""
        amount_in_paisa = int(order.total * 100)  # Convert to paisa (Indian currency subunit)
        
        try:
            receipt = f"receipt_{order.order_number}"
            
            # Create order in Razorpay
            razorpay_order = self.client.order.create({
                'amount': amount_in_paisa,
                'currency': order.currency.code,
                'receipt': receipt,
                'notes': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'email': order.user.email
                },
                'payment_capture': '1'  # Auto capture payment
            })
            
            # Record transaction in database
            transaction = Transaction.objects.create(
                order=order,
                payment=order.payments.first(),
                gateway='RAZORPAY',
                amount=order.total,
                currency=order.currency.code,
                status='INITIATED',
                payment_method=self._map_payment_method(order.payments.first().payment_method),
                gateway_order_id=razorpay_order['id'],
                gateway_response=razorpay_order,
                is_test=self.is_test
            )
            
            # Prepare payment options
            payment_options = {
                'key': self.gateway_settings.api_key,
                'amount': amount_in_paisa,
                'currency': order.currency.code,
                'name': 'Abaya Ecommerce',
                'description': f'Payment for order {order.order_number}',
                'order_id': razorpay_order['id'],
                'prefill': {
                    'name': order.user.name,
                    'email': order.user.email,
                    'contact': order.user.phone
                },
                'notes': {
                    'order_number': order.order_number
                },
                'theme': {
                    'color': '#3399cc'
                }
            }
            
            # Add callback URLs if provided
            if return_url:
                payment_options['callback_url'] = return_url
                payment_options['redirect'] = True
            
            return {
                'success': True,
                'order_id': razorpay_order['id'],
                'transaction_id': str(transaction.id),
                'payment_options': payment_options
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, payment_id, order_id, signature):
        """Verify Razorpay payment signature."""
        try:
            # Verify signature
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            }
            
            self.client.utility.verify_payment_signature(params_dict)
            
            # Get payment details
            payment_details = self.client.payment.fetch(payment_id)
            
            # Find transaction by order ID
            transaction = Transaction.objects.get(
                gateway='RAZORPAY',
                gateway_order_id=order_id
            )
            
            # Update transaction
            transaction.status = 'COMPLETED' if payment_details['status'] == 'captured' else 'PROCESSING'
            transaction.gateway_transaction_id = payment_id
            transaction.gateway_response = payment_details
            transaction.save()
            
            # Update order payment
            payment = transaction.payment
            if payment:
                payment.status = 'PAID' if payment_details['status'] == 'captured' else 'PENDING'
                payment.transaction_id = payment_id
                payment.save()
            
            return {
                'success': True,
                'transaction_id': str(transaction.id),
                'payment_id': payment_id,
                'status': payment_details['status']
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, request):
        """Process Razorpay webhook events."""
        payload = request.body.decode('utf-8')
        signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
        
        # Verify webhook signature
        if not self._verify_webhook_signature(payload, signature):
            return HttpResponse(status=400)
        
        try:
            import json
            event_data = json.loads(payload)
            event_type = event_data.get('event')
            
            # Create webhook event record
            from ..models import WebhookEvent
            webhook_event = WebhookEvent.objects.create(
                gateway='RAZORPAY',
                event_type=self._map_event_type(event_type),
                event_id=event_data.get('id', ''),
                is_test=self.is_test,
                payload=event_data
            )
            
            # Process the event
            if event_type == 'payment.captured':
                return self._handle_payment_success(event_data, webhook_event)
            elif event_type == 'payment.failed':
                return self._handle_payment_failure(event_data, webhook_event)
            elif event_type == 'refund.processed':
                return self._handle_refund(event_data, webhook_event)
            else:
                # Mark as processed but no specific handling
                webhook_event.processed = True
                webhook_event.save()
                return HttpResponse(status=200)
        
        except Exception as e:
            return HttpResponse(content=str(e), status=500)
    
    def _verify_webhook_signature(self, payload, signature):
        """Verify Razorpay webhook signature."""
        if not signature:
            return False
        
        webhook_secret = self.gateway_settings.webhook_secret
        if not webhook_secret:
            return False
        
        try:
            expected_signature = hmac.new(
                key=webhook_secret.encode(),
                msg=payload.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except:
            return False
    
    def _map_event_type(self, razorpay_event_type):
        """Map Razorpay event type to internal event type."""
        event_map = {
            'payment.captured': 'PAYMENT_INTENT_SUCCEEDED',
            'payment.failed': 'PAYMENT_INTENT_FAILED',
            'refund.processed': 'CHARGE_REFUNDED',
            'order.paid': 'CHECKOUT_COMPLETED',
        }
        return event_map.get(razorpay_event_type, 'OTHER')
    
    def _map_payment_method(self, internal_payment_method):
        """Map internal payment method to Razorpay payment method."""
        method_map = {
            'CREDIT_CARD': 'card',
            'DEBIT_CARD': 'card',
            'UPI': 'upi',
            'NET_BANKING': 'netbanking',
            'WALLET': 'wallet',
        }
        return method_map.get(internal_payment_method, internal_payment_method)
    
    def _handle_payment_success(self, event_data, webhook_event):
        """Handle successful payment event."""
        payment = event_data.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        
        try:
            # Find transaction by order ID
            transaction = Transaction.objects.get(
                gateway='RAZORPAY',
                gateway_order_id=order_id
            )
            
            # Update transaction
            transaction.status = 'COMPLETED'
            transaction.gateway_transaction_id = payment_id
            transaction.gateway_response = payment
            transaction.save()
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment_obj = transaction.payment
            if payment_obj:
                payment_obj.status = 'PAID'
                payment_obj.transaction_id = payment_id
                payment_obj.save()
            
            return HttpResponse(status=200)
        
        except Transaction.DoesNotExist:
            webhook_event.error_message = f"Transaction not found for order: {order_id}"
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=400)
    
    def _handle_payment_failure(self, event_data, webhook_event):
        """Handle failed payment event."""
        payment = event_data.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        
        try:
            # Find transaction by order ID
            transaction = Transaction.objects.get(
                gateway='RAZORPAY',
                gateway_order_id=order_id
            )
            
            # Update transaction
            transaction.status = 'FAILED'
            transaction.gateway_transaction_id = payment_id
            transaction.gateway_response = payment
            transaction.error_message = payment.get('error_description', '')
            transaction.save()
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment_obj = transaction.payment
            if payment_obj:
                payment_obj.status = 'FAILED'
                payment_obj.save()
            
            return HttpResponse(status=200)
        
        except Transaction.DoesNotExist:
            webhook_event.error_message = f"Transaction not found for order: {order_id}"
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=400)
    
    def _handle_refund(self, event_data, webhook_event):
        """Handle refund event."""
        refund = event_data.get('payload', {}).get('refund', {}).get('entity', {})
        payment_id = refund.get('payment_id')
        
        try:
            # Find transaction by payment ID
            transaction = Transaction.objects.get(
                gateway='RAZORPAY',
                gateway_transaction_id=payment_id
            )
            
            # Calculate refund amount
            refund_amount = Decimal(refund.get('amount', 0)) / 100  # Convert paisa to rupees
            
            # Update transaction
            if refund_amount >= transaction.amount:
                transaction.status = 'REFUNDED'
            else:
                transaction.status = 'PARTIALLY_REFUNDED'
            
            transaction.refund_amount = refund_amount
            transaction.gateway_response = {
                **transaction.gateway_response,
                'refund': refund
            }
            transaction.save()
            
            # Create refund record
            from ..models import Refund
            refund_record = Refund.objects.create(
                transaction=transaction,
                amount=refund_amount,
                reason=refund.get('notes', {}).get('reason', 'Refund processed through Razorpay'),
                status='COMPLETED',
                gateway_refund_id=refund.get('id'),
                gateway_response=refund
            )
            
            # Link webhook event to transaction
            webhook_event.transaction = transaction
            webhook_event.processed = True
            webhook_event.save()
            
            # Update order payment
            from orders.models import Payment
            payment_obj = transaction.payment
            if payment_obj:
                if refund_amount >= transaction.amount:
                    payment_obj.status = 'REFUNDED'
                else:
                    payment_obj.status = 'PARTIALLY_REFUNDED'
                payment_obj.save()
            
            return HttpResponse(status=200)
        
        except Transaction.DoesNotExist:
            webhook_event.error_message = f"Transaction not found for payment: {payment_id}"
            webhook_event.processed = True
            webhook_event.save()
            return HttpResponse(status=400)
    
    def create_refund(self, transaction, amount, reason):
        """Create a refund for a transaction."""
        if transaction.gateway != 'RAZORPAY':
            raise ValueError("Transaction was not processed by Razorpay")
        
        if transaction.status not in ['COMPLETED']:
            raise ValueError("Transaction must be completed to be refunded")
        
        if not transaction.gateway_transaction_id:
            raise ValueError("Transaction does not have a payment ID")
        
        try:
            payment_id = transaction.gateway_transaction_id
            
            # If amount is None, refund full amount
            if amount is None:
                amount_in_paisa = int(transaction.amount * 100)
                refund_amount = transaction.amount
            else:
                # Convert amount to paisa for Razorpay
                amount_in_paisa = int(amount * 100)
                refund_amount = amount
            
            # Create refund in Razorpay
            refund = self.client.payment.refund(
                payment_id,
                {
                    'amount': amount_in_paisa,
                    'notes': {
                        'reason': reason,
                        'transaction_id': str(transaction.id),
                        'order_number': transaction.order.order_number
                    }
                }
            )
            
            # Create refund record in database
            from ..models import Refund
            refund_record = Refund.objects.create(
                transaction=transaction,
                amount=refund_amount,
                reason=reason,
                status='PROCESSING',
                gateway_refund_id=refund['id'],
                gateway_response=refund
            )
            
            # Update transaction status and refund amount
            transaction.refund_amount = transaction.refund_amount + refund_amount
            if transaction.refund_amount >= transaction.amount:
                transaction.status = 'REFUNDED'
            else:
                transaction.status = 'PARTIALLY_REFUNDED'
            transaction.save()
            
            return {
                'success': True,
                'refund_id': refund['id'],
                'amount': refund_amount,
                'refund_record_id': str(refund_record.id)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }