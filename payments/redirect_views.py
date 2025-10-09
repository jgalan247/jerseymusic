"""
Alternative payment views using direct SumUp hosted checkout redirects.
More reliable than widget embedding for some scenarios.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

from . import sumup as sumup_api
from .widget_service import SumUpWidgetService
from .models import SumUpCheckout
from orders.models import Order
from events.models import ListingFee

logger = logging.getLogger(__name__)

@login_required
def checkout_hosted_redirect(request, order_id=None, listing_fee_id=None):
    """Create a SumUp hosted checkout and redirect customer directly to SumUp."""
    try:
        widget_service = SumUpWidgetService()

        if order_id:
            # Customer order checkout
            order = get_object_or_404(Order, id=order_id, user=request.user)

            # Create checkout with hosted redirect enabled
            checkout, checkout_data = widget_service.create_checkout_for_widget(order=order)

            # Create hosted checkout version
            hosted_checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=f"hosted_order_{order.order_number}",
                description=f"Jersey Events: Order {order.order_number}",
                return_url=f"{settings.SITE_URL}/payments/redirect/success/?order={order.order_number}",
                redirect_url=f"{settings.SITE_URL}/payments/redirect/success/?order={order.order_number}",
                enable_hosted_checkout=True
            )

            # Check if we got a hosted checkout URL
            hosted_url = hosted_checkout_data.get('hosted_checkout_url')
            if hosted_url:
                logger.info(f"Redirecting to hosted checkout: {hosted_url}")
                return redirect(hosted_url)
            else:
                # Fallback to checkout URL construction
                checkout_id = hosted_checkout_data.get('id')
                if checkout_id:
                    hosted_url = f"https://checkout.sumup.com/pay/{checkout_id}"
                    logger.info(f"Using constructed hosted URL: {hosted_url}")
                    return redirect(hosted_url)

        elif listing_fee_id:
            # Listing fee checkout
            listing_fee = get_object_or_404(ListingFee, id=listing_fee_id, organizer=request.user)

            # Create checkout with hosted redirect enabled
            checkout, checkout_data = widget_service.create_checkout_for_widget(listing_fee=listing_fee)

            # Create hosted checkout version
            hosted_checkout_data = sumup_api.create_checkout_simple(
                amount=float(listing_fee.amount),
                currency=listing_fee.currency,
                reference=f"hosted_{listing_fee.payment_reference}",
                description=f"Jersey Events - Listing fee for '{listing_fee.event.title}'",
                return_url=f"{settings.SITE_URL}/events/event/{listing_fee.event.id}/listing-fee/success/",
                redirect_url=f"{settings.SITE_URL}/events/event/{listing_fee.event.id}/listing-fee/success/",
                enable_hosted_checkout=True
            )

            # Check if we got a hosted checkout URL
            hosted_url = hosted_checkout_data.get('hosted_checkout_url')
            if hosted_url:
                logger.info(f"Redirecting to hosted checkout: {hosted_url}")
                return redirect(hosted_url)
            else:
                # Fallback to checkout URL construction
                checkout_id = hosted_checkout_data.get('id')
                if checkout_id:
                    hosted_url = f"https://checkout.sumup.com/pay/{checkout_id}"
                    logger.info(f"Using constructed hosted URL: {hosted_url}")
                    return redirect(hosted_url)

        # If we get here, something went wrong
        messages.error(request, "Unable to create payment checkout. Please try again.")
        return redirect('cart:view')

    except Exception as e:
        logger.error(f"Hosted checkout error: {e}")
        messages.error(request, "Payment system error. Please try again or contact support.")
        return redirect('cart:view')

def redirect_success(request):
    """
    Handle return from SumUp hosted checkout.

    SECURITY: This view is called when SumUp redirects back, but we CANNOT
    trust this redirect alone. User could manipulate the URL.

    We mark order as 'pending_verification' and polling service will verify
    payment server-side via SumUp API before issuing tickets.
    """
    order_number = request.GET.get('order')
    checkout_id = request.GET.get('checkout_id')

    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)

            # Check if order is already completed (payment verified)
            if order.status == 'completed' and order.is_paid:
                return render(request, 'payments/processing.html', {
                    'order': order,
                    'message': 'Payment already verified! Your tickets have been sent.',
                    'already_completed': True,
                    'processing_complete': True
                })

            # SECURITY: Do NOT mark as paid yet!
            # Mark as pending verification - polling will verify server-side
            if order.status != 'pending_verification':
                order.status = 'pending_verification'
                order.payment_notes = f"Returned from SumUp redirect at {request.META.get('REMOTE_ADDR')}"
                order.save()

                logger.info(
                    f"Order {order_number} marked as pending_verification. "
                    f"Polling service will verify payment."
                )

            # Show processing page (not success!)
            return render(request, 'payments/processing.html', {
                'order': order,
                'message': 'Processing your payment...',
                'processing': True,
                'estimated_time': '5-10 minutes'
            })

        except Order.DoesNotExist:
            logger.error(f"Order not found for hosted checkout return: {order_number}")
            return render(request, 'payments/processing.html', {
                'error': True,
                'message': 'Order not found. Please contact support if you completed payment.'
            })

    # No order number in URL
    return render(request, 'payments/processing.html', {
        'message': 'Payment processing. Please check your email for confirmation.',
        'processing': True
    })

def redirect_cancel(request):
    """Handle cancelled payment from SumUp hosted checkout."""
    return render(request, 'payments/cancel.html', {
        'message': 'Payment was cancelled. You can try again or contact support if you need help.',
        'cancelled': True
    })

@require_http_methods(["GET"])
def payment_method_choice(request, order_id=None, listing_fee_id=None):
    """Let customer choose between widget integration or hosted redirect."""
    context = {}

    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        context.update({
            'order': order,
            'amount': order.total,
            'description': f"Order {order.order_number}",
            'widget_url': f"/payments/widget/checkout/?order={order_id}",
            'redirect_url': f"/payments/redirect/checkout/?order={order_id}",
        })

    elif listing_fee_id:
        listing_fee = get_object_or_404(ListingFee, id=listing_fee_id, organizer=request.user)
        context.update({
            'listing_fee': listing_fee,
            'event': listing_fee.event,
            'amount': listing_fee.amount,
            'description': f"Listing fee for {listing_fee.event.title}",
            'widget_url': f"/events/event/{listing_fee.event.id}/listing-fee/widget/",
            'redirect_url': f"/payments/redirect/checkout/?listing_fee={listing_fee_id}",
        })

    return render(request, 'payments/payment_method_choice.html', context)

@require_http_methods(["POST"])
def test_hosted_checkout(request):
    """Test endpoint for creating hosted checkouts."""
    try:
        amount = request.POST.get('amount', '25.00')
        description = request.POST.get('description', 'Test payment')

        checkout_data = sumup_api.create_checkout_simple(
            amount=float(amount),
            currency='GBP',
            reference=f"test_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            description=description,
            return_url=f"{settings.SITE_URL}/payments/redirect/success/",
            redirect_url=f"{settings.SITE_URL}/payments/redirect/success/",
            enable_hosted_checkout=True
        )

        hosted_url = checkout_data.get('hosted_checkout_url')
        checkout_id = checkout_data.get('id')

        return JsonResponse({
            'success': True,
            'checkout_id': checkout_id,
            'hosted_url': hosted_url,
            'fallback_url': f"https://checkout.sumup.com/pay/{checkout_id}" if checkout_id else None,
            'data': checkout_data
        })

    except Exception as e:
        logger.error(f"Test hosted checkout error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)