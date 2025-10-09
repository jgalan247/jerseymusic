"""
Simplified checkout process that creates an order and redirects to SumUp.
No complex authentication requirements or widget issues.
"""

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.db import transaction

from cart.models import Cart
from orders.models import Order, OrderItem
from .redirect_checkout import create_order_checkout

logger = logging.getLogger(__name__)


def simple_checkout_process(request):
    """
    Simple checkout that:
    1. Gets cart items
    2. Creates order
    3. Redirects to SumUp payment
    Works for both authenticated and anonymous users.
    """
    logger.info("Starting simple checkout process")

    # Get cart
    cart = get_cart(request)

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:view')

    # Check cart items availability
    cart_items = cart.items.select_related('event')
    for item in cart_items:
        if item.event.status != 'published':
            messages.error(request, f"{item.event.title} is no longer available.")
            item.delete()
            return redirect('cart:view')

        if item.quantity > item.event.tickets_available:
            messages.warning(request, f"Only {item.event.tickets_available} tickets available for {item.event.title}")
            item.quantity = item.event.tickets_available
            item.save()

    # Collect customer information
    if request.method == 'GET':
        # Show simple form for email and contact details
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }

        return render(request, 'payments/simple_checkout_form.html', {
            'cart': cart,
            'cart_items': cart_items,
            'initial_data': initial_data
        })

    elif request.method == 'POST':
        # Process checkout
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone', '')

        # Validation
        if not email or not first_name or not last_name:
            messages.error(request, "Please fill in all required fields.")
            return redirect('payments:simple_checkout')

        try:
            with transaction.atomic():
                # Calculate totals first
                subtotal = Decimal('0.00')
                shipping_cost = Decimal('0.00')  # Digital tickets - no shipping

                for item in cart_items:
                    subtotal += item.event.ticket_price * item.quantity

                total = subtotal + shipping_cost

                # Create order with all required fields
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    email=email,
                    delivery_first_name=first_name,
                    delivery_last_name=last_name,
                    delivery_address_line_1='Digital Delivery',  # For digital tickets
                    delivery_parish='st_helier',  # Default
                    delivery_postcode='JE1 1AA',  # Default
                    phone=phone,
                    status='pending',
                    is_paid=False,
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    total=total,
                    payment_method='sumup',
                    delivery_method='collection'  # Digital tickets
                )

                # Create order items
                for item in cart_items:
                    item_total = item.event.ticket_price * item.quantity
                    OrderItem.objects.create(
                        order=order,
                        event=item.event,
                        event_title=item.event.title,
                        event_organiser=item.event.organiser.get_full_name() if item.event.organiser else '',
                        event_date=item.event.event_date,
                        venue_name=item.event.venue_name,
                        quantity=item.quantity,
                        price=item.event.ticket_price,
                        total=item_total
                    )

                # Store order ID in session for anonymous users
                if not request.user.is_authenticated:
                    request.session['order_id'] = order.id

                # Clear cart
                cart.items.all().delete()

                logger.info(f"Created order {order.order_number} for {email}")

                # Redirect to payment
                return redirect('payments:redirect_checkout', order_id=order.id)

        except Exception as e:
            logger.error(f"Checkout error: {e}")
            messages.error(request, "An error occurred during checkout. Please try again.")
            return redirect('cart:view')

    return redirect('cart:view')


def get_cart(request):
    """Get or create cart for current user/session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
    else:
        # For anonymous users, use session
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, _ = Cart.objects.get_or_create(
            session_key=session_key,
            is_active=True
        )

    return cart