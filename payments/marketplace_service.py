"""
Marketplace payment routing service for Jersey Events.
Routes customer payments to event organizers via SumUp.
"""

import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

from .models import SumUpCheckout
from orders.models import Order
from events.models import Event
from accounts.models import ArtistProfile
from . import sumup as sumup_api

logger = logging.getLogger(__name__)


class MarketplacePaymentService:
    """Service to handle marketplace payment routing."""

    def __init__(self):
        self.platform_fee_percentage = getattr(settings, 'PLATFORM_FEE_PERCENTAGE', 5.0)

    def calculate_payment_split(self, order):
        """Calculate how payment should be split between organizer and platform."""
        total_amount = order.total
        platform_fee = (total_amount * Decimal(str(self.platform_fee_percentage))) / 100
        organizer_amount = total_amount - platform_fee

        return {
            'total_amount': total_amount,
            'platform_fee': platform_fee,
            'organizer_amount': organizer_amount,
            'platform_fee_percentage': self.platform_fee_percentage
        }

    def get_payment_routing(self, order):
        """Determine payment routing strategy for an order."""
        # Get the event from the first order item
        first_item = order.items.first()
        if not first_item or not first_item.event:
            return {
                'type': 'platform_only',
                'reason': 'No event found in order'
            }

        event = first_item.event
        organizer = event.organiser

        # Check if organizer has SumUp connected
        try:
            artist_profile = organizer.artistprofile
            if artist_profile.is_sumup_connected:
                return {
                    'type': 'direct_to_organizer',
                    'organizer': organizer,
                    'artist_profile': artist_profile,
                    'merchant_code': artist_profile.sumup_merchant_code,
                    'payment_split': self.calculate_payment_split(order)
                }
        except ArtistProfile.DoesNotExist:
            pass

        # Fallback to platform collection
        return {
            'type': 'platform_collection',
            'organizer': organizer,
            'reason': 'Organizer not connected to SumUp',
            'payment_split': self.calculate_payment_split(order)
        }

    def create_organizer_checkout(self, order, routing_info):
        """Create a checkout that pays directly to the organizer."""
        if routing_info['type'] != 'direct_to_organizer':
            raise ValueError("Invalid routing type for organizer checkout")

        artist_profile = routing_info['artist_profile']
        payment_split = routing_info['payment_split']

        # Get the event for description
        first_item = order.items.first()
        event = first_item.event if first_item else None

        # Create description
        description = f"Jersey Events - {event.title if event else 'Event Ticket'}"

        try:
            # Create checkout using organizer's SumUp account
            checkout_data = sumup_api.create_checkout_for_artist(
                artist_profile,
                amount=float(payment_split['organizer_amount']),
                currency='GBP',
                reference=f"order_{order.order_number}",
                description=description,
                return_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}"
            )

            # Create SumUpCheckout record
            checkout = SumUpCheckout.objects.create(
                order=order,
                customer=order.user,
                artist=artist_profile.user,
                amount=payment_split['organizer_amount'],
                currency='GBP',
                description=description,
                merchant_code=artist_profile.sumup_merchant_code,
                checkout_reference=f"order_{order.order_number}",
                sumup_checkout_id=checkout_data.get('id', ''),
                return_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(f"Created organizer checkout for order {order.order_number}, amount: £{payment_split['organizer_amount']}")
            return checkout, checkout_data

        except Exception as e:
            logger.error(f"Failed to create organizer checkout for order {order.order_number}: {e}")
            raise

    def create_platform_checkout(self, order, routing_info):
        """Create a checkout that pays to the platform (for later payout)."""
        payment_split = routing_info['payment_split']

        # Get the event for description
        first_item = order.items.first()
        event = first_item.event if first_item else None

        # Create description
        description = f"Jersey Events - {event.title if event else 'Event Ticket'}"

        try:
            # Create checkout using platform's SumUp account
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=f"order_{order.order_number}",
                description=description,
                return_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}",
                redirect_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}"
            )

            # Create SumUpCheckout record
            checkout = SumUpCheckout.objects.create(
                order=order,
                customer=order.user,
                amount=order.total,
                currency='GBP',
                description=description,
                merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
                checkout_reference=f"order_{order.order_number}",
                sumup_checkout_id=checkout_data.get('id', ''),
                return_url=f"{settings.SITE_URL}/payments/success/?order={order.order_number}",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(f"Created platform checkout for order {order.order_number}, amount: £{order.total}")
            return checkout, checkout_data

        except Exception as e:
            logger.error(f"Failed to create platform checkout for order {order.order_number}: {e}")
            raise

    def process_order_payment(self, order):
        """Process payment for an order using the appropriate routing."""
        # Determine payment routing
        routing_info = self.get_payment_routing(order)

        logger.info(f"Processing payment for order {order.order_number}, routing: {routing_info['type']}")

        # Create appropriate checkout
        if routing_info['type'] == 'direct_to_organizer':
            return self.create_organizer_checkout(order, routing_info)
        else:
            return self.create_platform_checkout(order, routing_info)

    def handle_successful_payment(self, checkout_id, payment_data):
        """Handle successful payment notification."""
        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
            order = checkout.order

            if not order:
                logger.warning(f"No order found for checkout {checkout_id}")
                return

            # Update checkout status
            checkout.status = 'paid'
            checkout.paid_at = timezone.now()
            checkout.sumup_response.update(payment_data)
            checkout.save()

            # Update order status
            order.status = 'confirmed'
            order.is_paid = True
            order.paid_at = timezone.now()
            order.save()

            # Get routing info to determine next steps
            routing_info = self.get_payment_routing(order)

            if routing_info['type'] == 'direct_to_organizer':
                # Payment went directly to organizer
                logger.info(f"Order {order.order_number} paid directly to organizer")
                # TODO: Record platform fee owed by organizer
                # TODO: Send notification to organizer
            else:
                # Payment collected by platform
                logger.info(f"Order {order.order_number} collected by platform for later payout")
                # TODO: Calculate and record organizer payout
                # TODO: Send notification to organizer about pending payout

            # TODO: Generate and send tickets
            # TODO: Send confirmation emails

            return True

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Checkout not found for ID {checkout_id}")
            return False
        except Exception as e:
            logger.error(f"Error handling successful payment for checkout {checkout_id}: {e}")
            return False

    def get_organizer_earnings(self, organizer, start_date=None, end_date=None):
        """Get earnings summary for an organizer."""
        # Get all paid orders for this organizer's events
        orders = Order.objects.filter(
            items__event__organiser=organizer,
            status='confirmed',
            is_paid=True
        )

        if start_date:
            orders = orders.filter(paid_at__gte=start_date)
        if end_date:
            orders = orders.filter(paid_at__lte=end_date)

        total_sales = sum(order.total for order in orders)
        total_fees = (total_sales * Decimal(str(self.platform_fee_percentage))) / 100
        net_earnings = total_sales - total_fees

        return {
            'total_sales': total_sales,
            'platform_fees': total_fees,
            'net_earnings': net_earnings,
            'order_count': orders.count(),
            'fee_percentage': self.platform_fee_percentage
        }