"""
SumUp Widget-based payment views for Jersey Events.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth.models import AnonymousUser

from orders.models import Order
from events.models import Event, ListingFee, ListingFeeConfig
from .widget_service import SumUpWidgetService

logger = logging.getLogger(__name__)

# Enhanced debug logger for payment views
payment_debug = logging.getLogger('payment_debug')
payment_debug.setLevel(logging.DEBUG)


@login_required
@xframe_options_exempt
def widget_checkout(request, order_id):
    """Display SumUp widget checkout page for an order."""
    payment_debug.info("=== WIDGET CHECKOUT DEBUG START ===")
    payment_debug.info(f"Request method: {request.method}")
    payment_debug.info(f"Order ID: {order_id}")
    payment_debug.info(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    payment_debug.info(f"User authenticated: {request.user.is_authenticated}")
    payment_debug.info(f"Session key: {request.session.session_key}")

    try:
        order = get_object_or_404(Order, id=order_id)
        payment_debug.info(f"Found order: {order.order_number}, user: {order.user.username if order.user else 'None'}")

        # Ensure user can access this order
        if order.user != request.user:
            payment_debug.error(f"USER MISMATCH: Order user {order.user.username if order.user else 'None'} != Request user {request.user.username}")
            messages.error(request, "You can only checkout your own orders.")
            return redirect('cart:view')

        payment_debug.info("User authorization check passed")

        try:
            # Create hosted checkout
            payment_debug.info("Creating hosted checkout...")
            from . import sumup as sumup_api

            hosted_checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=f"order_{order.order_number}",
                description=f"Jersey Events: Order {order.order_number}",
                return_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}",
                redirect_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}",
                enable_hosted_checkout=True
            )

            hosted_url = hosted_checkout_data.get('hosted_checkout_url')
            if not hosted_url:
                # Fallback URL construction
                checkout_id = hosted_checkout_data.get('id')
                if checkout_id:
                    hosted_url = f"https://checkout.sumup.com/pay/{checkout_id}"

            payment_debug.info(f"Hosted checkout created: {hosted_checkout_data.get('id')}")
            payment_debug.info(f"Hosted URL: {hosted_url}")

            if hosted_url:
                # Render redirect page that immediately redirects to SumUp
                context = {
                    'order': order,
                    'hosted_checkout_url': hosted_url,
                }
                payment_debug.info("Rendering hosted checkout redirect template")
                return render(request, 'payments/widget_checkout.html', context)
            else:
                messages.error(request, "Unable to create payment checkout. Please try again.")
                return redirect('cart:view')

        except ValueError as e:
            # User-friendly error messages from the service layer
            payment_debug.error(f"PAYMENT SERVICE ERROR: {e}")
            payment_debug.error(f"Error details: order_id={order_id}, user={request.user.username}")
            messages.error(request, str(e))
            return redirect('cart:view')
        except Exception as e:
            payment_debug.error(f"UNEXPECTED PAYMENT ERROR: {type(e).__name__}: {e}")
            payment_debug.error(f"Error details: order_id={order_id}, user={request.user.username}")
            logger.error(f"Widget checkout creation failed for order {order_id}: {e}")
            messages.error(request, "An unexpected error occurred. Please try again or contact support.")
            return redirect('cart:view')

    except Exception as e:
        payment_debug.error(f"CHECKOUT VIEW ERROR: {type(e).__name__}: {e}")
        payment_debug.error(f"Error in widget_checkout view for order_id={order_id}")
        logger.error(f"Widget checkout view failed for order {order_id}: {e}")
        messages.error(request, "Payment page could not be loaded. Please try again.")
        return redirect('cart:view')


def widget_listing_fee(request, event_id):
    """Display SumUp widget checkout page for listing fee."""
    event = get_object_or_404(Event, id=event_id)

    # Ensure user is the organizer
    if not request.user.is_authenticated or event.organiser != request.user:
        messages.error(request, "You can only pay listing fees for your own events.")
        return redirect('events:event_detail', pk=event.id)

    try:
        # Get or create listing fee
        listing_fee, created = ListingFee.objects.get_or_create(
            event=event,
            defaults={
                'organizer': request.user,
                'amount': ListingFeeConfig.get_config().standard_fee
            }
        )

        # Check if already paid
        if listing_fee.is_paid:
            messages.info(request, "Listing fee has already been paid for this event.")
            return redirect('events:event_detail', pk=event.id)

        # Create checkout for widget
        widget_service = SumUpWidgetService()
        checkout, checkout_data = widget_service.create_checkout_for_widget(listing_fee=listing_fee)

        # Get widget configuration
        widget_config = widget_service.get_widget_config(checkout)

        context = {
            'event': event,
            'listing_fee': listing_fee,
            'checkout': checkout,
            'widget_config': widget_config
        }

        return render(request, 'payments/widget_listing_fee.html', context)

    except Exception as e:
        logger.error(f"Widget listing fee checkout creation failed for event {event_id}: {e}")
        messages.error(request, "Payment setup failed. Please try again.")
        return redirect('events:event_detail', pk=event.id)


def widget_success(request):
    """Handle successful payment from SumUp widget."""
    payment_debug.info("=== WIDGET SUCCESS DEBUG START ===")
    payment_debug.info(f"Request method: {request.method}")
    payment_debug.info(f"GET parameters: {dict(request.GET)}")
    payment_debug.info(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    payment_debug.info(f"User authenticated: {request.user.is_authenticated}")

    checkout_id = request.GET.get('checkout_id') or request.GET.get('id')
    payment_debug.info(f"Extracted checkout_id: {checkout_id}")

    if not checkout_id:
        payment_debug.error("No checkout_id found in request parameters")
        messages.error(request, "Invalid payment confirmation.")
        return redirect('events:home')

    try:
        payment_debug.info("Creating widget service for success handling...")
        widget_service = SumUpWidgetService()

        payment_debug.info(f"Calling handle_widget_success with checkout_id: {checkout_id}")
        result = widget_service.handle_widget_success(checkout_id, request)
        payment_debug.info(f"Success handler result: {result}")

        if result['success']:
            payment_debug.info(f"Payment success confirmed for type: {result['type']}")

            if result['type'] == 'order':
                order = result['order']
                payment_debug.info(f"Order payment success: {order.order_number}, redirecting to home with message")
                messages.success(request, f"Payment successful! Order {order.order_number} confirmed. Check your email for tickets.")
                # Redirect to home instead of order detail to avoid URL issues
                return redirect('events:home')

            elif result['type'] == 'listing_fee':
                event = result['event']
                payment_debug.info(f"Listing fee payment success: {event.title}, redirecting to event detail")
                messages.success(request, f"Listing fee paid! Your event '{event.title}' is now published.")
                return redirect('events:event_detail', pk=event.id)

            else:
                payment_debug.info(f"Generic payment success, redirecting to home")
                messages.success(request, "Payment completed successfully!")
                return redirect('events:home')

        else:
            payment_debug.error(f"Payment confirmation failed: {result.get('error', 'Unknown error')}")
            messages.error(request, f"Payment confirmation failed: {result.get('error', 'Unknown error')}")
            return redirect('events:home')

    except Exception as e:
        payment_debug.error(f"WIDGET SUCCESS ERROR: {type(e).__name__}: {e}")
        payment_debug.error(f"Error in widget_success for checkout_id: {checkout_id}")
        logger.error(f"Widget success handling error: {e}")
        messages.error(request, "Payment confirmation failed. Please contact support if you were charged.")
        return redirect('events:home')


def widget_failure(request):
    """Handle failed payment from SumUp widget."""
    payment_debug.info("=== WIDGET FAILURE DEBUG ===")
    payment_debug.info(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    payment_debug.info(f"GET parameters: {dict(request.GET)}")

    # Extract any error information from the request
    error_code = request.GET.get('error_code')
    error_message = request.GET.get('error_message')
    checkout_id = request.GET.get('checkout_id')

    payment_debug.error(f"Payment failure - checkout_id: {checkout_id}, error_code: {error_code}, error_message: {error_message}")

    # Provide user-friendly error message
    if error_code:
        messages.error(request, f"Payment failed: {error_message or 'Unknown error'}. Please try again or use a different payment method.")
    else:
        messages.error(request, "Payment was not completed. Please try again.")

    return redirect('cart:view')


def widget_cancel(request):
    """Handle cancelled payment from SumUp widget."""
    payment_debug.info("=== WIDGET CANCEL DEBUG ===")
    payment_debug.info(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    payment_debug.info(f"GET parameters: {dict(request.GET)}")

    checkout_id = request.GET.get('checkout_id')
    payment_debug.info(f"Payment cancelled - checkout_id: {checkout_id}")

    messages.info(request, "Payment was cancelled. You can try again anytime.")
    return redirect('cart:view')


@csrf_exempt
def widget_webhook(request):
    """Handle webhook notifications from SumUp widget payments."""
    # Widget payments are handled via the success URL redirect
    # This endpoint is here for any additional webhook processing if needed
    return JsonResponse({'status': 'ok'})


def widget_status(request, checkout_id):
    """Check payment status for a widget checkout."""
    try:
        from .models import SumUpCheckout
        checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

        return JsonResponse({
            'checkout_id': checkout_id,
            'status': checkout.status,
            'paid': checkout.status == 'paid',
            'amount': float(checkout.amount),
            'currency': checkout.currency
        })

    except SumUpCheckout.DoesNotExist:
        return JsonResponse({
            'error': 'Checkout not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Widget status check error: {e}")
        return JsonResponse({
            'error': 'Status check failed'
        }, status=500)