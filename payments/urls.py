from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Checkout flow
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('select-method/', views.SelectPaymentMethodView.as_view(), name='select_method'),
    path('sumup/checkout/<int:order_id>/', views.SumUpCheckoutView.as_view(), name='sumup_checkout'),

    # SumUp callbacks and webhooks
    path('sumup/callback/', views.SumUpCallbackView.as_view(), name='sumup_callback'),
    path('sumup/success/', views.SumUpSuccessView.as_view(), name='sumup_success'),
    path('sumup/webhook/', views.SumUpWebhookView.as_view(), name='sumup_webhook'),

    # Legacy compatibility
    path('process/sumup/', views.ProcessSumUpPaymentView.as_view(), name='process_sumup'),
    path('callback/', views.SumUpCallbackView.as_view(), name='callback'),
    path('success/', views.PaymentSuccessView.as_view(), name='success'),
    path('failed/', views.PaymentFailedView.as_view(), name='failed'),

    path("sumup/connect/<int:artist_id>/", views.sumup_connect_start, name="sumup_connect_start"),
    path("sumup/callback/", views.sumup_connect_callback, name="sumup_connect_callback"),
    path("checkout/start/<int:artist_id>/", views.start_checkout, name="start_checkout"),
    path("success/", views.payment_success, name="payment_success"),
    path("fail/", views.payment_fail, name="payment_fail"),
    path("sumup/webhook/", views.sumup_webhook, name="sumup_webhook"),
    path("billing/run/", views.run_monthly_billing, name="run_monthly_billing"),
    path('checkout-widget/<str:checkout_id>/', views.CheckoutWidgetView.as_view(), name='checkout_widget'),

    path('subscription/process/<int:subscription_payment_id>/', views.process_subscription, name='process_subscription'),
    path('subscription/history/', views.subscription_history, name='subscription_history'),
]
