"""
SumUp Widget-based payment service for Jersey Events.
Much simpler than OAuth API - uses embedded widgets.
"""

import logging
import uuid
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

from . import sumup as sumup_api
from .models import SumUpCheckout
from orders.models import Order
from events.models import Event, ListingFee

logger = logging.getLogger(__name__)

# Enhanced debug logger for payment flow
debug_logger = logging.getLogger('payment_debug')
debug_logger.setLevel(logging.DEBUG)


class SumUpWidgetService:
    """Simplified service for SumUp widget-based payments."""

    def __init__(self):
        self.platform_fee_percentage = getattr(settings, 'PLATFORM_FEE_PERCENTAGE', 5.0)

    def create_checkout_for_widget(self, order=None, listing_fee=None, merchant_code=None, amount=None, description=None):
        """Create a SumUp checkout for widget integration."""
        debug_logger.info("=== PAYMENT DEBUG: Creating checkout for widget ===")
        debug_logger.info(f"Parameters: order={order.order_number if order else None}, listing_fee={listing_fee.id if listing_fee else None}, merchant_code={merchant_code}")

        try:
            if order:
                debug_logger.info(f"Processing CUSTOMER ORDER checkout for order {order.order_number}")
                # Customer ticket purchase - route to organizer or platform
                return self._create_order_checkout(order)
            elif listing_fee:
                debug_logger.info(f"Processing LISTING FEE checkout for event {listing_fee.event.title}")
                # Listing fee payment - always to platform
                return self._create_listing_fee_checkout(listing_fee)
            else:
                debug_logger.info(f"Processing CUSTOM checkout with amount {amount}")
                # Custom checkout
                return self._create_custom_checkout(merchant_code, amount, description)
        except Exception as e:
            debug_logger.error(f"PAYMENT DEBUG: Checkout creation failed - {type(e).__name__}: {e}")
            debug_logger.error(f"PAYMENT DEBUG: Parameters at failure - order: {order}, listing_fee: {listing_fee}")
            raise

    def _create_order_checkout(self, order):
        """Create checkout for customer ticket purchase."""
        debug_logger.info(f"=== ORDER CHECKOUT DEBUG: Processing order {order.order_number} ===")
        debug_logger.info(f"Order details: user={order.user.username if order.user else 'Anonymous'}, total=£{order.total}, status={order.status}")

        # Get the event and organizer
        first_item = order.items.first()
        if not first_item or not first_item.event:
            debug_logger.error("PAYMENT DEBUG: Order has no items or event")
            raise ValueError("Order must have at least one event item")

        event = first_item.event
        organizer = event.organiser
        debug_logger.info(f"Event: {event.title}, Organizer: {organizer.username}")

        # Check if organizer has merchant code
        organizer_merchant_code = None
        if hasattr(organizer, 'artistprofile') and organizer.artistprofile:
            organizer_merchant_code = organizer.artistprofile.sumup_merchant_code
            debug_logger.info(f"Found artist profile with merchant code: {organizer_merchant_code or 'EMPTY'}")
        else:
            debug_logger.warning(f"No artist profile found for organizer {organizer.username}")

        # Log the merchant code routing decision
        if organizer_merchant_code:
            debug_logger.info(f"✅ ROUTING: Using organizer merchant code: {organizer_merchant_code} for event {event.title}")
            logger.info(f"Using organizer merchant code: {organizer_merchant_code} for event {event.title}")
        else:
            debug_logger.info(f"⚠️ ROUTING: No organizer merchant code found, using platform code for event {event.title}")
            logger.info(f"No organizer merchant code found, using platform code for event {event.title}")

        # Use organizer merchant code if available, otherwise platform
        merchant_code = organizer_merchant_code or settings.SUMUP_MERCHANT_CODE or 'M28WNZCB'
        debug_logger.info(f"Final merchant code: {merchant_code}")

        # Create description
        event_titles = [item.event.title for item in order.items.all()[:3]]
        description = f"Jersey Events: {', '.join(event_titles)}"
        if order.items.count() > 3:
            description += f" +{order.items.count() - 3} more"

        # Calculate amounts
        if organizer_merchant_code:
            # Direct to organizer - they get full amount, owe us platform fee later
            checkout_amount = order.total
            payment_type = 'direct_to_organizer'
        else:
            # To platform - we'll pay out organizer later
            checkout_amount = order.total
            payment_type = 'platform_collection'

        try:
            debug_logger.info(f"Creating SumUp checkout with amount: £{checkout_amount}, merchant: {merchant_code}")
            debug_logger.info(f"SumUp API call parameters: amount={float(checkout_amount)}, currency=GBP, reference=order_{order.order_number}")

            # Create SumUp checkout via API
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(checkout_amount),
                currency='GBP',
                reference=f"order_{order.order_number}",
                description=description[:255],
                return_url=f"{settings.SITE_URL}/payments/widget/success/?order={order.order_number}",
                redirect_url=f"{settings.SITE_URL}/payments/widget/success/?order={order.order_number}"
            )
            debug_logger.info(f"SumUp checkout created successfully: {checkout_data.get('id', 'NO_ID')}")

            # Create local tracking record
            checkout = SumUpCheckout.objects.create(
                order=order,
                customer=order.user,
                artist=organizer if organizer_merchant_code else None,
                amount=checkout_amount,
                currency='GBP',
                description=description[:255],
                merchant_code=merchant_code,
                checkout_reference=f"order_{order.order_number}",
                sumup_checkout_id=checkout_data.get('id', ''),
                return_url=f"{settings.SITE_URL}/payments/widget/success/?order={order.order_number}",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(f"Created order checkout for widget: {checkout.sumup_checkout_id}, type: {payment_type}")
            return checkout, checkout_data

        except ConnectionError as e:
            debug_logger.error(f"NETWORK ERROR: Cannot connect to SumUp API - {e}")
            raise ValueError("Payment service is currently unavailable. Please try again later.")
        except requests.exceptions.Timeout as e:
            debug_logger.error(f"TIMEOUT ERROR: SumUp API request timed out - {e}")
            raise ValueError("Payment service is taking too long to respond. Please try again.")
        except requests.exceptions.RequestException as e:
            debug_logger.error(f"REQUEST ERROR: SumUp API request failed - {e}")
            raise ValueError("Payment service error. Please try again.")
        except KeyError as e:
            debug_logger.error(f"API RESPONSE ERROR: Missing required field in SumUp response - {e}")
            raise ValueError("Invalid response from payment service. Please try again.")
        except Exception as e:
            debug_logger.error(f"CHECKOUT CREATION ERROR: {type(e).__name__}: {e}")
            logger.error(f"Failed to create order checkout for widget: {e}")
            raise ValueError("Payment setup failed. Please try again or contact support.")

    def _create_listing_fee_checkout(self, listing_fee):
        """Create checkout for listing fee payment (always to platform)."""
        event = listing_fee.event
        description = f"Jersey Events - Listing fee for '{event.title}'"

        try:
            # Create SumUp checkout via API (using platform merchant code)
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(listing_fee.amount),
                currency=listing_fee.currency,
                reference=listing_fee.payment_reference,
                description=description,
                return_url=f"{settings.SITE_URL}/events/event/{event.id}/listing-fee/success/",
                redirect_url=f"{settings.SITE_URL}/events/event/{event.id}/listing-fee/success/"
            )

            # Update listing fee with checkout ID
            listing_fee.sumup_checkout_id = checkout_data.get('id', '')
            listing_fee.payment_data = checkout_data
            listing_fee.save()

            # Create SumUpCheckout record for tracking
            checkout = SumUpCheckout.objects.create(
                order=None,  # This is for listing fees, not orders
                customer=listing_fee.organizer,
                amount=listing_fee.amount,
                currency=listing_fee.currency,
                description=description,
                merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
                checkout_reference=listing_fee.payment_reference,
                sumup_checkout_id=checkout_data.get('id', ''),
                return_url=f"{settings.SITE_URL}/events/event/{event.id}/listing-fee/success/",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(f"Created listing fee checkout for widget: {checkout.sumup_checkout_id}")
            return checkout, checkout_data

        except Exception as e:
            logger.error(f"Failed to create listing fee checkout for widget: {e}")
            raise

    def _create_custom_checkout(self, merchant_code, amount, description):
        """Create custom checkout."""
        if not merchant_code or not amount or not description:
            raise ValueError("merchant_code, amount, and description are required for custom checkout")

        try:
            checkout_ref = f"custom_{uuid.uuid4().hex[:8]}"

            checkout_data = sumup_api.create_checkout_simple(
                amount=float(amount),
                currency='GBP',
                reference=checkout_ref,
                description=description,
                return_url=f"{settings.SITE_URL}/payments/widget/success/",
                redirect_url=f"{settings.SITE_URL}/payments/widget/success/"
            )

            checkout = SumUpCheckout.objects.create(
                order=None,
                customer=None,
                amount=Decimal(str(amount)),
                currency='GBP',
                description=description,
                merchant_code=merchant_code,
                checkout_reference=checkout_ref,
                sumup_checkout_id=checkout_data.get('id', ''),
                return_url=f"{settings.SITE_URL}/payments/widget/success/",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(f"Created custom checkout for widget: {checkout.sumup_checkout_id}")
            return checkout, checkout_data

        except Exception as e:
            logger.error(f"Failed to create custom checkout for widget: {e}")
            raise

    def handle_widget_success(self, checkout_id, request):
        """Handle successful payment from widget."""
        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

            # Update checkout status
            checkout.status = 'paid'
            checkout.paid_at = timezone.now()
            checkout.save()

            # Handle different types of payments
            if checkout.order:
                # Customer order payment
                order = checkout.order
                order.status = 'confirmed'
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()

                logger.info(f"Order {order.order_number} marked as paid via widget")

                # Generate tickets for each order item
                tickets = self._generate_tickets_for_order(order)

                # Send confirmation emails
                self._send_order_confirmation_emails(order, tickets)

                return {
                    'type': 'order',
                    'order': order,
                    'success': True
                }

            else:
                # Check if it's a listing fee
                try:
                    listing_fee = ListingFee.objects.get(sumup_checkout_id=checkout_id)
                    listing_fee.payment_status = 'paid'
                    listing_fee.paid_at = timezone.now()
                    listing_fee.save()

                    # Publish the event
                    event = listing_fee.event
                    if event.status == 'draft':
                        event.status = 'published'
                        event.save()

                    logger.info(f"Listing fee paid for event {event.id}, event published")

                    return {
                        'type': 'listing_fee',
                        'event': event,
                        'listing_fee': listing_fee,
                        'success': True
                    }

                except ListingFee.DoesNotExist:
                    # Generic payment
                    logger.info(f"Generic payment completed: {checkout_id}")
                    return {
                        'type': 'generic',
                        'checkout': checkout,
                        'success': True
                    }

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Widget success: Checkout not found for ID {checkout_id}")
            return {'success': False, 'error': 'Checkout not found'}
        except Exception as e:
            logger.error(f"Widget success handling error: {e}")
            return {'success': False, 'error': str(e)}

    def get_widget_config(self, checkout):
        """Get configuration for SumUp widget."""
        return {
            'checkout_id': checkout.sumup_checkout_id,
            'amount': float(checkout.amount),
            'currency': checkout.currency,
            'description': checkout.description,
            'merchant_code': checkout.merchant_code,
            'sdk_url': 'https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js',
            'success_url': checkout.return_url,
            'site_url': settings.SITE_URL
        }

    def _generate_tickets_for_order(self, order):
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
                        debug_logger.info(f"Generated PDF ticket for {ticket.ticket_number}")
                    else:
                        debug_logger.warning(f"Failed to generate PDF for ticket {ticket.ticket_number}")

                    tickets_created.append(ticket)
                    logger.info(f"Generated ticket {ticket.ticket_number} for order {order.order_number}")

                except Exception as e:
                    logger.error(f"Failed to generate ticket for order {order.order_number}: {e}")
                    debug_logger.error(f"Ticket creation error: {type(e).__name__}: {e}")
                    # Continue creating other tickets even if one fails

        logger.info(f"Generated {len(tickets_created)} tickets for order {order.order_number}")
        return tickets_created

    def _send_order_confirmation_emails(self, order, tickets):
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