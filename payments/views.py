from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from tickets.models import Payment
from .mpesa_service import MPesaService
from .stripe_service import StripeService
import stripe

logger = logging.getLogger(__name__)

class MPesaCallbackView(APIView):
    """
    View to handle M-Pesa STK push callbacks
    """
    # No authentication required for M-Pesa callbacks
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            # Parse callback data
            callback_data = request.data
            logger.info(f"Received M-Pesa callback: {json.dumps(callback_data)}")

            # Extract checkout request ID
            checkout_request_id = callback_data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")

            if not checkout_request_id:
                logger.error("No CheckoutRequestID in callback data")
                return Response({"result": "error", "message": "Invalid callback data"}, status=status.HTTP_400_BAD_REQUEST)

            # Find payment with this checkout request ID
            try:
                payment = Payment.objects.get(transaction_id=checkout_request_id)
            except Payment.DoesNotExist:
                logger.error(f"No payment found for CheckoutRequestID: {checkout_request_id}")
                return Response({"result": "error", "message": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            # Process the callback
            mpesa_service = MPesaService()
            mpesa_service.process_callback(callback_data, payment)

            # Return success response
            return Response({"result": "success"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing M-Pesa callback: {str(e)}", exc_info=True)
            return Response({"result": "error", "message": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(APIView):
    """
    View to handle Stripe webhook events
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            
            logger.info(f"Received Stripe webhook: {event.type}")
            
            # Handle payment events
            if event.type == 'charge.succeeded':
                charge = event.data.object
                transaction_id = charge.id
                
                try:
                    payment = Payment.objects.get(transaction_id=transaction_id)
                    
                    # If the payment isn't already marked as completed
                    if payment.status != 'COMPLETED':
                        payment.status = 'COMPLETED'
                        payment.save()
                        
                        # Update ticket status
                        ticket = payment.ticket
                        ticket.status = 'CONFIRMED'
                        ticket.payment_completed = True
                        ticket.save()
                        
                        # Update event date tickets sold count
                        event_date = ticket.event_date
                        event_date.tickets_sold += ticket.quantity
                        event_date.save()
                        
                        logger.info(f"Payment {payment.id} marked as completed via webhook")
                
                except Payment.DoesNotExist:
                    logger.error(f"No payment found for transaction ID: {transaction_id}")
            
            elif event.type == 'charge.refunded':
                charge = event.data.object
                transaction_id = charge.id
                
                try:
                    payment = Payment.objects.get(transaction_id=transaction_id)
                    
                    # If the payment isn't already refunded
                    if payment.status != 'REFUNDED':
                        payment.status = 'REFUNDED'
                        payment.save()
                        
                        # Update ticket status
                        ticket = payment.ticket
                        ticket.status = 'CANCELLED'
                        ticket.save()
                        
                        logger.info(f"Payment {payment.id} marked as refunded via webhook")
                
                except Payment.DoesNotExist:
                    logger.error(f"No payment found for transaction ID: {transaction_id}")
                    
            return Response({"status": "success"}, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            return Response({"status": "error", "message": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            return Response({"status": "error", "message": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error processing Stripe webhook: {str(e)}", exc_info=True)
            return Response({"status": "error", "message": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusView(APIView):
    """
    View to check payment status
    """
    def get(self, request, payment_id, *args, **kwargs):
        try:
            payment = Payment.objects.get(id=payment_id)
            
            # Authorization check - only payment owner can check status
            if payment.ticket.user != request.user:
                return Response({"status": "error", "message": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
            
            # If payment is still pending, check its current status
            if payment.status == 'PENDING':
                if payment.payment_method == 'MPESA':
                    # For M-Pesa, query the transaction status
                    mpesa_service = MPesaService()
                    checkout_request_id = payment.transaction_id
                    if checkout_request_id:
                        result = mpesa_service.query_transaction(checkout_request_id)
                        return Response({
                            "status": "success",
                            "payment_status": payment.status,
                            "mpesa_status": result
                        })
                
                # For other payment methods, just return current status
                return Response({
                    "status": "success", 
                    "payment_status": payment.status,
                    "payment_details": payment.payment_details
                })
            
            # For completed/failed payments, return the current status
            return Response({
                "status": "success",
                "payment_status": payment.status,
                "payment_details": payment.payment_details
            })
            
        except Payment.DoesNotExist:
            return Response({"status": "error", "message": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
            return Response({"status": "error", "message": "Server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
