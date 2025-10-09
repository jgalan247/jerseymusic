"""Service for handling payments to SumUp-connected artists."""

import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from accounts.models import ArtistProfile
from payments import sumup as sumup_api
from payments.models import SumUpCheckout, SumUpTransaction
from orders.models import Order, OrderItem

logger = logging.getLogger(__name__)


class ConnectedPaymentService:
    """Handle payments for SumUp-connected artists."""

    def __init__(self):
        self.platform_fee_rate = Decimal(str(getattr(settings, 'PLATFORM_FEE_PERCENTAGE', 5.0)))

    def create_test_payment(self, order_data, artist):
        """Create a test payment for testing purposes."""
        try:
            quantity = order_data['quantity']
            unit_price = order_data['unit_price']
            total_amount = unit_price * quantity

            # Calculate platform fee
            platform_fee = (total_amount * self.platform_fee_rate) / 100
            artist_amount = total_amount - platform_fee

            return {
                'success': True,
                'amount': total_amount,
                'artist_amount': artist_amount,
                'platform_fee': platform_fee,
                'merchant_code': artist.sumup_merchant_code,
                'test_mode': True
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_connected_checkout(self, order):
        """
        Create a SumUp checkout for a SumUp-connected artist.

        For multi-artist orders, we'll need to handle them separately.
        For now, assume single-artist orders.
        """
        try:
            # Get the primary artist from the order
            artist_profile = self._get_order_artist(order)

            if not artist_profile.is_sumup_connected:
                raise ValueError(f"Artist {artist_profile.display_name} is not connected to SumUp")

            # Calculate platform fee
            platform_fee = (order.total * self.platform_fee_rate) / 100
            artist_amount = order.total - platform_fee

            # Create checkout using artist's SumUp connection
            checkout_data = sumup_api.create_checkout_for_connected_artist(
                artist_profile=artist_profile,
                amount=order.total,
                currency='GBP',
                reference=f"JE-{order.order_number}",
                description=f"Jersey Events - Order {order.order_number}",
                return_url=f"{settings.SITE_URL}/payments/callback/"
            )

            # Create our checkout record
            checkout = SumUpCheckout.objects.create(
                order=order,
                customer=order.user,
                artist=artist_profile.user,
                checkout_reference=checkout_data['checkout_reference'],
                sumup_checkout_id=checkout_data['id'],
                amount=order.total,
                currency='GBP',
                description=f"Order {order.order_number}",
                merchant_code=artist_profile.sumup_merchant_code or settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
                return_url=f"{settings.SITE_URL}/payments/callback/",
                status='created',
                sumup_response=checkout_data
            )

            logger.info(
                f"Created connected checkout {checkout.payment_id} for artist "
                f"{artist_profile.display_name} (order {order.order_number})"
            )

            return checkout

        except Exception as e:
            logger.error(f"Failed to create connected checkout for order {order.order_number}: {e}")
            raise

    def process_connected_callback(self, checkout_id, payment_status='paid'):
        """Process callback for connected artist payment."""
        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

            if payment_status == 'paid':
                # Get updated checkout data from SumUp
                artist_profile = checkout.artist.artistprofile
                updated_data = sumup_api.get_checkout_for_artist(artist_profile, checkout_id)

                # Update checkout status
                checkout.status = 'paid'
                checkout.paid_at = timezone.now()
                checkout.sumup_response = updated_data
                checkout.save()

                # Create transaction record
                if 'transactions' in updated_data and updated_data['transactions']:
                    transaction_data = updated_data['transactions'][0]

                    platform_fee = (checkout.amount * self.platform_fee_rate) / 100
                    artist_earnings = checkout.amount - platform_fee

                    sumup_transaction = SumUpTransaction.objects.create(
                        checkout=checkout,
                        sumup_transaction_id=transaction_data['id'],
                        transaction_code=transaction_data['transaction_code'],
                        amount=checkout.amount,
                        currency=checkout.currency,
                        status='successful',
                        payment_type='ecom',
                        platform_fee_percentage=self.platform_fee_rate,
                        platform_fee_amount=platform_fee,
                        artist_earnings=artist_earnings,
                        timestamp=timezone.now(),
                        sumup_response=transaction_data
                    )

                    # Update order status
                    order = checkout.order
                    order.status = 'confirmed'
                    order.is_paid = True
                    order.paid_at = timezone.now()
                    order.transaction_id = sumup_transaction.transaction_code
                    order.save()

                    logger.info(
                        f"Processed connected payment {sumup_transaction.transaction_code} "
                        f"for order {order.order_number}"
                    )

                    return {
                        'success': True,
                        'transaction': sumup_transaction,
                        'order': order
                    }
            else:
                # Payment failed
                checkout.status = 'failed'
                checkout.save()

                checkout.order.status = 'cancelled'
                checkout.order.save()

                logger.warning(f"Connected payment failed for checkout {checkout.payment_id}")

            return {'success': payment_status == 'paid'}

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Checkout not found for SumUp checkout ID: {checkout_id}")
            return {'success': False, 'error': 'Checkout not found'}
        except Exception as e:
            logger.error(f"Error processing connected callback for {checkout_id}: {e}")
            return {'success': False, 'error': str(e)}

    def create_artist_payout_batch(self, artist_profile, period_start, period_end):
        """Create a payout batch for a connected artist."""
        try:
            # Get all successful transactions for this artist in the period
            transactions = SumUpTransaction.objects.filter(
                checkout__artist=artist_profile.user,
                status='successful',
                timestamp__gte=period_start,
                timestamp__lte=period_end
            ).exclude(
                artist_payouts__isnull=False  # Exclude already paid out transactions
            )

            if not transactions.exists():
                return None

            total_sales = sum(t.amount for t in transactions)
            total_fees = sum(t.platform_fee_amount for t in transactions)
            payout_amount = sum(t.artist_earnings for t in transactions)

            from payments.models import ArtistPayout
            payout = ArtistPayout.objects.create(
                artist=artist_profile.user,
                amount=payout_amount,
                currency='GBP',
                status='pending',
                period_start=period_start.date(),
                period_end=period_end.date(),
                total_sales=total_sales,
                total_fees=total_fees,
                # Bank details would be collected from artist profile
                bank_account_name=artist_profile.business_name or artist_profile.display_name,
                bank_account_number='',  # To be filled
                bank_sort_code='',       # To be filled
            )

            # Link transactions to this payout
            payout.transactions.set(transactions)

            logger.info(
                f"Created payout batch {payout.payout_id} for {artist_profile.display_name}: "
                f"£{payout_amount} from {transactions.count()} transactions"
            )

            return payout

        except Exception as e:
            logger.error(f"Failed to create payout batch for {artist_profile.display_name}: {e}")
            raise

    def _get_order_artist(self, order):
        """Get the primary artist for an order. For now, assume single-artist orders."""
        first_item = order.items.first()
        if not first_item or not hasattr(first_item.event.organiser, 'artistprofile'):
            raise ValueError("No valid artist found for this order")

        return first_item.event.organiser.artistprofile

    def get_checkout_url(self, checkout):
        """Get the SumUp checkout URL for redirecting customers."""
        if checkout.sumup_response and 'checkout_url' in checkout.sumup_response:
            return checkout.sumup_response['checkout_url']

        # Fallback URL construction
        return f"https://pay.sumup.com/checkout/{checkout.sumup_checkout_id}"

    def can_process_connected_payment(self, order):
        """Check if order can be processed through connected artist workflow."""
        try:
            artist_profile = self._get_order_artist(order)
            return artist_profile.is_sumup_connected and not artist_profile.sumup_token_expired
        except Exception:
            return False