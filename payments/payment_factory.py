from .stripe_service import StripeService
from .mpesa_service import MPesaService
from .exceptions import PaymentProcessingError

class PaymentFactory:
    """
    Factory class for creating payment processors based on payment method
    """
    
    @staticmethod
    def get_processor(payment_method):
        """
        Get the appropriate payment processor based on payment method
        
        Args:
            payment_method: Payment method code (CARD, MPESA, etc.)
            
        Returns:
            Payment processor instance
        """
        if payment_method == 'CARD':
            return StripeService()
        elif payment_method == 'MPESA':
            return MPesaService()
        else:
            raise PaymentProcessingError(f"Unsupported payment method: {payment_method}")
    
    @staticmethod
    def process_payment(payment, payment_data):
        """
        Process a payment using the appropriate processor
        
        Args:
            payment: Payment model instance
            payment_data: Dictionary containing payment details
            
        Returns:
            Updated payment with transaction details
        """
        processor = PaymentFactory.get_processor(payment.payment_method)
        return processor.process_payment(payment, payment_data)
    
    @staticmethod
    def process_refund(payment):
        """
        Process a refund using the appropriate processor
        
        Args:
            payment: Payment model instance
            
        Returns:
            Updated payment with refund details
        """
        processor = PaymentFactory.get_processor(payment.payment_method)
        return processor.process_refund(payment)
