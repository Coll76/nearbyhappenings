import requests
import base64
import json
from datetime import datetime
import logging
from django.conf import settings
from .exceptions import PaymentProcessingError

logger = logging.getLogger(__name__)

class MPesaService:
    """
    Service for processing payments through M-Pesa
    """
    
    def __init__(self):
        # M-Pesa API endpoints
        self.access_token_url = f"{settings.MPESA_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = f"{settings.MPESA_API_URL}/mpesa/stkpush/v1/processrequest"
        self.query_url = f"{settings.MPESA_API_URL}/mpesa/stkpushquery/v1/query"
        
        # M-Pesa credentials
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        
    def _get_access_token(self):
        """Get M-Pesa API access token"""
        try:
            auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode("utf-8")
            headers = {
                "Authorization": f"Basic {auth}"
            }
            
            response = requests.get(self.access_token_url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get("access_token")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting M-Pesa access token: {str(e)}")
            raise PaymentProcessingError("Could not connect to M-Pesa")
            
    def _generate_password(self):
        """Generate the M-Pesa password"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        return encoded, timestamp
    
    def process_payment(self, payment, payment_data):
        """
        Process a payment through M-Pesa
        
        Args:
            payment: Payment model instance
            payment_data: Dictionary containing payment details like phone number
            
        Returns:
            Updated payment object with transaction details
        """
        try:
            phone_number = payment_data.get('phone_number')
            if not phone_number:
                raise PaymentProcessingError("Phone number is required for M-Pesa payments")
                
            # Format phone number (ensure it starts with 254)
            if phone_number.startswith('+'):
                phone_number = phone_number[1:]
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            if not phone_number.startswith('254'):
                phone_number = '254' + phone_number
                
            # Get access token
            access_token = self._get_access_token()
            
            # Generate password and timestamp
            password, timestamp = self._generate_password()
            
            # Amount should be an integer
            amount = int(payment.amount)
            
            # Prepare STK push request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            stk_payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": payment.ticket.order_number,
                "TransactionDesc": f"Ticket purchase for {payment.ticket.event.title}"
            }
            
            # Initiate STK push
            response = requests.post(self.stk_push_url, headers=headers, json=stk_payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ResponseCode") == "0":
                # STK push was successful, update payment with checkout request ID
                checkout_request_id = result.get("CheckoutRequestID")
                
                # Update payment record
                payment.status = 'PENDING'  # Payment still needs confirmation from callback
                payment.transaction_id = checkout_request_id
                payment.payment_details = {
                    'phone_number': phone_number,
                    'checkout_request_id': checkout_request_id,
                    'merchant_request_id': result.get("MerchantRequestID")
                }
                payment.save()
                
                logger.info(f"M-Pesa STK push initiated: {checkout_request_id}")
                return payment
            else:
                # STK push failed
                payment.status = 'FAILED'
                payment.payment_details = {
                    'error': result.get("ResponseDescription", "STK push failed"),
                    'error_code': result.get("ResponseCode")
                }
                payment.save()
                logger.error(f"M-Pesa STK push failed: {result}")
                raise PaymentProcessingError(result.get("ResponseDescription", "Payment initiation failed"))
                
        except requests.exceptions.RequestException as e:
            payment.status = 'FAILED'
            payment.payment_details = {'error': str(e)}
            payment.save()
            logger.error(f"M-Pesa request error: {str(e)}")
            raise PaymentProcessingError("Could not connect to M-Pesa")
            
        except Exception as e:
            payment.status = 'FAILED'
            payment.payment_details = {'error': str(e)}
            payment.save()
            logger.error(f"Unexpected error in M-Pesa payment: {str(e)}", exc_info=True)
            raise PaymentProcessingError("An unexpected error occurred")
            
    def query_transaction(self, checkout_request_id):
        """
        Query the status of an M-Pesa transaction
        
        Args:
            checkout_request_id: M-Pesa checkout request ID
            
        Returns:
            Transaction status
        """
        try:
            # Get access token
            access_token = self._get_access_token()
            
            # Generate password and timestamp
            password, timestamp = self._generate_password()
            
            # Prepare query request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            query_payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            # Send query request
            response = requests.post(self.query_url, headers=headers, json=query_payload)
            response.raise_for_status()
            result = response.json()
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa query error: {str(e)}")
            raise PaymentProcessingError("Could not connect to M-Pesa")
            
        except Exception as e:
            logger.error(f"Unexpected error in M-Pesa query: {str(e)}", exc_info=True)
            raise PaymentProcessingError("An unexpected error occurred")
            
    def process_callback(self, callback_data, payment):
        """
        Process M-Pesa callback data
        
        Args:
            callback_data: Callback data from M-Pesa
            payment: Payment model instance
            
        Returns:
            Updated payment object
        """
        try:
            # Extract result code and the body
            stkCallback = callback_data.get("Body", {}).get("stkCallback", {})
            result_code = stkCallback.get("ResultCode")
            
            if result_code == 0:
                # Payment successful
                item_list = stkCallback.get("CallbackMetadata", {}).get("Item", [])
                
                # Extract payment details from item list
                payment_details = {}
                for item in item_list:
                    name = item.get("Name")
                    value = item.get("Value")
                    if name and value:
                        payment_details[name] = value
                
                # Update payment record
                payment.status = 'COMPLETED'
                payment.transaction_id = payment_details.get("MpesaReceiptNumber", payment.transaction_id)
                
                # Update payment details
                existing_details = payment.payment_details or {}
                existing_details.update({
                    'mpesa_receipt': payment_details.get("MpesaReceiptNumber"),
                    'transaction_date': payment_details.get("TransactionDate"),
                    'amount': payment_details.get("Amount"),
                    'phone_number': payment_details.get("PhoneNumber")
                })
                payment.payment_details = existing_details
                payment.save()
                
                # Update ticket status
                ticket = payment.ticket
                ticket.status = 'CONFIRMED'
                ticket.payment_completed = True
                ticket.save()
                
                logger.info(f"M-Pesa payment completed: {payment.transaction_id}")
                return payment
                
            else:
                # Payment failed
                payment.status = 'FAILED'
                reason = stkCallback.get("ResultDesc", "Payment failed")
                
                # Update payment details
                existing_details = payment.payment_details or {}
                existing_details.update({
                    'error': reason,
                    'error_code': result_code
                })
                payment.payment_details = existing_details
                payment.save()
                
                logger.error(f"M-Pesa payment failed: {reason}")
                return payment
                
        except Exception as e:
            payment.status = 'FAILED'
            payment.payment_details = {'error': str(e)}
            payment.save()
            logger.error(f"Error processing M-Pesa callback: {str(e)}", exc_info=True)
            raise PaymentProcessingError("Error processing payment callback")
            
    def process_refund(self, payment):
        """
        Process refund for M-Pesa payment
        
        Note: M-Pesa refunds typically require a separate process through the M-Pesa Business portal
        or API. This is a simplified version.
        
        Args:
            payment: Payment model instance
            
        Returns:
            Updated payment with refund details
        """
        try:
            # Check if payment was completed and has a transaction ID
            if payment.status != 'COMPLETED' or not payment.transaction_id:
                raise PaymentProcessingError("Cannot refund a payment that wasn't completed")
                
            # In a real implementation, you would initiate a refund request to M-Pesa
            # Here we're marking it as refunded and logging the action
            
            # Update payment status
            payment.status = 'REFUNDED'
            
            # Add refund details to payment record
            payment_details = payment.payment_details or {}
            payment_details.update({
                'refund_initiated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'refund_status': 'INITIATED',
                'refund_notes': 'Refund will be processed manually through M-Pesa Business'
            })
            payment.payment_details = payment_details
            payment.save()
            
            logger.info(f"M-Pesa refund initiated for: {payment.transaction_id}")
            return payment
            
        except Exception as e:
            logger.error(f"Unexpected error in M-Pesa refund: {str(e)}", exc_info=True)
            raise PaymentProcessingError("An unexpected error occurred during refund")
