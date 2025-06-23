from django.contrib import admin

from django.contrib import admin
from .models import Ticket, Payment

class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'event', 'status', 'quantity', 'payment_completed', 'created_at']
    list_filter = ['status', 'payment_completed', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'event__title']
    readonly_fields = ['id', 'order_number', 'qr_code', 'created_at', 'updated_at']
    inlines = [PaymentInline]
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('id', 'order_number', 'user', 'event', 'event_date', 'ticket_type', 'quantity', 'status')
        }),
        ('Payment Details', {
            'fields': ('total_price', 'service_fee', 'payment_method', 'payment_completed')
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'ticket', 'payment_method', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'ticket__order_number', 'ticket__user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
