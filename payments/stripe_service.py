import stripe
from django.conf import settings
from decimal import Decimal
from .exceptions import PaymentProcessingError
import logging

logger = logging.getLogger(__name__)

# Configure Stripe with your API key
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """
    Service for processing payments through Stripe
    """
    def process_payment(self, payment, payment_data):
        try:
            # Use payment_method_id or token from frontend
            payment_method_id = payment_data.get('payment_method_id')
            if not payment_method_id:
                raise PaymentProcessingError("Missing payment method ID")

            # Create Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),
                currency=payment.currency.lower(),
                payment_method=payment_method_id,
                confirm=True,
                return_url=settings.STRIPE_RETURN_URL,
                metadata={
                    "order_number": payment.ticket.order_number,
                    "event": payment.ticket.event.title,
                    "user_id": str(payment.ticket.user.id)
                }
            )

            # Update payment record
            payment.status = 'PROCESSING' if intent.status == 'processing' else 'COMPLETED'
            payment.transaction_id = intent.id
            payment.payment_details = {
                'payment_method': intent.payment_method,
                'status': intent.status
            }
            payment.save()

            return payment
        
        except stripe.error.CardError as e:
            # Card declined
            payment.status = 'FAILED'
            payment.payment_details = {
                'error': str(e),
                'error_code': e.code,
                'decline_code': e.decline_code if hasattr(e, 'decline_code') else None
            }
            payment.save()
            logger.error(f"Card error: {str(e)}")
            raise PaymentProcessingError(f"Card was declined: {e.user_message}")

        except stripe.error.StripeError as e:
            # Other Stripe errors
            payment.status = 'FAILED'
            payment.payment_details = {'error': str(e)}
            payment.save()
            logger.error(f"Stripe error: {str(e)}")
            raise PaymentProcessingError("Payment processing failed")

        except Exception as e:
            payment.status = 'FAILED'
            payment.payment_details = {'error': str(e)}
            payment.save()
            logger.error(f"Unexpected error in Stripe payment: {str(e)}", exc_info=True)
            raise PaymentProcessingError("An unexpected error occurred")


    def process_refund(self, payment):
        """
        Process a refund for a previous payment
        
        Args:
            payment: Payment model instance
            
        Returns:
            Updated payment with refund details
        """
        try:
            # Check if payment was completed and has a transaction ID
            if payment.status != 'COMPLETED' or not payment.transaction_id:
                raise PaymentProcessingError("Cannot refund a payment that wasn't completed")
                
            # Process refund through Stripe
            refund = stripe.Refund.create(
                charge=payment.transaction_id,
                reason="requested_by_customer"
            )
            
            # Update payment status
            payment.status = 'REFUNDED'
            
            # Add refund details to payment record
            payment_details = payment.payment_details or {}
            payment_details.update({
                'refund_id': refund.id,
                'refund_status': refund.status,
                'refund_date': refund.created
            })
            payment.payment_details = payment_details
            payment.save()
            
            logger.info(f"Refund processed successfully: {refund.id}")
            return payment
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {str(e)}")
            raise PaymentProcessingError(f"Refund failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in Stripe refund: {str(e)}", exc_info=True)
            raise PaymentProcessingError("An unexpected error occurred during refund")
