"""
Fixed SumUp Widget-based payment views for Jersey Events.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt, xframe_options_sameorigin
from django.contrib.auth.models import AnonymousUser

from orders.models import Order
from events.models import Event, ListingFee, ListingFeeConfig
from .models import SumUpCheckout

logger = logging.getLogger(__name__)

# Enhanced debug logger for payment views
payment_debug = logging.getLogger('payment_debug')
payment_debug.setLevel(logging.DEBUG)


@login_required
@xframe_options_exempt  # Allow this view to be embedded in SumUp iframes
def widget_checkout_fixed(request, order_id):
    """Display SumUp widget checkout page with proper X-Frame-Options handling."""
    payment_debug.info("=== FIXED WIDGET CHECKOUT DEBUG START ===")
    payment_debug.info(f"Request method: {request.method}")
    payment_debug.info(f"Order ID: {order_id}")
    payment_debug.info(f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
    payment_debug.info(f"User authenticated: {request.user.is_authenticated}")
    payment_debug.info(f"Session key: {request.session.session_key}")

    try:
        order = get_object_or_404(Order, id=order_id)
        payment_debug.info(f"Found order: {order.order_number}, user: {order.user.email if order.user else 'None'}")

        # Ensure user can access this order
        if order.user != request.user:
            payment_debug.error(f"USER MISMATCH: Order user {order.user.email if order.user else 'None'} != Request user {request.user.email}")
            messages.error(request, "You can only checkout your own orders.")
            return redirect('cart:view')

        payment_debug.info("User authorization check passed")

        # Check if order is already paid
        if order.is_paid:
            payment_debug.info("Order already paid, redirecting to success")
            messages.info(request, "This order has already been paid.")
            return redirect('payments:success')

        try:
            # Create SumUp checkout for widget (not hosted)
            payment_debug.info("Creating SumUp widget checkout...")
            from . import sumup as sumup_api

            # Create checkout WITHOUT hosted checkout enabled (for widget)
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=order.order_number,
                description=f"Jersey Events - Order {order.order_number}",
                return_url=f"{settings.SITE_URL}/payments/success/",
                redirect_url=f"{settings.SITE_URL}/payments/success/",
                enable_hosted_checkout=False  # Important: Disable hosted checkout for widget
            )

            checkout_id = checkout_data.get('id')
            payment_debug.info(f"Created checkout: {checkout_id}")

            if not checkout_id:
                payment_debug.error("No checkout ID received from SumUp")
                messages.error(request, "Failed to create payment session. Please try again.")
                return redirect('cart:view')

            # Store checkout information
            sumup_checkout, created = SumUpCheckout.objects.update_or_create(
                order=order,
                defaults={
                    'sumup_checkout_id': checkout_id,
                    'amount': order.total,
                    'currency': 'GBP',
                    'status': 'pending'
                }
            )

            payment_debug.info(f"SumUp checkout record {'created' if created else 'updated'}: {sumup_checkout.id}")

            context = {
                'order': order,
                'checkout_id': checkout_id,
                'sumup_checkout': sumup_checkout,
                'debug': settings.DEBUG,
            }

            payment_debug.info("Rendering widget template with checkout ID")
            return render(request, 'payments/widget_checkout_fixed.html', context)

        except Exception as e:
            payment_debug.error(f"Error creating SumUp checkout: {e}")
            messages.error(request, f"Payment system error: {e}")
            return redirect('cart:view')

    except Order.DoesNotExist:
        payment_debug.error(f"Order not found: {order_id}")
        messages.error(request, "Order not found.")
        return redirect('cart:view')

    except Exception as e:
        payment_debug.error(f"Unexpected error in widget checkout: {e}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('cart:view')


@csrf_exempt
@xframe_options_exempt
def widget_test(request):
    """Test page for SumUp widget integration."""
    payment_debug.info("=== WIDGET TEST PAGE ===")

    # Create a test checkout for demo purposes
    try:
        from . import sumup as sumup_api

        checkout_data = sumup_api.create_checkout_simple(
            amount=10.00,
            currency='GBP',
            reference=f"test_widget_{request.session.session_key}",
            description="Test SumUp Widget - Jersey Events",
            return_url=f"{settings.SITE_URL}/payments/success/",
            redirect_url=f"{settings.SITE_URL}/payments/success/",
            enable_hosted_checkout=False  # Widget mode
        )

        checkout_id = checkout_data.get('id')
        payment_debug.info(f"Test checkout created: {checkout_id}")

        context = {
            'checkout_id': checkout_id,
            'test_mode': True,
            'debug': settings.DEBUG,
        }

        return render(request, 'payments/widget_checkout_fixed.html', context)

    except Exception as e:
        payment_debug.error(f"Error creating test checkout: {e}")
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to create test checkout'
        }, status=500)


@login_required
@xframe_options_exempt
def listing_fee_widget(request, event_id):
    """Widget checkout for listing fees."""
    payment_debug.info("=== LISTING FEE WIDGET DEBUG START ===")

    try:
        event = get_object_or_404(Event, id=event_id)

        # Check if user owns this event
        if event.organiser != request.user:
            messages.error(request, "You can only pay listing fees for your own events.")
            return redirect('events:my_events')

        # Get listing fee configuration
        listing_config = ListingFeeConfig.objects.first()
        if not listing_config:
            messages.error(request, "Listing fee configuration not found.")
            return redirect('events:my_events')

        try:
            # Create SumUp checkout for listing fee
            from . import sumup as sumup_api

            checkout_data = sumup_api.create_checkout_simple(
                amount=float(listing_config.amount),
                currency='GBP',
                reference=f"listing_fee_{event.id}",
                description=f"Listing Fee - {event.title}",
                return_url=f"{settings.SITE_URL}/events/listing-fee/success/",
                redirect_url=f"{settings.SITE_URL}/events/listing-fee/success/",
                enable_hosted_checkout=False  # Widget mode
            )

            checkout_id = checkout_data.get('id')
            payment_debug.info(f"Created listing fee checkout: {checkout_id}")

            # Store listing fee record
            listing_fee, created = ListingFee.objects.update_or_create(
                event=event,
                defaults={
                    'amount': listing_config.amount,
                    'currency': 'GBP',
                    'sumup_checkout_id': checkout_id,
                    'payment_status': 'pending'
                }
            )

            context = {
                'event': event,
                'listing_fee': listing_fee,
                'checkout_id': checkout_id,
                'debug': settings.DEBUG,
            }

            return render(request, 'payments/widget_listing_fee_fixed.html', context)

        except Exception as e:
            payment_debug.error(f"Error creating listing fee checkout: {e}")
            messages.error(request, f"Payment system error: {e}")
            return redirect('events:my_events')

    except Event.DoesNotExist:
        payment_debug.error(f"Event not found: {event_id}")
        messages.error(request, "Event not found.")
        return redirect('events:my_events')