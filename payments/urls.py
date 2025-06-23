from django.urls import path
from .views import MPesaCallbackView, StripeWebhookView, PaymentStatusView

urlpatterns = [
    path('mpesa/callback/', MPesaCallbackView.as_view(), name='mpesa-callback'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('status/<uuid:payment_id>/', PaymentStatusView.as_view(), name='payment-status'),
]
