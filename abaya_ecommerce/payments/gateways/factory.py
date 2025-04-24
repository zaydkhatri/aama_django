# payments/gateways/factory.py
from django.conf import settings
from ..models import PaymentGatewaySettings

class PaymentGatewayFactory:
    """Factory class to create payment gateway instances."""
    
    @staticmethod
    def get_gateway(gateway_name=None):
        """
        Get a payment gateway instance by name.
        If no name is provided, returns the default gateway.
        """
        if not gateway_name:
            # Get default gateway
            gateway_setting = PaymentGatewaySettings.objects.filter(
                is_active=True
            ).first()
            
            if not gateway_setting:
                raise ValueError("No active payment gateway configured")
            
            gateway_name = gateway_setting.gateway
        
        # Ensure gateway is active
        if not PaymentGatewaySettings.objects.filter(
            gateway=gateway_name,
            is_active=True
        ).exists():
            raise ValueError(f"Payment gateway {gateway_name} is not active")
        
        # Create and return gateway instance
        if gateway_name == 'STRIPE':
            from .stripe import StripeGateway
            return StripeGateway()
        
        elif gateway_name == 'RAZORPAY':
            from .razorpay import RazorpayGateway
            return RazorpayGateway()
        
        elif gateway_name == 'PAYPAL':
            from .paypal import PayPalGateway
            return PayPalGateway()
        
        elif gateway_name == 'PAYU':
            from .payu import PayUGateway
            return PayUGateway()
        
        else:
            raise ValueError(f"Unsupported payment gateway: {gateway_name}")
    
    @staticmethod
    def get_available_gateways():
        """Get all available active payment gateways."""
        gateways = []
        gateway_settings = PaymentGatewaySettings.objects.filter(is_active=True)
        
        for setting in gateway_settings:
            gateways.append({
                'id': setting.gateway,
                'name': setting.display_name,
                'description': setting.description,
                'payment_methods': setting.payment_methods
            })
        
        return gateways