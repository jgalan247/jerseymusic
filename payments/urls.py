from django.urls import path
from . import views
from . import widget_views
from . import widget_views_fixed
from . import redirect_checkout
from . import simple_checkout
from . import redirect_success_fixed

app_name = 'payments'

urlpatterns = [
    # SIMPLE CHECKOUT FLOW - PRIMARY METHOD
    path('simple-checkout/', simple_checkout.simple_checkout_process, name='simple_checkout'),

    # SIMPLIFIED REDIRECT-BASED CHECKOUT (NO WIDGETS)
    path('redirect/checkout/<int:order_id>/', redirect_checkout.create_order_checkout, name='redirect_checkout'),
    path('redirect/success/', redirect_success_fixed.redirect_success_fixed, name='redirect_success'),
    path('redirect/cancel/', redirect_checkout.redirect_cancel, name='redirect_cancel'),
    path('redirect/listing-fee/<int:event_id>/', redirect_checkout.create_listing_fee_checkout, name='redirect_listing_fee'),
    path('redirect/listing-success/', redirect_checkout.redirect_listing_success, name='redirect_listing_success'),

    # Main checkout flow
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('select-method/', views.SelectPaymentMethodView.as_view(), name='select_method'),

    # SumUp checkout endpoints
    path('sumup/checkout/<int:order_id>/', views.SumUpCheckoutView.as_view(), name='sumup_checkout'),
    path('sumup/connected-checkout/<int:order_id>/', views.ConnectedSumUpCheckoutView.as_view(), name='connected_sumup_checkout'),
    path('checkout-widget/<str:checkout_id>/', views.CheckoutWidgetView.as_view(), name='checkout_widget'),

    # Payment result endpoints
    path('success/', views.payment_success, name='success'),
    path('fail/', views.payment_fail, name='fail'),
    path('cancel/', views.payment_cancel, name='cancel'),

    # Payment result views (class-based)
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/failed/', views.PaymentFailedView.as_view(), name='payment_failed'),
    path('payment/cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),

    # SumUp-specific endpoints
    path('sumup/success/', views.SumUpSuccessView.as_view(), name='sumup_success'),
    path('sumup/callback/', views.SumUpCallbackView.as_view(), name='sumup_callback'),
    path('sumup/webhook/', views.sumup_webhook, name='sumup_webhook'),

    # SumUp OAuth endpoints
    path('sumup/oauth/connect/<int:artist_id>/', views.sumup_connect_start, name='sumup_connect_start'),
    path('sumup/oauth/callback/', views.sumup_connect_callback, name='sumup_oauth_callback'),

    # Artist checkout
    path('checkout/start/<int:artist_id>/', views.start_checkout, name='start_checkout'),

    # Processing endpoints
    path('process/sumup/', views.ProcessSumUpPaymentView.as_view(), name='process_sumup'),

    # Billing and subscriptions
    path('billing/run/', views.run_monthly_billing, name='run_monthly_billing'),
    path('subscription/process/<int:subscription_payment_id>/', views.process_subscription, name='process_subscription'),
    path('subscription/history/', views.subscription_history, name='subscription_history'),

    # SumUp Widget Integration
    path('widget/checkout/<int:order_id>/', widget_views.widget_checkout, name='widget_checkout'),
    path('widget/listing-fee/<int:event_id>/', widget_views.widget_listing_fee, name='widget_listing_fee'),
    path('widget/success/', widget_views.widget_success, name='widget_success'),
    path('widget/failure/', widget_views.widget_failure, name='widget_failure'),
    path('widget/cancel/', widget_views.widget_cancel, name='widget_cancel'),
    path('widget/webhook/', widget_views.widget_webhook, name='widget_webhook'),
    path('widget/status/<str:checkout_id>/', widget_views.widget_status, name='widget_status'),

    # Fixed SumUp Widget Integration (with proper X-Frame-Options)
    path('widget-fixed/checkout/<int:order_id>/', widget_views_fixed.widget_checkout_fixed, name='widget_checkout_fixed'),
    path('widget-fixed/listing-fee/<int:event_id>/', widget_views_fixed.listing_fee_widget, name='listing_fee_widget_fixed'),
    path('widget-fixed/test/', widget_views_fixed.widget_test, name='widget_test'),
]
