# payments/gateways/base.py
from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    """
    Abstract base class for payment gateway integrations.
    All payment gateway classes should implement these methods.
    """
    
    @abstractmethod
    def __init__(self):
        """Initialize the payment gateway with settings."""
        pass
    
    @abstractmethod
    def create_payment(self, order, return_url=None, cancel_url=None):
        """
        Create a payment for the order.
        
        Args:
            order: The Order object to be paid
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect after canceled payment
            
        Returns:
            dict: Response with payment information
        """
        pass
    
    @abstractmethod
    def verify_payment(self, *args, **kwargs):
        """
        Verify a payment.
        
        Args vary by payment gateway.
        
        Returns:
            dict: Response with verification result
        """
        pass
    
    @abstractmethod
    def process_webhook(self, request):
        """
        Process webhook events from the payment gateway.
        
        Args:
            request: The HTTP request with webhook data
            
        Returns:
            HttpResponse: Response to the webhook
        """
        pass
    
    @abstractmethod
    def create_refund(self, transaction, amount, reason):
        """
        Create a refund for a transaction.
        
        Args:
            transaction: The Transaction object to refund
            amount: Amount to refund (None for full refund)
            reason: Reason for the refund
            
        Returns:
            dict: Response with refund information
        """
        pass