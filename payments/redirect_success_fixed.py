"""
Fixed redirect success handler with detailed logging
and proper order processing for SumUp payments.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from orders.models import Order, OrderItem
from cart.models import Cart
from .models import SumUpCheckout
from events.models import Ticket
from .ticket_email_service import ticket_email_service
import requests

logger = logging.getLogger('payment_debug')


# ⚠️ ⚠️ ⚠️  CRITICAL SECURITY WARNING ⚠️ ⚠️ ⚠️
# This webhook endpoint has NO SumUp signature verification!
# This is a MAJOR SECURITY RISK in production!
#
# TODO BEFORE PRODUCTION:
# 1. Implement SumUp webhook signature verification
# 2. Verify the payment amount matches the order amount
# 3. Verify the payment status with SumUp API
# 4. Add idempotency to prevent duplicate processing
#
# WITHOUT THESE CHECKS, ATTACKERS CAN:
# - Fake successful payments
# - Modify payment amounts
# - Replay webhook requests
# ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️

@csrf_exempt
def redirect_success_fixed(request):
    """
    Fixed success handler that properly processes SumUp payment redirects.
    Handles both order parameter and checkout_id from SumUp.

    ⚠️  SECURITY WARNING: This endpoint lacks webhook signature verification!
    """
    # Log security warning if in production
    if not settings.DEBUG:
        logger.warning(
            "⚠️  CRITICAL: Processing payment webhook WITHOUT signature verification! "
            "This is a security vulnerability in production!"
        )
    # Log all parameters received from SumUp
    logger.info("=" * 60)
    logger.info("🔍 PAYMENT SUCCESS REDIRECT RECEIVED")
    logger.info(f"GET parameters: {dict(request.GET)}")
    logger.info(f"Session data: cart_id={request.session.get('cart_id')}, order_id={request.session.get('order_id')}")

    # Get parameters from URL
    order_number = request.GET.get('order')
    checkout_id = request.GET.get('checkout_id')

    # SumUp might send different parameter names
    if not order_number:
        order_number = request.GET.get('reference')
    if not checkout_id:
        checkout_id = request.GET.get('id')

    logger.info(f"Extracted: order_number={order_number}, checkout_id={checkout_id}")

    # Try to find order by multiple methods
    order = None

    # Method 1: By order number
    if order_number:
        try:
            order = Order.objects.get(order_number=order_number)
            logger.info(f"✅ Found order by order_number: {order_number}")
        except Order.DoesNotExist:
            logger.warning(f"❌ Order not found by order_number: {order_number}")

    # Method 2: By checkout ID
    if not order and checkout_id:
        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
            order = checkout.order
            logger.info(f"✅ Found order by checkout_id: {checkout_id}")
        except SumUpCheckout.DoesNotExist:
            logger.warning(f"❌ Checkout not found: {checkout_id}")

    # Method 3: By session order_id
    if not order:
        session_order_id = request.session.get('order_id')
        if session_order_id:
            try:
                order = Order.objects.get(id=session_order_id)
                logger.info(f"✅ Found order by session order_id: {session_order_id}")
            except Order.DoesNotExist:
                logger.warning(f"❌ Order not found by session: {session_order_id}")

    # If no order found, show error
    if not order:
        logger.error("❌ NO ORDER FOUND - Cannot process payment")
        messages.error(request, "Order not found. Please contact support with your payment reference.")
        return redirect('events:events_list')

    logger.info(f"📦 Processing Order: {order.order_number}")
    logger.info(f"   - Current status: {order.status}")
    logger.info(f"   - Is paid: {order.is_paid}")
    logger.info(f"   - Total: £{order.total}")

    # Check if already processed
    if order.is_paid:
        logger.info(f"✅ Order {order.order_number} already marked as paid")

        # Get existing tickets
        tickets = Ticket.objects.filter(order=order)

        # Clear cart from session
        clear_cart_session(request)

        return render(request, 'payments/redirect_success.html', {
            'order': order,
            'already_paid': True,
            'tickets': tickets,
            'success': True
        })

    # ⚠️ CRITICAL: Verify payment with SumUp - DO NOT assume success on failure!
    payment_verified = False
    verification_failed = False

    if checkout_id:
        try:
            payment_verified, amount_verified = verify_sumup_payment(checkout_id, order.total)
            logger.info(f"SumUp verification result: verified={payment_verified}, amount_ok={amount_verified}")

            if not amount_verified:
                logger.error(
                    f"🚨 PAYMENT AMOUNT MISMATCH: Order {order.order_number}, "
                    f"Expected: £{order.total}, Got different amount from SumUp"
                )
                verification_failed = True

        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to verify payment with SumUp: {e}")
            verification_failed = True
    else:
        # No checkout_id - cannot verify payment
        logger.error(f"❌ CRITICAL: No checkout_id provided for order {order.order_number}")
        verification_failed = True

    # Handle verification failures by marking order as pending manual verification
    if verification_failed or not payment_verified:
        logger.error(f"🚨 PAYMENT VERIFICATION FAILED for order {order.order_number}")

        # Mark order as pending verification (not paid)
        order.status = 'pending_verification'
        order.payment_notes = f"Payment verification failed at {timezone.now()}. Requires manual verification."
        order.save()

        # Send admin notification for manual verification
        send_admin_verification_alert(order, checkout_id, verification_failed)

        # Show user a "processing" message instead of success
        messages.warning(
            request,
            "Your payment is being processed. You will receive confirmation within 24 hours. "
            "If you have any concerns, please contact support."
        )

        return render(request, 'payments/redirect_success.html', {
            'order': order,
            'pending_verification': True,
            'message': 'Payment processing - confirmation within 24 hours'
        })

    # Process the successful payment
    try:
        with transaction.atomic():
            logger.info(f"💳 Processing payment for order {order.order_number}")

            # Mark order as paid
            order.is_paid = True
            order.status = 'confirmed'
            order.paid_at = timezone.now()
            order.save()

            logger.info(f"✅ Order {order.order_number} marked as paid")

            # Update checkout record if exists
            if checkout_id:
                try:
                    checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
                    checkout.status = 'paid'
                    checkout.paid_at = timezone.now()
                    checkout.save()
                    logger.info(f"✅ Checkout {checkout_id} marked as paid")
                except SumUpCheckout.DoesNotExist:
                    logger.warning(f"Checkout record not found: {checkout_id}")

            # Generate tickets
            tickets = generate_tickets_for_order(order)
            logger.info(f"🎫 Generated {len(tickets)} tickets for order {order.order_number}")

            # Clear cart from session
            clear_cart_session(request)

            # Send confirmation emails (if implemented)
            try:
                send_confirmation_emails(order, tickets)
                logger.info(f"📧 Confirmation email sent to {order.email}")
            except Exception as e:
                logger.error(f"Failed to send confirmation email: {e}")
                # Don't fail the whole transaction for email errors

            logger.info(f"🎉 Order {order.order_number} processed successfully!")

            messages.success(request, f"Payment successful! Your order {order.order_number} has been confirmed.")

            return render(request, 'payments/redirect_success.html', {
                'order': order,
                'success': True,
                'tickets': tickets,
                'just_paid': True
            })

    except Exception as e:
        logger.error(f"❌ Error processing payment for order {order.order_number}: {e}")
        messages.error(request, "Error processing payment. Please contact support.")
        return render(request, 'payments/redirect_success.html', {
            'order': order,
            'error': True,
            'message': f'Processing error: {str(e)}'
        })


def verify_sumup_payment(checkout_id, expected_amount):
    """
    Verify payment status and amount with SumUp API.

    Returns:
        tuple: (payment_verified, amount_verified)
        - payment_verified: True if payment was successful
        - amount_verified: True if amount matches expected amount
    """
    try:
        # Get access token
        from payments.sumup import get_checkout_status
        from decimal import Decimal

        # Get checkout status from SumUp
        checkout_data = get_checkout_status(checkout_id)

        if not checkout_data:
            logger.error(f"No checkout data returned from SumUp for {checkout_id}")
            return False, False

        # Check payment status
        status = checkout_data.get('status', '').upper()
        payment_verified = status in ['PAID', 'SUCCESSFUL']

        logger.info(f"SumUp checkout {checkout_id} status: {status}")

        # Check amount matches expected amount
        sumup_amount = checkout_data.get('amount', 0)
        expected_decimal = Decimal(str(expected_amount))
        sumup_decimal = Decimal(str(sumup_amount))

        # Allow for minor floating point differences (within 1 penny)
        amount_difference = abs(expected_decimal - sumup_decimal)
        amount_verified = amount_difference < Decimal('0.01')

        if not amount_verified:
            logger.error(
                f"🚨 AMOUNT MISMATCH: Checkout {checkout_id}, "
                f"Expected: £{expected_decimal}, SumUp: £{sumup_decimal}, "
                f"Difference: £{amount_difference}"
            )

        logger.info(
            f"Payment verification: {checkout_id}, "
            f"Status: {status}, Payment OK: {payment_verified}, "
            f"Amount OK: {amount_verified} (Expected: £{expected_decimal}, Got: £{sumup_decimal})"
        )

        return payment_verified, amount_verified

    except Exception as e:
        logger.error(f"❌ CRITICAL: Failed to verify SumUp payment {checkout_id}: {e}")
        # SECURITY: On verification failure, return False (do not assume success)
        return False, False


def clear_cart_session(request):
    """Clear cart from session after successful payment."""
    try:
        # Clear cart from session
        if 'cart_id' in request.session:
            cart_id = request.session['cart_id']
            try:
                cart = Cart.objects.get(id=cart_id)
                cart.items.all().delete()
                logger.info(f"✅ Cleared cart {cart_id}")
            except Cart.DoesNotExist:
                pass
            del request.session['cart_id']

        # Clear order from session
        if 'order_id' in request.session:
            del request.session['order_id']

        logger.info("✅ Session cleared")

    except Exception as e:
        logger.error(f"Error clearing session: {e}")


def generate_tickets_for_order(order):
    """Generate tickets for all items in the order."""
    tickets = []

    for order_item in order.items.all():
        event = order_item.event
        quantity = order_item.quantity

        for i in range(quantity):
            # Only create ticket if we have a customer (user)
            # For anonymous orders, skip ticket generation or handle differently
            if order.user:
                ticket = Ticket.objects.create(
                    order=order,
                    event=event,
                    customer=order.user,
                    status='valid'
                )
                # Generate QR code (if implemented)
                try:
                    ticket.generate_qr_code()
                except:
                    pass
                tickets.append(ticket)
                logger.info(f"Created ticket {ticket.ticket_number} for {event.title}")
            else:
                # For anonymous orders, we can't create Ticket objects
                # Just log that tickets would be sent via email
                logger.info(f"Anonymous order - tickets for {event.title} will be sent via email")

    return tickets


def send_confirmation_emails(order, tickets):
    """Send order confirmation and tickets via email with QR codes."""
    try:
        # Use the ticket email service to send professional email with QR codes
        success = ticket_email_service.send_ticket_confirmation(order)

        if success:
            logger.info(f"📧 Confirmation email with tickets sent to {order.email}")
        else:
            logger.error(f"Failed to send confirmation email to {order.email}")
            # Don't raise exception - email failure shouldn't break the order

    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        # Don't raise - email failure shouldn't break the order process


def send_admin_verification_alert(order, checkout_id, verification_failed):
    """
    Send alert to admin for manual payment verification.

    Args:
        order: Order that needs verification
        checkout_id: SumUp checkout ID (may be None)
        verification_failed: Whether verification completely failed
    """
    try:
        from django.core.mail import mail_admins
        from django.conf import settings

        subject = f"🚨 URGENT: Payment Verification Required - Order {order.order_number}"

        message = f"""
URGENT: Manual payment verification required for order {order.order_number}

ORDER DETAILS:
- Order Number: {order.order_number}
- Customer: {order.delivery_first_name} {order.delivery_last_name}
- Email: {order.email}
- Amount: £{order.total}
- Status: {order.status}

PAYMENT DETAILS:
- SumUp Checkout ID: {checkout_id or 'NOT PROVIDED'}
- Verification Failed: {verification_failed}
- Timestamp: {timezone.now()}

REQUIRED ACTIONS:
1. Check SumUp dashboard for payment status
2. Verify the payment amount matches £{order.total}
3. Go to Django admin: /admin/orders/order/{order.id}/
4. Update order status to 'confirmed' if payment is valid
5. Contact customer if payment issues found

CUSTOMER SHOWN MESSAGE:
"Payment processing - confirmation within 24 hours"

This requires immediate attention to maintain customer trust.
"""

        # Send to all admins
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False
        )

        logger.error(f"🚨 Admin verification alert sent for order {order.order_number}")

    except Exception as e:
        logger.error(f"Failed to send admin verification alert: {e}")
        # Log to console as fallback
        print(f"🚨 URGENT: Manual verification needed for order {order.order_number}")
        print(f"   Checkout ID: {checkout_id}")
        print(f"   Amount: £{order.total}")
        print(f"   Admin action required!")