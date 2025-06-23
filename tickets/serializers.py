from rest_framework import serializers
from .models import Ticket, Payment
from events.serializers import EventListSerializer
from django.db import transaction
from events.models import EventDate, Event
import decimal
from payments.payment_factory import PaymentFactory
from payments.exceptions import PaymentProcessingError
from core.models import SiteSetting
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'payment_method', 'amount', 'currency', 'status', 'transaction_id']
        read_only_fields = ['id', 'status', 'transaction_id']

class TicketSerializer(serializers.ModelSerializer):
    payment = PaymentSerializer(read_only=True)
    event_details = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'event', 'event_date', 'quantity', 'ticket_type',
            'status', 'order_number', 'qr_code', 'total_price',
            'service_fee', 'payment_method', 'payment_completed',
            'created_at', 'updated_at', 'payment', 'event_details',
            'is_past', 'can_be_cancelled'
        ]
        read_only_fields = [
            'id', 'status', 'order_number', 'qr_code',
            'payment_completed', 'created_at', 'updated_at'
        ]

    def get_event_details(self, obj):
        """Get formatted event details for display in tickets list"""
        return {
            'eventId': str(obj.event.id),
            'eventTitle': obj.event.title,
            'eventImage': obj.event.image.url if obj.event.image else None,
            'location': obj.event.location,
            'date': obj.event_date.date.strftime("%b %d, %Y"),
            'time': obj.event_date.time.strftime("%I:%M %p")
        }

class TicketPurchaseSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    date_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)
    payment_method = serializers.ChoiceField(choices=['CARD', 'MPESA'])

    # Card payment fields (only required if payment method is CARD)
    card_number = serializers.CharField(max_length=19, required=False)
    card_expiry = serializers.CharField(max_length=5, required=False)
    card_cvv = serializers.CharField(max_length=4, required=False)
    card_name = serializers.CharField(max_length=100, required=False)

    # M-Pesa field (only required if payment method is MPESA)
    phone_number = serializers.CharField(max_length=15, required=False)

    

    def validate(self, data):
        # Validate event exists
        try:
            event = Event.objects.get(id=data['event_id'])
        except Event.DoesNotExist:
            raise serializers.ValidationError({"event_id": "Event does not exist"})

        # Validate event date exists and belongs to the event 
        try:
            # Use select_for_update to lock the row during validation
            from django.db import transaction
            with transaction.atomic():
                event_date = EventDate.objects.select_for_update().get(
                    id=data['date_id'], 
                    event=event
                )
            
                # Check if tickets are available
                if event_date.availability == 'Sold Out':
                    raise serializers.ValidationError({"date_id": "This event date is sold out"})

                # Check if requested quantity is available
                if event_date.tickets_sold + data['quantity'] > event_date.capacity:
                    remaining = event_date.capacity - event_date.tickets_sold
                    raise serializers.ValidationError({
                        "quantity": f"Only {remaining} tickets are available for this date"
                    })
        except EventDate.DoesNotExist:
            raise serializers.ValidationError({"date_id": "Event date does not exist or doesn't belong to this event"})

        # The rest of the validation remains the same...
        # Validate payment method specific fields
        if data['payment_method'] == 'CARD':
            required_fields = ['card_number', 'card_expiry', 'card_cvv', 'card_name']
            for field in required_fields:
                if field not in data or not data[field]:
                    raise serializers.ValidationError({field: f"{field} is required for card payments"})

        elif data['payment_method'] == 'MPESA':
            if 'phone_number' not in data or not data['phone_number']:
                raise serializers.ValidationError({"phone_number": "Phone number is required for M-Pesa payments"})

        # Add calculated fields to validated data
        data['event'] = event
        data['event_date'] = event_date



        # Get the site settings
        site_settings = SiteSetting.get_settings()
        
        # Calculate prices
        ticket_price = event_date.price if event_date.price else event.price
        subtotal = ticket_price * data['quantity']
        
        # Apply service fee only if enabled in settings
        if site_settings.service_fee_enabled:
            service_fee_rate = site_settings.service_fee_percentage / 100
            service_fee = subtotal * decimal.Decimal(str(service_fee_rate))
        else:
            service_fee = decimal.Decimal('0.00')  # No service fee
            
        total_price = subtotal + service_fee
        
        data['ticket_price'] = ticket_price
        data['subtotal'] = subtotal
        data['service_fee'] = service_fee
        data['total_price'] = total_price
        
        return data



    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        event = validated_data['event']
        event_date = validated_data['event_date']

        # Create ticket record
        ticket = Ticket.objects.create(
            user=user,
            event=event,
            event_date=event_date,
            quantity=validated_data['quantity'],
            ticket_type='Regular',
            total_price=validated_data['total_price'],
            service_fee=validated_data['service_fee'],
            payment_method=validated_data['payment_method'],
        )

        # Create payment record
        payment = Payment.objects.create(
            ticket=ticket,
            payment_method=validated_data['payment_method'],
            amount=validated_data['total_price'],
            currency=event.currency,
        )

        # Process payment using the payment factory
        try:
            PaymentFactory.process_payment(payment, validated_data)
        except PaymentProcessingError as e:
            # If payment processing fails, mark ticket as pending
            # The ticket will be automatically updated if/when payment completes
            ticket.status = 'PENDING'
            ticket.save()
            raise serializers.ValidationError({"payment": str(e)})

        # Update ticket status if payment was successful immediately
        if payment.status == 'COMPLETED':
            ticket.update_status('CONFIRMED')

        return ticket

