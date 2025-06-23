from django.shortcuts import render
from django.db import transaction
from core.models import SiteSetting
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta, date
from django.db.models import Q
import logging
from rest_framework.decorators import action
from payments.payment_factory import PaymentFactory
from payments.exceptions import PaymentProcessingError
from .models import Ticket, Payment
from .serializers import TicketSerializer, TicketPurchaseSerializer
from events.models import EventDate

# Set up logging
logger = logging.getLogger(__name__)

class IsTicketOwnerOrEventPlanner(permissions.BasePermission):
    """
    Custom permission to allow ticket owners and event planners to access their tickets.
    """
    def has_object_permission(self, request, view, obj):
        # Check if this ticket belongs to the user
        if obj.user == request.user:
            return True
            
        # Check if user is the event planner for this ticket
        if hasattr(request.user, 'planner_profile'):
            return obj.event.planner == request.user.planner_profile
            
        return False

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketOwnerOrEventPlanner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'event', 'payment_completed']
    ordering_fields = ['created_at', 'event_date__date']
    
    def get_queryset(self):
        """
        Filter tickets for the current user or event planner
        """
        user = self.request.user
        
        # Check if filtering for upcoming or past tickets
        filter_type = self.request.query_params.get('filter', None)
        today = date.today()
        
        queryset = Ticket.objects.none()
        
        # If user is a planner, show tickets for their events
        if hasattr(user, 'planner_profile'):
            planner = user.planner_profile
            queryset = Ticket.objects.filter(event__planner=planner)
        else:
            # Regular users see their own tickets
            queryset = Ticket.objects.filter(user=user)
        
        # Apply upcoming/past filter
        if filter_type == 'upcoming':
            queryset = queryset.filter(event_date__date__gte=today)
        elif filter_type == 'past':
            queryset = queryset.filter(event_date__date__lt=today)
            
        return queryset.order_by('-created_at')





    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        Refund a ticket payment
        """
        ticket = self.get_object()
        
        if not hasattr(ticket, 'payment') or ticket.payment.status != 'COMPLETED':
            return Response(
                {"status": "error", "detail": "This ticket cannot be refunded as payment is not complete"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Process refund through the payment factory
            payment = ticket.payment
            
            # Use transaction to ensure data consistency
            with transaction.atomic():
                PaymentFactory.process_refund(payment)
                # Update ticket status using the model method
                ticket.update_status('CANCELLED')

            return Response(
                {"status": "success", "detail": "Ticket refunded successfully"},
                status=status.HTTP_200_OK
            )

        except PaymentProcessingError as e:
            logger.error(f"Error processing refund: {str(e)}")
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error processing refund: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "detail": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






    @action(detail=True, methods=['get'])
    def payment_details(self, request, pk=None):
        """
        Get payment details for a ticket
        """
        ticket = self.get_object()
    
        if not hasattr(ticket, 'payment'):
            return Response(
                {"status": "error", "detail": "No payment found for this ticket"},
                status=status.HTTP_404_NOT_FOUND
            )
    
        payment = ticket.payment
        payment_data = {
            "id": str(payment.id),
            "payment_method": payment.payment_method,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "transaction_id": payment.transaction_id,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }
    
        # Add payment method specific details
        if payment.payment_method == 'CARD' and payment.status == 'COMPLETED':
            payment_data.update({
                "card_last4": payment.payment_details.get('card_last4', ''),
                "card_expiry": payment.payment_details.get('card_expiry', ''),
                "card_name": payment.payment_details.get('card_name', '')
            })
        elif payment.payment_method == 'MPESA' and payment.status == 'COMPLETED':
            payment_data.update({
                "mpesa_receipt": payment.payment_details.get('mpesa_receipt', ''),
                "phone_number": payment.payment_details.get('phone_number', ''),
                "transaction_date": payment.payment_details.get('transaction_date', '')
            })
    
        return Response(payment_data)




    @action(detail=True, methods=['get'])
    def check_payment_status(self, request, pk=None):
        """
        Check current payment status for a pending ticket
        """
        ticket = self.get_object()

        if not hasattr(ticket, 'payment'):
            return Response(
                {"status": "error", "detail": "No payment found for this ticket"},
                status=status.HTTP_404_NOT_FOUND
            )

        payment = ticket.payment

        # If payment is still pending, check its current status
        if payment.status == 'PENDING':
            if payment.payment_method == 'MPESA' and payment.transaction_id:
                try:
                    # For M-Pesa, query the transaction status
                    from payments.mpesa_service import MPesaService
                    mpesa_service = MPesaService()
                    result = mpesa_service.query_transaction(payment.transaction_id)

                    # If the query shows payment is complete, update the status
                    if result.get('ResultCode') == '0':
                        with transaction.atomic():
                            payment.status = 'COMPLETED'
                            payment.save()
                            # Use the model method to update ticket status
                            ticket.update_status('CONFIRMED')

                    return Response({
                        "status": "success",
                        "ticket_status": ticket.status,
                        "payment_status": payment.status,
                        "mpesa_status": result
                    })

                except Exception as e:
                    logger.error(f"Error checking M-Pesa status: {str(e)}", exc_info=True)

        # For other payment methods or non-pending status, just return current status
        return Response({
            "status": "success",
            "ticket_status": ticket.status,
            "payment_status": payment.status,
        })


    
    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Purchase tickets for an event
        """
        try:
            serializer = TicketPurchaseSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                return Response(
                    {
                        "status": "error",
                        "detail": "Invalid ticket purchase data",
                        "errors": serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Create ticket with payment
            ticket = serializer.save()
            
            # Return ticket details
            return Response(
                {
                    "status": "success",
                    "detail": "Ticket purchased successfully",
                    "ticket": TicketSerializer(ticket).data,
                    "order_number": ticket.order_number
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Unexpected error processing ticket purchase: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "detail": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
           

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a ticket
        """
        ticket = self.get_object()

        if not ticket.can_be_cancelled:
            return Response(
                {"status": "error", "detail": "This ticket cannot be cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use a transaction for data consistency
            with transaction.atomic():
                # Mark ticket as cancelled using the model method
                ticket.update_status('CANCELLED')

            return Response(
                {"status": "success", "detail": "Ticket cancelled successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error cancelling ticket: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "detail": "An error occurred while cancelling ticket"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get ticket stats for event planners
        """
        # Only event planners can access this endpoint
        if not hasattr(request.user, 'planner_profile'):
            return Response(
                {"status": "error", "detail": "Only event planners can access ticket stats"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        planner = request.user.planner_profile
        queryset = Ticket.objects.filter(event__planner=planner)
        
        # Basic stats
        total_tickets = queryset.count()
        total_sales = sum(ticket.total_price for ticket in queryset.filter(payment_completed=True))
        total_service_fees = sum(ticket.service_fee for ticket in queryset.filter(payment_completed=True))
        
        # Status breakdown
        status_counts = {
            'confirmed': queryset.filter(status='CONFIRMED').count(),
            'pending': queryset.filter(status='PENDING').count(),
            'cancelled': queryset.filter(status='CANCELLED').count(),
            'used': queryset.filter(status='USED').count()
        }
        
        # Event breakdown (top 5 events by ticket sales)
        from django.db.models import Count, Sum
        events_data = queryset.values('event__title').annotate(
            ticket_count=Count('id'),
            revenue=Sum('total_price', filter=Q(payment_completed=True))
        ).order_by('-ticket_count')[:5]
        
        return Response({
            "total_tickets": total_tickets,
            "total_sales": total_sales,
            "total_service_fees": total_service_fees,
            "status_counts": status_counts,
            "top_events": events_data
        })
