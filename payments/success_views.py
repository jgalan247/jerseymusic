"""
Payment success and failure handlers for SumUp hosted checkout returns.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone

from orders.models import Order
from events.models import Event, ListingFee
from .models import SumUpCheckout
from . import sumup as sumup_api

logger = logging.getLogger(__name__)

def payment_success(request):
    """
    Handle return from SumUp hosted checkout.

    SECURITY: This view is called when SumUp redirects back, but we CANNOT
    trust this redirect alone. User could manipulate the URL.

    We mark order as 'pending_verification' and polling service will verify
    payment server-side via SumUp API before issuing tickets.
    """
    order_number = request.GET.get('order')
    checkout_id = request.GET.get('checkout_id')

    logger.info(f"Payment success callback: order={order_number}, checkout_id={checkout_id}")

    # Handle order payment
    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)

            # Check if order is already completed (payment verified by polling)
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
                order.payment_notes = f"Returned from SumUp at {timezone.now()}, IP: {request.META.get('REMOTE_ADDR')}"
                order.save()

                logger.info(
                    f"Order {order_number} marked as pending_verification. "
                    f"Polling service will verify payment server-side."
                )

            # Show processing page
            return render(request, 'payments/processing.html', {
                'order': order,
                'message': 'Processing your payment...',
                'processing': True,
                'estimated_time': '5-10 minutes',
                'info': 'We are verifying your payment with the payment provider. You will receive an email confirmation with your tickets shortly.'
            })

        except Order.DoesNotExist:
            logger.error(f"Order not found for payment success: {order_number}")
            return render(request, 'payments/processing.html', {
                'error': True,
                'message': 'Order not found. Please contact support if you completed payment.'
            })

    # Generic success (no order specified)
    return render(request, 'payments/processing.html', {
        'message': 'Payment processing. Please check your email for confirmation.',
        'processing': True,
        'info': 'We are verifying your payment. You will receive confirmation shortly.'
    })

def payment_cancel(request):
    """Handle cancelled payment from SumUp hosted checkout."""
    order_number = request.GET.get('order')

    logger.info(f"Payment cancelled: order={order_number}")

    context = {
        'message': 'Payment was cancelled. You can try again or contact support if you need help.',
        'cancelled': True
    }

    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)
            context['order'] = order
            context['message'] = f'Payment for order {order_number} was cancelled. You can try again from your cart.'
        except Order.DoesNotExist:
            pass

    return render(request, 'payments/cancel.html', context)

def payment_failure(request):
    """Handle failed payment from SumUp hosted checkout."""
    order_number = request.GET.get('order')
    checkout_id = request.GET.get('checkout_id')

    logger.error(f"Payment failed: order={order_number}, checkout_id={checkout_id}")

    context = {
        'message': 'Payment failed. Please try again or contact support.',
        'failed': True
    }

    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)
            context['order'] = order
            context['message'] = f'Payment for order {order_number} failed. Please try again.'
        except Order.DoesNotExist:
            pass

    return render(request, 'payments/failure.html', context)

def process_order_payment(order, checkout_id=None):
    """Process successful order payment - generate tickets and send emails."""
    try:
        from django.db import transaction

        with transaction.atomic():
            # Mark order as paid
            order.status = 'confirmed'
            order.is_paid = True
            order.paid_at = timezone.now()
            order.save()

            logger.info(f"Order {order.order_number} marked as paid")

            # Generate tickets for each order item
            tickets_created = generate_tickets_for_order(order)

            # Send confirmation emails
            send_order_confirmation_emails(order, tickets_created)

            # Update SumUpCheckout record if it exists
            if checkout_id:
                try:
                    sumup_checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
                    sumup_checkout.status = 'paid'
                    sumup_checkout.paid_at = timezone.now()
                    sumup_checkout.save()
                except SumUpCheckout.DoesNotExist:
                    logger.warning(f"SumUpCheckout record not found for checkout_id: {checkout_id}")

            return True

    except Exception as e:
        logger.error(f"Error processing order payment for {order.order_number}: {e}")
        return False

def generate_tickets_for_order(order):
    """Generate tickets for all items in an order."""
    from events.models import Ticket

    tickets_created = []

    for order_item in order.items.all():
        event = order_item.event
        quantity = order_item.quantity

        # Create tickets for each quantity
        for i in range(quantity):
            try:
                ticket = Ticket.objects.create(
                    event=event,
                    customer=order.user,
                    order=order,
                    status='valid'
                )

                # Generate PDF ticket with QR code
                pdf_generated = ticket.generate_pdf_ticket()
                if pdf_generated:
                    logger.info(f"Generated PDF ticket for {ticket.ticket_number}")
                else:
                    logger.warning(f"Failed to generate PDF for ticket {ticket.ticket_number}")

                tickets_created.append(ticket)
                logger.info(f"Generated ticket {ticket.ticket_number} for order {order.order_number}")

            except Exception as e:
                logger.error(f"Failed to generate ticket for order {order.order_number}: {e}")
                # Continue creating other tickets even if one fails

    logger.info(f"Generated {len(tickets_created)} tickets for order {order.order_number}")
    return tickets_created

def send_order_confirmation_emails(order, tickets):
    """Send order confirmation emails to customer and notify organizers."""
    try:
        from events.email_utils import email_service

        # Send confirmation email to customer
        customer_email_sent = email_service.send_order_confirmation(order)

        if customer_email_sent:
            logger.info(f"Order confirmation email sent to {order.email}")
        else:
            logger.warning(f"Failed to send order confirmation email to {order.email}")

        # Send notifications to organizers for each event
        organizers_notified = set()
        for order_item in order.items.all():
            event = order_item.event
            organizer = event.organiser

            # Only send one notification per organizer
            if organizer.email not in organizers_notified:
                try:
                    # Get the artist profile for the notification
                    artist_profile = getattr(organizer, 'artistprofile', None)

                    if artist_profile:
                        organizer_email_sent = email_service.send_artist_notification(order, artist_profile)
                        if organizer_email_sent:
                            logger.info(f"Order notification sent to organizer {organizer.email}")
                            organizers_notified.add(organizer.email)
                        else:
                            logger.warning(f"Failed to send notification to organizer {organizer.email}")
                    else:
                        logger.warning(f"No artist profile found for organizer {organizer.email}")

                except Exception as e:
                    logger.error(f"Error sending notification to organizer {organizer.email}: {e}")

    except Exception as e:
        logger.error(f"Error sending order confirmation emails: {e}")
        # Don't raise exception - emails are not critical for order completion

@csrf_exempt
@require_http_methods(["POST"])
def sumup_webhook(request):
    """Handle SumUp webhook notifications for payment status updates."""
    try:
        import json

        # Parse webhook payload
        payload = json.loads(request.body.decode('utf-8'))
        event_type = payload.get('event_type')
        checkout_id = payload.get('id')

        logger.info(f"SumUp webhook received: {event_type} for checkout {checkout_id}")

        if event_type == 'CHECKOUT_PAID':
            # Find and process the order
            try:
                sumup_checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

                if sumup_checkout.order:
                    # Process order payment
                    if not sumup_checkout.order.is_paid:
                        success = process_order_payment(sumup_checkout.order, checkout_id)
                        if success:
                            logger.info(f"Order {sumup_checkout.order.order_number} processed via webhook")
                        else:
                            logger.error(f"Failed to process order via webhook: {checkout_id}")
                else:
                    # Check for listing fee
                    try:
                        listing_fee = ListingFee.objects.get(sumup_checkout_id=checkout_id)
                        if not listing_fee.is_paid:
                            listing_fee.payment_status = 'paid'
                            listing_fee.paid_at = timezone.now()
                            listing_fee.save()

                            # Publish the event
                            if listing_fee.event.status == 'draft':
                                listing_fee.event.status = 'published'
                                listing_fee.event.save()

                            logger.info(f"Listing fee paid via webhook for event {listing_fee.event.id}")
                    except ListingFee.DoesNotExist:
                        logger.warning(f"No listing fee found for checkout {checkout_id}")

            except SumUpCheckout.DoesNotExist:
                logger.error(f"SumUpCheckout not found for webhook: {checkout_id}")

        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"Error processing SumUp webhook: {e}")
        return HttpResponse("Error", status=400)