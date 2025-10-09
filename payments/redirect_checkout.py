"""
Clean redirect-based SumUp payment implementation.
No widgets, no iframes, no X-Frame-Options issues.
Simple flow: Create checkout → Redirect to SumUp → Handle return.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required

from orders.models import Order
from events.models import Event, ListingFee, ListingFeeConfig, Ticket
from .models import SumUpCheckout
from . import sumup as sumup_api

logger = logging.getLogger(__name__)


def create_order_checkout(request, order_id):
    """
    Create a SumUp checkout for an order and redirect directly to SumUp.
    No widget, no iframe - just a clean redirect.
    """
    logger.info(f"Creating redirect checkout for order {order_id}")

    try:
        # Get the order
        order = get_object_or_404(Order, id=order_id)

        # Security check - allow both authenticated users and session-based orders
        if request.user.is_authenticated:
            if order.user and order.user != request.user:
                messages.error(request, "You cannot checkout another user's order.")
                return redirect('cart:view')
        else:
            # For anonymous users, check session
            session_order_id = request.session.get('order_id')
            if session_order_id != order.id:
                messages.error(request, "Order not found in your session.")
                return redirect('cart:view')

        # Check if order is already paid
        if order.is_paid:
            messages.info(request, "This order has already been paid.")
            from django.urls import reverse
            return redirect(reverse('payments:redirect_success') + f'?order={order.order_number}')

        # Create SumUp checkout
        try:
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=order.order_number,
                description=f"Jersey Events - Order {order.order_number}",
                return_url=f"{settings.SITE_URL}/payments/redirect/success/?order={order.order_number}",
                redirect_url=f"{settings.SITE_URL}/payments/redirect/success/?order={order.order_number}",
                enable_hosted_checkout=True  # Use hosted checkout for direct redirect
            )

            checkout_id = checkout_data.get('id')
            hosted_url = checkout_data.get('hosted_checkout_url')

            # Fallback URL construction if not provided
            if not hosted_url and checkout_id:
                hosted_url = f"https://checkout.sumup.com/pay/c-{checkout_id}"

            if not hosted_url:
                logger.error(f"No hosted URL returned for checkout {checkout_id}")
                messages.error(request, "Unable to create payment session. Please try again.")
                return redirect('cart:view')

            # Store checkout record
            SumUpCheckout.objects.update_or_create(
                order=order,
                defaults={
                    'sumup_checkout_id': checkout_id,
                    'amount': order.total,
                    'currency': 'GBP',
                    'status': 'pending'
                }
            )

            logger.info(f"Redirecting to SumUp checkout: {hosted_url}")

            # Direct redirect to SumUp hosted checkout
            return redirect(hosted_url)

        except Exception as e:
            logger.error(f"SumUp checkout creation failed: {e}")
            messages.error(request, "Payment system error. Please try again.")
            return redirect('cart:view')

    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('cart:view')


def redirect_success(request):
    """
    Handle successful payment return from SumUp.
    Process order, generate tickets, send emails.
    """
    order_number = request.GET.get('order')
    checkout_id = request.GET.get('checkout_id')

    logger.info(f"Payment success return: order={order_number}, checkout={checkout_id}")

    if not order_number:
        messages.warning(request, "No order specified in return URL.")
        return redirect('events:events_list')

    try:
        order = Order.objects.get(order_number=order_number)

        # Check if already processed
        if order.is_paid:
            logger.info(f"Order {order_number} already paid")
            return render(request, 'payments/redirect_success.html', {
                'order': order,
                'already_paid': True,
                'tickets': order.tickets.all()
            })

        # Process the payment
        with transaction.atomic():
            # Mark order as paid
            order.is_paid = True
            order.status = 'confirmed'
            order.paid_at = timezone.now()
            order.save()

            # Update checkout record if exists
            if checkout_id:
                try:
                    checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
                    checkout.status = 'paid'
                    checkout.paid_at = timezone.now()
                    checkout.save()
                except SumUpCheckout.DoesNotExist:
                    pass

            # Generate tickets
            tickets = generate_tickets_for_order(order)

            # Send confirmation emails
            send_confirmation_emails(order, tickets)

            logger.info(f"Order {order_number} processed successfully")

            return render(request, 'payments/redirect_success.html', {
                'order': order,
                'success': True,
                'tickets': tickets
            })

    except Order.DoesNotExist:
        logger.error(f"Order not found: {order_number}")
        messages.error(request, "Order not found.")
        return redirect('events:events_list')
    except Exception as e:
        logger.error(f"Error processing payment success: {e}")
        messages.error(request, "Error processing payment. Please contact support.")
        return redirect('cart:view')


def redirect_cancel(request):
    """
    Handle cancelled payment return from SumUp.
    Allow user to retry payment.
    """
    order_number = request.GET.get('order')

    logger.info(f"Payment cancelled: order={order_number}")

    context = {
        'cancelled': True,
        'message': 'Payment was cancelled.'
    }

    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)
            context['order'] = order
            context['can_retry'] = True
        except Order.DoesNotExist:
            pass

    return render(request, 'payments/redirect_cancel.html', context)


def generate_tickets_for_order(order):
    """Generate tickets for all items in the order."""
    tickets = []

    for order_item in order.items.all():
        event = order_item.event
        quantity = order_item.quantity

        for i in range(quantity):
            try:
                ticket = Ticket.objects.create(
                    event=event,
                    customer=order.user,
                    order=order,
                    status='valid'
                )

                # Generate PDF with QR code
                if hasattr(ticket, 'generate_pdf_ticket'):
                    ticket.generate_pdf_ticket()

                tickets.append(ticket)
                logger.info(f"Generated ticket {ticket.ticket_number}")

            except Exception as e:
                logger.error(f"Failed to generate ticket: {e}")

    return tickets


def send_confirmation_emails(order, tickets):
    """Send order confirmation emails."""
    try:
        from events.email_utils import email_service

        # Send to customer
        email_service.send_order_confirmation(order)

        # Notify organizers
        organizers_notified = set()
        for item in order.items.all():
            organizer = item.event.organiser
            if organizer.email not in organizers_notified:
                try:
                    artist_profile = getattr(organizer, 'artistprofile', None)
                    if artist_profile:
                        email_service.send_artist_notification(order, artist_profile)
                        organizers_notified.add(organizer.email)
                except Exception as e:
                    logger.error(f"Failed to notify organizer: {e}")

    except Exception as e:
        logger.error(f"Error sending confirmation emails: {e}")
        # Don't fail the order if emails fail


def create_listing_fee_checkout(request, event_id):
    """
    Create a SumUp checkout for event listing fee and redirect.
    """
    logger.info(f"Creating listing fee checkout for event {event_id}")

    try:
        event = get_object_or_404(Event, id=event_id)

        # Security check
        if request.user != event.organiser:
            messages.error(request, "You can only pay listing fees for your own events.")
            return redirect('events:my_events')

        # Get listing fee config
        config = ListingFeeConfig.objects.first()
        if not config:
            messages.error(request, "Listing fee configuration not found.")
            return redirect('events:my_events')

        # Create SumUp checkout
        try:
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(config.amount),
                currency='GBP',
                reference=f"listing_fee_{event.id}",
                description=f"Listing Fee - {event.title}",
                return_url=f"{settings.SITE_URL}/payments/redirect/listing-success/?event={event.id}",
                redirect_url=f"{settings.SITE_URL}/payments/redirect/listing-success/?event={event.id}",
                enable_hosted_checkout=True
            )

            checkout_id = checkout_data.get('id')
            hosted_url = checkout_data.get('hosted_checkout_url')

            if not hosted_url and checkout_id:
                hosted_url = f"https://checkout.sumup.com/pay/c-{checkout_id}"

            if not hosted_url:
                messages.error(request, "Unable to create payment session.")
                return redirect('events:my_events')

            # Store listing fee record
            ListingFee.objects.update_or_create(
                event=event,
                defaults={
                    'amount': config.amount,
                    'currency': 'GBP',
                    'sumup_checkout_id': checkout_id,
                    'payment_status': 'pending'
                }
            )

            # Redirect to SumUp
            return redirect(hosted_url)

        except Exception as e:
            logger.error(f"Listing fee checkout failed: {e}")
            messages.error(request, "Payment system error.")
            return redirect('events:my_events')

    except Event.DoesNotExist:
        messages.error(request, "Event not found.")
        return redirect('events:my_events')


def redirect_listing_success(request):
    """Handle successful listing fee payment."""
    event_id = request.GET.get('event')
    checkout_id = request.GET.get('checkout_id')

    if not event_id:
        messages.warning(request, "No event specified.")
        return redirect('events:my_events')

    try:
        event = Event.objects.get(id=event_id)

        # Process listing fee payment
        with transaction.atomic():
            listing_fee = ListingFee.objects.get(event=event)
            listing_fee.payment_status = 'paid'
            listing_fee.paid_at = timezone.now()
            listing_fee.save()

            # Publish event
            event.status = 'published'
            event.save()

            messages.success(request, f"Listing fee paid! Your event '{event.title}' is now published.")

        return redirect('events:event_detail', slug=event.slug)

    except (Event.DoesNotExist, ListingFee.DoesNotExist):
        messages.error(request, "Payment record not found.")
        return redirect('events:my_events')
    except Exception as e:
        logger.error(f"Error processing listing fee payment: {e}")
        messages.error(request, "Error processing payment.")
        return redirect('events:my_events')