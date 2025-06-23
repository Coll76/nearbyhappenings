from django.db import models

from django.db import models
from authentication.models import User
from events.models import Event, EventDate
import uuid
from django.utils import timezone

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('USED', 'Used'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('CARD', 'Credit/Debit Card'),
        ('MPESA', 'M-Pesa'),
        ('PAYPAL', 'PayPal'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    event_date = models.ForeignKey(EventDate, on_delete=models.CASCADE, related_name='tickets')
    quantity = models.PositiveIntegerField(default=1)
    ticket_type = models.CharField(max_length=50, default='Regular')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    qr_code = models.CharField(max_length=255, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Generate order number if not already set
        if not self.order_number:
            # Format: ORD-{6 random digits}
            random_id = uuid.uuid4().hex[:6].upper()
            self.order_number = f"ORD-{random_id}"
            
        # Generate QR code value (in a real app, you'd generate an actual QR code image)
        if not self.qr_code and self.status == 'CONFIRMED':
            self.qr_code = f"{self.order_number}-{uuid.uuid4().hex[:10].upper()}"
            
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user.username} - {self.event.title} - {self.order_number}"
    
    @property
    def is_past(self):
        """Check if ticket is for a past event"""
        now = timezone.now().date()
        return self.event_date.date < now
    
    @property
    def can_be_cancelled(self):
        """Check if ticket can be cancelled (not past and not already cancelled)"""
        return not self.is_past and self.status != 'CANCELLED'



    def update_status(self, new_status, update_event_count=True):
        """
        Update ticket status and related event counters in a consistent way
        """
        old_status = self.status
        self.status = new_status
        
        # Update payment completion flag
        if new_status == 'CONFIRMED':
            self.payment_completed = True
        elif new_status == 'CANCELLED':
            self.payment_completed = False
    
        self.save()
        
        # Update event date tickets sold count
        if update_event_count:
            event_date = self.event_date
            
            # Only update counts if status changed from/to CONFIRMED
            if old_status != 'CONFIRMED' and new_status == 'CONFIRMED':
                # Adding tickets
                event_date.tickets_sold += self.quantity
                event_date.save()
            elif old_status == 'CONFIRMED' and new_status != 'CONFIRMED':
                # Removing tickets
                event_date.tickets_sold -= self.quantity
                event_date.save()
    
        # If there's a payment record, update it too
        if hasattr(self, 'payment'):
            if new_status == 'CONFIRMED':
                self.payment.status = 'COMPLETED'
            elif new_status == 'CANCELLED':
                self.payment.status = 'REFUNDED'
            self.payment.save()





class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=Ticket.PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.ticket.order_number} - {self.amount} {self.currency} - {self.status}"
