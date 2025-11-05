"""
Payment Polling Service
=======================
Verifies pending payments by calling SumUp API every 5 minutes.

SECURITY CRITICAL: This service verifies payment amounts server-side
before issuing tickets. NEVER issue tickets based on return_url alone.

Author: Jersey Events Platform
"""

import logging
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from datetime import timedelta
from decimal import Decimal

from orders.models import Order
from payments import sumup as sumup_api
from payments.models import SumUpCheckout
from events.email_utils import email_service

logger = logging.getLogger('payments.polling_service')


class PaymentPollingService:
    """
    Polls SumUp API to verify pending payments and issue tickets.
    Runs every 5 minutes via Django-Q scheduled task.

    Security Features:
    - Verifies payment amounts match order totals
    - Uses database locks to prevent race conditions
    - Implements idempotency checks
    - Logs all verification attempts with full audit trail
    - Alerts admin for suspicious patterns or failures
    """

    MAX_ORDERS_PER_CYCLE = 20
    MAX_AGE_HOURS = 2
    ADMIN_EMAIL = 'alerts@coderra.je'

    def process_pending_payments(self):
        """
        Main entry point - called by scheduled task every 5 minutes.

        Now uses SumUpCheckout.needs_polling property for efficient polling.
        Supports both ticket orders and listing fees.
        """
        logger.info("=" * 80)
        logger.info("Starting payment polling cycle")

        # Find all checkouts that need polling using the new polling fields
        pending_checkouts = SumUpCheckout.objects.filter(
            status__in=['created', 'pending'],
            should_poll=True,
            created_at__gte=timezone.now() - timedelta(hours=self.MAX_AGE_HOURS)
        ).select_related('order', 'customer').order_by('created_at')[:self.MAX_ORDERS_PER_CYCLE]

        if not pending_checkouts.exists():
            logger.info("No pending checkouts to process")
            return {'message': 'No pending checkouts'}

        logger.info(f"Found {pending_checkouts.count()} pending checkouts to verify")

        stats = {
            'verified': 0,
            'failed': 0,
            'still_pending': 0,
            'errors': 0,
            'listing_fees': 0,  # Track listing fee payments separately
        }

        for checkout in pending_checkouts:
            try:
                # Check if this checkout actually needs polling
                if not checkout.needs_polling:
                    logger.info(f"Checkout {checkout.payment_id} no longer needs polling (may have expired or reached max duration)")
                    checkout.stop_polling("Max duration reached or expired")
                    continue

                # Start polling timestamp if not already set
                checkout.start_polling()

                # Verify the checkout
                result = self._verify_single_checkout(checkout)

                # Update polling timestamp
                checkout.update_poll_timestamp()

                # Track stats
                if result in stats:
                    stats[result] += 1
                else:
                    logger.error(f"Unknown result type: {result}")
                    stats['errors'] += 1

                logger.info(f"Checkout {checkout.payment_id}: {result} (poll #{checkout.poll_count})")

            except Exception as e:
                logger.error(
                    f"Unexpected error processing checkout {checkout.payment_id}: {e}",
                    exc_info=True
                )
                stats['errors'] += 1

        logger.info(f"Polling cycle complete: {stats}")
        return stats

    def _verify_single_checkout(self, checkout):
        """
        Verify a single checkout via SumUp API.
        Handles both ticket orders and listing fee payments.

        Args:
            checkout: SumUpCheckout instance to verify

        Returns:
            str: 'verified', 'failed', 'still_pending', 'errors', or 'listing_fees'
        """
        try:
            checkout_id = checkout.sumup_checkout_id or checkout.checkout_id

            if not checkout_id:
                logger.error(f"Checkout {checkout.payment_id} missing sumup_checkout_id")
                checkout.stop_polling("Missing checkout ID")
                return 'errors'

            # Determine if this is a listing fee or ticket order
            is_listing_fee = checkout.order is None and 'listing_fee' in checkout.checkout_reference.lower()

            # Call SumUp API to get current status
            logger.info(f"Calling SumUp API for checkout {checkout_id}")

            try:
                # Always use platform token for consistency
                payment_data = sumup_api.get_checkout_status(checkout_id)
            except Exception as api_error:
                logger.error(f"SumUp API call failed for {checkout_id}: {api_error}", exc_info=True)
                # Don't mark as failed - might be temporary issue
                return 'errors'

            status = payment_data.get('status')
            amount = Decimal(str(payment_data.get('amount', 0)))

            logger.info(
                f"Checkout {checkout.payment_id}: "
                f"SumUp status={status}, amount={amount}, expected={checkout.amount}"
            )

            # Update checkout response data
            checkout.sumup_response = payment_data
            checkout.save(update_fields=['sumup_response'])

            # Process based on status
            if status == 'PAID':
                # SECURITY CHECK: Verify amount
                if amount != checkout.amount:
                    logger.error(
                        f"CRITICAL: Amount mismatch for checkout {checkout.payment_id}! "
                        f"Expected: {checkout.amount}, Received: {amount}"
                    )
                    self._handle_checkout_amount_mismatch(checkout, amount)
                    return 'errors'

                # Payment verified - process based on type
                if is_listing_fee:
                    self._process_listing_fee_payment(checkout, payment_data)
                    return 'listing_fees'
                elif checkout.order:
                    self._process_successful_order_payment(checkout, payment_data)
                    return 'verified'
                else:
                    logger.warning(f"Checkout {checkout.payment_id} has no order or listing fee association")
                    checkout.status = 'paid'
                    checkout.paid_at = timezone.now()
                    checkout.stop_polling("Payment completed")
                    checkout.save()
                    return 'verified'

            elif status == 'FAILED':
                self._process_failed_checkout(checkout)
                return 'failed'

            elif status in ['PENDING', 'pending', 'created', 'CREATED']:
                # Check if too old
                age = timezone.now() - checkout.created_at
                if age > timedelta(hours=self.MAX_AGE_HOURS):
                    logger.warning(f"Checkout {checkout.payment_id} expired (age: {age})")
                    self._mark_checkout_as_expired(checkout)
                    return 'failed'

                return 'still_pending'

            else:
                logger.warning(f"Unknown status '{status}' for checkout {checkout.payment_id}")
                return 'errors'

        except Exception as e:
            logger.error(
                f"Error in _verify_single_checkout for {checkout.payment_id}: {e}",
                exc_info=True
            )
            return 'errors'

    def _verify_single_order(self, order):
        """
        Verify a single order via SumUp API.

        Args:
            order: Order instance to verify

        Returns:
            str: 'verified', 'failed', 'still_pending', or 'error'
        """
        try:
            # Get checkout record
            try:
                checkout = SumUpCheckout.objects.get(order=order)
            except SumUpCheckout.DoesNotExist:
                logger.error(f"No checkout found for order {order.order_number}")
                order.payment_notes = "No checkout record found - requires manual investigation"
                order.status = 'requires_manual_review'
                order.save()
                self._send_critical_alert(
                    subject=f"Missing Checkout - Order {order.order_number}",
                    message=f"Order {order.order_number} has no SumUpCheckout record. "
                            f"This should never happen. Requires immediate investigation."
                )
                return 'errors'

            checkout_id = checkout.sumup_checkout_id

            if not checkout_id:
                logger.error(f"Checkout {checkout.payment_id} missing sumup_checkout_id")
                order.payment_notes = "Checkout missing SumUp ID"
                order.status = 'requires_manual_review'
                order.save()
                return 'errors'

            # Get organizer's profile for OAuth tokens
            try:
                # Get first order item to find the event organizer
                order_item = order.items.first()
                if not order_item or not order_item.event:
                    logger.error(f"Order {order.order_number} has no event")
                    return 'errors'

                organizer_profile = order_item.event.organiser.artistprofile
            except AttributeError as e:
                logger.error(
                    f"No organizer profile found for order {order.order_number}: {e}"
                )
                order.payment_notes = "Organizer missing SumUp connection"
                order.status = 'requires_manual_review'
                order.save()
                return 'errors'

            # Call SumUp API
            logger.info(f"Calling SumUp API for checkout {checkout_id}")

            try:
                # Check if artist has OAuth connection
                if organizer_profile and organizer_profile.is_sumup_connected:
                    # Use artist's OAuth tokens
                    logger.info(f"Using artist OAuth tokens for checkout {checkout_id}")
                    payment_data = sumup_api.get_checkout_for_artist(
                        artist_profile=organizer_profile,
                        checkout_id=checkout_id
                    )
                else:
                    # Use platform token as fallback
                    logger.info(f"Artist not connected to SumUp - using platform token for checkout {checkout_id}")
                    payment_data = sumup_api.get_checkout_status(checkout_id)
            except Exception as api_error:
                logger.error(f"SumUp API call failed: {api_error}", exc_info=True)
                # Don't mark as failed - might be temporary issue
                # Will retry next cycle
                return 'errors'

            status = payment_data.get('status')
            amount = Decimal(str(payment_data.get('amount', 0)))

            logger.info(
                f"Order {order.order_number}: "
                f"SumUp status={status}, amount={amount}, expected={order.total}"
            )

            # Process based on status
            if status == 'PAID':
                # SECURITY CHECK: Verify amount
                if amount != order.total:
                    logger.error(
                        f"CRITICAL: Amount mismatch for order {order.order_number}! "
                        f"Expected: {order.total}, Received: {amount}"
                    )
                    self._handle_amount_mismatch(order, amount)
                    return 'errors'

                # Payment verified - issue tickets
                self._process_successful_payment(order, checkout, payment_data)
                return 'verified'

            elif status == 'FAILED':
                self._process_failed_payment(order, checkout)
                return 'failed'

            elif status == 'PENDING':
                # Check if too old
                age = timezone.now() - order.created_at
                if age > timedelta(hours=self.MAX_AGE_HOURS):
                    logger.warning(f"Order {order.order_number} expired (age: {age})")
                    self._mark_as_expired(order)
                    return 'failed'

                return 'still_pending'

            else:
                logger.warning(f"Unknown status '{status}' for order {order.order_number}")
                return 'errors'

        except Exception as e:
            logger.error(
                f"Error in _verify_single_order for {order.order_number}: {e}",
                exc_info=True
            )
            return 'errors'

    def _process_successful_payment(self, order, checkout, payment_data):
        """
        Payment verified successfully - issue tickets and send email.
        Uses database transaction for atomicity.

        Args:
            order: Order instance
            checkout: SumUpCheckout instance
            payment_data: Dict from SumUp API
        """
        with transaction.atomic():
            # Lock order to prevent race conditions
            order = Order.objects.select_for_update().get(id=order.id)

            # Double-check not already processed (idempotency)
            if order.status == 'completed':
                logger.warning(f"Order {order.order_number} already completed - skipping")
                return

            # Update order
            order.status = 'completed'
            order.is_paid = True
            order.paid_at = timezone.now()
            order.transaction_id = payment_data.get('transaction_code', checkout.sumup_checkout_id)
            order.payment_notes = f"Payment verified via polling at {timezone.now()}"
            order.save()

            # Update checkout
            checkout.status = 'paid'
            checkout.paid_at = timezone.now()
            checkout.sumup_response = payment_data
            checkout.save()

            # Generate tickets
            tickets = self._generate_tickets(order)

            logger.info(
                f"✓ Order {order.order_number} verified successfully. "
                f"{len(tickets)} tickets issued."
            )

        # Send confirmation email (after transaction commits)
        try:
            email_service.send_order_confirmation(order, tickets)
            logger.info(f"Confirmation email sent to {order.email}")
        except Exception as email_error:
            logger.error(
                f"Failed to send confirmation email for order {order.order_number}: {email_error}",
                exc_info=True
            )
            # Alert admin but don't fail the order
            self._alert_email_failure(order, str(email_error))

    def _generate_tickets(self, order):
        """
        Generate ticket records for order items.

        Args:
            order: Order instance

        Returns:
            list: List of created Ticket instances
        """
        from events.models import Ticket

        tickets = []

        for order_item in order.items.all():
            for i in range(order_item.quantity):
                ticket = Ticket.objects.create(
                    event=order_item.event,
                    order=order,
                    customer=order.user if order.user else None,
                    status='valid'
                )

                # Generate PDF if method exists
                if hasattr(ticket, 'generate_pdf_ticket'):
                    try:
                        ticket.generate_pdf_ticket()
                        logger.info(f"PDF generated for ticket {ticket.ticket_number}")
                    except Exception as pdf_error:
                        logger.error(
                            f"PDF generation failed for ticket {ticket.id}: {pdf_error}",
                            exc_info=True
                        )

                tickets.append(ticket)

        logger.info(f"Generated {len(tickets)} tickets for order {order.order_number}")
        return tickets

    def _process_failed_payment(self, order, checkout):
        """
        Payment failed - update records and notify customer.

        Args:
            order: Order instance
            checkout: SumUpCheckout instance
        """
        with transaction.atomic():
            order.status = 'failed'
            order.payment_notes = f'Payment failed at SumUp - {timezone.now()}'
            order.save()

            checkout.status = 'failed'
            checkout.save()

        logger.info(f"Order {order.order_number} marked as failed")

        # Send failure notification
        try:
            self._send_payment_failed_email(order)
        except Exception as e:
            logger.error(f"Failed to send failure email: {e}", exc_info=True)

    def _mark_as_expired(self, order):
        """
        Mark order as expired (pending too long without confirmation).

        Args:
            order: Order instance
        """
        order.status = 'expired'
        order.payment_notes = (
            f"Payment verification timed out after {self.MAX_AGE_HOURS} hours - {timezone.now()}"
        )
        order.save()

        logger.warning(f"Order {order.order_number} marked as expired")

        # Alert admin - needs manual investigation
        self._alert_admin_expired_order(order)

    def _handle_amount_mismatch(self, order, actual_amount):
        """
        CRITICAL: Payment amount doesn't match order total.

        Args:
            order: Order instance
            actual_amount: Decimal amount received from SumUp
        """
        order.status = 'requires_manual_review'
        order.payment_notes = (
            f"AMOUNT MISMATCH - Expected: £{order.total}, "
            f"Received: £{actual_amount} - {timezone.now()}"
        )
        order.save()

        logger.error(f"AMOUNT MISMATCH for order {order.order_number}")

        # Immediate critical alert
        self._send_critical_alert(
            subject=f"CRITICAL: Amount Mismatch - Order {order.order_number}",
            message=f"""
CRITICAL PAYMENT ISSUE

Order: {order.order_number}
Expected Amount: £{order.total}
Received Amount: £{actual_amount}
Customer: {order.email}
Customer Name: {order.delivery_first_name} {order.delivery_last_name}

This order requires IMMEDIATE manual review.

Do NOT issue tickets until verified.

View order: {self._get_admin_order_url(order)}
            """.strip()
        )

    def _check_for_stuck_orders(self):
        """
        Find orders stuck in pending >30 minutes and alert admin.
        """
        threshold = timezone.now() - timedelta(minutes=30)

        stuck_orders = Order.objects.filter(
            status='pending_verification',
            created_at__lt=threshold,
            created_at__gte=timezone.now() - timedelta(hours=self.MAX_AGE_HOURS)
        )

        count = stuck_orders.count()

        if count > 0:
            logger.warning(f"Found {count} orders stuck >30 minutes")

            # Prepare order details (limit to 10 in email)
            order_list = "\n".join([
                f"- Order {o.order_number}: £{o.total}, created {o.created_at}, email {o.email}"
                for o in stuck_orders[:10]
            ])

            self._send_admin_alert(
                subject=f"Warning: {count} Orders Stuck in Processing",
                message=f"""
{count} orders have been in 'pending_verification' for >30 minutes:

{order_list}

{'(Showing first 10 only)' if count > 10 else ''}

These may be legitimate slow payments, but check for patterns.

Admin panel: {self._get_base_url()}/admin/orders/order/
                """.strip()
            )

    def _alert_admin_expired_order(self, order):
        """
        Alert about order that expired without verification.

        Args:
            order: Order instance
        """
        self._send_admin_alert(
            subject=f"Order Expired: {order.order_number}",
            message=f"""
Order {order.order_number} expired after {self.MAX_AGE_HOURS} hours
without payment verification.

Customer: {order.email}
Name: {order.delivery_first_name} {order.delivery_last_name}
Amount: £{order.total}
Created: {order.created_at}

Action required:
1. Check customer's bank statement
2. Check organizer's SumUp account
3. Contact customer if payment was actually received

View order: {self._get_admin_order_url(order)}
            """.strip()
        )

    def _alert_email_failure(self, order, error_message):
        """
        Alert about email delivery failure.

        Args:
            order: Order instance
            error_message: str error message
        """
        self._send_admin_alert(
            subject=f"Email Delivery Failed: Order {order.order_number}",
            message=f"""
Failed to send confirmation email for order {order.order_number}

Order completed successfully and tickets were issued,
but customer did not receive email.

Customer: {order.email}
Name: {order.delivery_first_name} {order.delivery_last_name}
Error: {error_message}

Action required: Manually send tickets to customer

View order: {self._get_admin_order_url(order)}
            """.strip()
        )

    def _send_payment_failed_email(self, order):
        """
        Send email notification about failed payment.

        Args:
            order: Order instance
        """
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        context = {
            'order': order,
            'customer_name': f"{order.delivery_first_name} {order.delivery_last_name}",
            'site_name': 'Jersey Events',
            'support_email': 'support@coderra.je',
            'retry_url': f"{self._get_base_url()}/cart/"
        }

        html_message = render_to_string('emails/payment_failed.html', context)
        text_message = strip_tags(html_message)

        email_service.send_email_with_retry(
            subject=f'Payment Failed - Order #{order.order_number}',
            message=text_message,
            html_message=html_message,
            recipient_list=[order.email]
        )

        logger.info(f"Payment failed email sent to {order.email}")

    def _send_admin_alert(self, subject, message):
        """
        Send non-critical alert to admin.

        Args:
            subject: str email subject
            message: str email body
        """
        try:
            send_mail(
                subject=f"[JerseyEvents Alert] {subject}",
                message=message,
                from_email='noreply@coderra.je',
                recipient_list=[self.ADMIN_EMAIL],
                fail_silently=False
            )
            logger.info(f"Admin alert sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send admin alert: {e}", exc_info=True)

    def _send_critical_alert(self, subject, message):
        """
        Send CRITICAL alert to admin.

        Args:
            subject: str email subject
            message: str email body
        """
        try:
            send_mail(
                subject=f"[JerseyEvents CRITICAL] {subject}",
                message=message,
                from_email='noreply@coderra.je',
                recipient_list=[self.ADMIN_EMAIL],
                fail_silently=False
            )

            # Also log as critical
            logger.critical(f"CRITICAL ALERT SENT: {subject}")
        except Exception as e:
            logger.error(f"Failed to send CRITICAL alert: {e}", exc_info=True)

    def _get_base_url(self):
        """Get base URL for the site."""
        from django.conf import settings
        return getattr(settings, 'SITE_URL', 'http://localhost:8000')

    def _get_admin_order_url(self, order):
        """Get admin URL for order."""
        return f"{self._get_base_url()}/admin/orders/order/{order.id}/change/"

    def _process_successful_order_payment(self, checkout, payment_data):
        """
        Process successful payment for ticket orders.

        Args:
            checkout: SumUpCheckout instance
            payment_data: Dict from SumUp API
        """
        order = checkout.order

        with transaction.atomic():
            # Lock order to prevent race conditions
            order = Order.objects.select_for_update().get(id=order.id)

            # Double-check not already processed (idempotency)
            if order.status == 'completed':
                logger.warning(f"Order {order.order_number} already completed - skipping")
                checkout.stop_polling("Order already completed")
                return

            # Update order
            order.status = 'completed'
            order.is_paid = True
            order.paid_at = timezone.now()
            order.transaction_id = payment_data.get('transaction_code', checkout.sumup_checkout_id)
            order.payment_notes = f"Payment verified via polling at {timezone.now()}"
            order.save()

            # Update checkout
            checkout.status = 'paid'
            checkout.paid_at = timezone.now()
            checkout.sumup_response = payment_data
            checkout.stop_polling("Payment completed")
            checkout.save()

            # Generate tickets
            tickets = self._generate_tickets(order)

            logger.info(
                f"✓ Order {order.order_number} verified successfully. "
                f"{len(tickets)} tickets issued."
            )

        # Send confirmation email (after transaction commits)
        try:
            email_service.send_order_confirmation(order, tickets)
            logger.info(f"Confirmation email sent to {order.email}")
        except Exception as email_error:
            logger.error(
                f"Failed to send confirmation email for order {order.order_number}: {email_error}",
                exc_info=True
            )
            self._alert_email_failure(order, str(email_error))

    def _process_listing_fee_payment(self, checkout, payment_data):
        """
        Process successful payment for listing fees.

        Args:
            checkout: SumUpCheckout instance
            payment_data: Dict from SumUp API
        """
        from events.models import ListingFee

        try:
            # Find the listing fee by checkout reference
            listing_fee = ListingFee.objects.get(
                payment_reference__in=[
                    checkout.checkout_reference.replace('listing_fee_', ''),
                    checkout.checkout_reference
                ]
            )

            with transaction.atomic():
                # Update listing fee
                listing_fee.payment_status = 'paid'
                listing_fee.paid_at = timezone.now()
                listing_fee.payment_data = payment_data
                listing_fee.save()

                # Update checkout
                checkout.status = 'paid'
                checkout.paid_at = timezone.now()
                checkout.sumup_response = payment_data
                checkout.stop_polling("Listing fee payment completed")
                checkout.save()

                # Publish the event if it was draft
                event = listing_fee.event
                if event.status == 'draft':
                    event.status = 'published'
                    event.save()
                    logger.info(f"Event {event.id} published after listing fee payment")

            logger.info(f"✓ Listing fee paid for event {event.id}")

            # Send confirmation email to organizer
            try:
                from django.template.loader import render_to_string
                from django.core.mail import send_mail

                context = {
                    'event': event,
                    'listing_fee': listing_fee,
                    'organizer_name': event.organiser.get_full_name(),
                }

                html_message = render_to_string('emails/listing_fee_paid.html', context)

                send_mail(
                    subject=f"Listing Fee Paid - {event.title}",
                    message=f"Your listing fee for {event.title} has been paid. Your event is now published!",
                    html_message=html_message,
                    from_email='noreply@coderra.je',
                    recipient_list=[event.organiser.email],
                    fail_silently=True
                )

                logger.info(f"Listing fee confirmation email sent to {event.organiser.email}")
            except Exception as email_error:
                logger.error(f"Failed to send listing fee confirmation: {email_error}", exc_info=True)

        except ListingFee.DoesNotExist:
            logger.error(f"No listing fee found for checkout {checkout.payment_id}")
            checkout.stop_polling("Listing fee not found")
        except Exception as e:
            logger.error(f"Error processing listing fee payment: {e}", exc_info=True)

    def _process_failed_checkout(self, checkout):
        """
        Process failed checkout payment.

        Args:
            checkout: SumUpCheckout instance
        """
        with transaction.atomic():
            checkout.status = 'failed'
            checkout.stop_polling("Payment failed")
            checkout.save()

            # If associated with an order, update order status
            if checkout.order:
                order = checkout.order
                order.status = 'failed'
                order.payment_notes = f'Payment failed at SumUp - {timezone.now()}'
                order.save()

                logger.info(f"Order {order.order_number} marked as failed")

                # Send failure notification
                try:
                    self._send_payment_failed_email(order)
                except Exception as e:
                    logger.error(f"Failed to send failure email: {e}", exc_info=True)
            else:
                logger.info(f"Checkout {checkout.payment_id} marked as failed (no order associated)")

    def _mark_checkout_as_expired(self, checkout):
        """
        Mark checkout as expired (pending too long without confirmation).

        Args:
            checkout: SumUpCheckout instance
        """
        checkout.status = 'expired'
        checkout.stop_polling("Expired after max duration")
        checkout.save()

        # If associated with an order, mark order as expired
        if checkout.order:
            order = checkout.order
            order.status = 'expired'
            order.payment_notes = (
                f"Payment verification timed out after {self.MAX_AGE_HOURS} hours - {timezone.now()}"
            )
            order.save()

            logger.warning(f"Order {order.order_number} marked as expired")
            self._alert_admin_expired_order(order)
        else:
            logger.warning(f"Checkout {checkout.payment_id} marked as expired")

    def _handle_checkout_amount_mismatch(self, checkout, actual_amount):
        """
        CRITICAL: Payment amount doesn't match checkout total.

        Args:
            checkout: SumUpCheckout instance
            actual_amount: Decimal amount received from SumUp
        """
        checkout.status = 'requires_manual_review'
        checkout.stop_polling("Amount mismatch - manual review required")
        checkout.save()

        if checkout.order:
            order = checkout.order
            order.status = 'requires_manual_review'
            order.payment_notes = (
                f"AMOUNT MISMATCH - Expected: £{checkout.amount}, "
                f"Received: £{actual_amount} - {timezone.now()}"
            )
            order.save()

            # Send critical alert
            self._send_critical_alert(
                subject=f"CRITICAL: Amount Mismatch - Order {order.order_number}",
                message=f"""
CRITICAL PAYMENT ISSUE

Order: {order.order_number}
Checkout: {checkout.payment_id}
Expected Amount: £{checkout.amount}
Received Amount: £{actual_amount}
Customer: {order.email}

This order requires IMMEDIATE manual review.
Do NOT issue tickets until verified.

View order: {self._get_admin_order_url(order)}
                """.strip()
            )
        else:
            # Listing fee or other payment type
            logger.error(f"AMOUNT MISMATCH for checkout {checkout.payment_id}")
            self._send_critical_alert(
                subject=f"CRITICAL: Amount Mismatch - Checkout {checkout.payment_id}",
                message=f"""
CRITICAL PAYMENT ISSUE

Checkout: {checkout.payment_id}
Reference: {checkout.checkout_reference}
Expected Amount: £{checkout.amount}
Received Amount: £{actual_amount}

This requires IMMEDIATE manual review.
                """.strip()
            )


# Singleton instance
polling_service = PaymentPollingService()
