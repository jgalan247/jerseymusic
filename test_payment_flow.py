#!/usr/bin/env python
"""Test complete payment flow with fixed SumUp API integration."""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from events.models import Event, Ticket
from orders.models import Order, OrderItem
from payments.models import SumUpCheckout
from accounts.models import ArtistProfile
# from cart.cart import Cart  # Not needed for this test
import json

User = get_user_model()

def create_test_data():
    """Create test users and events."""
    print("\n" + "="*60)
    print("CREATING TEST DATA")
    print("="*60)

    # Create organizer user
    organizer, created = User.objects.get_or_create(
        email="testorganizer@example.com",
        defaults={
            'first_name': 'Test',
            'last_name': 'Organizer',
            'user_type': 'artist',
            'email_verified': True
        }
    )
    if created:
        organizer.set_password('testpass123')
        organizer.save()
        print(f"✅ Created organizer: {organizer.email}")
    else:
        print(f"ℹ️  Using existing organizer: {organizer.email}")

    # Get or create artist profile
    artist_profile, created = ArtistProfile.objects.get_or_create(
        user=organizer,
        defaults={
            'display_name': 'Test Artist',
            'bio': 'Test bio',
            'sumup_merchant_code': settings.SUMUP_MERCHANT_CODE  # Use platform merchant code for testing
        }
    )
    if created:
        print(f"✅ Created artist profile")
    else:
        print(f"ℹ️  Using existing artist profile")

    # Create customer user
    customer, created = User.objects.get_or_create(
        email="testcustomer@example.com",
        defaults={
            'first_name': 'Test',
            'last_name': 'Customer',
            'user_type': 'customer',
            'email_verified': True
        }
    )
    if created:
        customer.set_password('testpass123')
        customer.save()
        print(f"✅ Created customer: {customer.email}")
    else:
        print(f"ℹ️  Using existing customer: {customer.email}")

    # Create test event
    event, created = Event.objects.get_or_create(
        title="Test Concert",
        organiser=organizer,
        defaults={
            'slug': 'test-concert',
            'description': 'Test event for payment flow',
            'venue_name': 'Test Venue',
            'venue_address': '123 Test Street, St. Helier, JE2 3AB',
            'event_date': '2025-12-25',
            'event_time': '20:00',
            'status': 'published',
            'ticket_price': Decimal('25.00'),
            'capacity': 100,
            'tickets_sold': 0
        }
    )
    if created:
        print(f"✅ Created event: {event.title}")
    else:
        print(f"ℹ️  Using existing event: {event.title}")

    return organizer, customer, event, artist_profile

def test_anonymous_checkout():
    """Test checkout as anonymous user."""
    print("\n" + "="*60)
    print("TESTING ANONYMOUS CHECKOUT")
    print("="*60)

    client = Client()

    # Get event
    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found")
        return None

    print(f"\n📋 Event: {event.title}")
    print(f"   Price: £{event.ticket_price}")

    # Add to cart
    add_url = reverse('cart:add', args=[event.id])
    response = client.post(add_url, {'quantity': 2}, follow=True)
    print(f"✅ Added to cart: {response.status_code}")

    # View cart
    cart_url = reverse('cart:view')
    response = client.get(cart_url)
    print(f"✅ Cart view: {response.status_code}")

    # Proceed to checkout
    checkout_url = reverse('payments:checkout')
    response = client.post(checkout_url, {
        'first_name': 'Anonymous',
        'last_name': 'Buyer',
        'email': 'anonymous@example.com',
        'phone': '+44 7700 900123'
    }, follow=True)

    print(f"✅ Checkout initiated: {response.status_code}")

    # Check if order was created
    order = Order.objects.filter(email='anonymous@example.com').order_by('-created_at').first()
    if order:
        print(f"\n✅ Order created:")
        print(f"   Order number: {order.order_number}")
        print(f"   Total: £{order.total}")
        print(f"   Status: {order.status}")

        # Check if checkout was created
        checkout = SumUpCheckout.objects.filter(order=order).first()
        if checkout:
            print(f"\n✅ SumUp checkout created:")
            print(f"   Checkout ID: {checkout.sumup_checkout_id}")
            print(f"   Status: {checkout.status}")
        else:
            print(f"\n⚠️  No SumUp checkout found for order")

        return order
    else:
        print(f"❌ No order created")
        return None

def test_customer_checkout():
    """Test checkout as logged-in customer."""
    print("\n" + "="*60)
    print("TESTING CUSTOMER CHECKOUT")
    print("="*60)

    client = Client()

    # Login as customer
    customer = User.objects.filter(email="testcustomer@example.com").first()
    if not customer:
        print("❌ Test customer not found")
        return None

    client.force_login(customer)
    print(f"✅ Logged in as: {customer.email}")

    # Get event
    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found")
        return None

    print(f"\n📋 Event: {event.title}")
    print(f"   Price: £{event.ticket_price}")

    # Add to cart
    add_url = reverse('cart:add', args=[event.id])
    response = client.post(add_url, {'quantity': 1}, follow=True)
    print(f"✅ Added to cart: {response.status_code}")

    # Proceed to checkout
    checkout_url = reverse('payments:checkout')
    response = client.get(checkout_url)
    print(f"✅ Checkout page: {response.status_code}")

    # Submit checkout form
    response = client.post(checkout_url, {
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'email': customer.email,
        'phone': '+44 7700 900456'
    }, follow=True)

    print(f"✅ Checkout submitted: {response.status_code}")

    # Check if order was created
    order = Order.objects.filter(user=customer).order_by('-created_at').first()
    if order:
        print(f"\n✅ Order created:")
        print(f"   Order number: {order.order_number}")
        print(f"   Total: £{order.total}")
        print(f"   Status: {order.status}")

        # Check if checkout was created
        checkout = SumUpCheckout.objects.filter(order=order).first()
        if checkout:
            print(f"\n✅ SumUp checkout created:")
            print(f"   Checkout ID: {checkout.sumup_checkout_id}")
            print(f"   Status: {checkout.status}")
            print(f"   Merchant code: {checkout.merchant_code}")
        else:
            print(f"\n⚠️  No SumUp checkout found for order")

        return order
    else:
        print(f"❌ No order created")
        return None

def test_widget_payment():
    """Test payment using widget service."""
    print("\n" + "="*60)
    print("TESTING WIDGET PAYMENT SERVICE")
    print("="*60)

    from payments.widget_service import SumUpWidgetService

    # Create a test order
    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found")
        return

    order = Order.objects.create(
        order_number=f"TEST-{Order.objects.count() + 1:06d}",
        email="widget@test.com",
        phone="+44 7700 900789",
        delivery_first_name="Widget",
        delivery_last_name="Test",
        delivery_address_line_1="123 Test Street",
        delivery_parish="st_helier",
        delivery_postcode="JE2 3AB",
        subtotal=Decimal('50.00'),
        shipping_cost=Decimal('0.00'),
        total=Decimal('50.00'),
        status='pending'
    )

    OrderItem.objects.create(
        order=order,
        event=event,
        price=event.ticket_price,
        quantity=2
    )

    print(f"✅ Test order created: {order.order_number}")

    # Test widget service
    widget_service = SumUpWidgetService()

    try:
        checkout, checkout_data = widget_service.create_checkout_for_widget(order=order)

        print(f"\n✅ Widget checkout created:")
        print(f"   Checkout ID: {checkout.sumup_checkout_id}")
        print(f"   Amount: £{checkout.amount}")
        print(f"   Status: {checkout.status}")

        # Get widget config
        config = widget_service.get_widget_config(checkout)
        print(f"\n✅ Widget configuration:")
        print(f"   Checkout ID: {config.get('checkout_id')}")
        print(f"   Amount: {config.get('amount')}")
        print(f"   Currency: {config.get('currency')}")

    except Exception as e:
        print(f"❌ Widget checkout failed: {e}")
        import traceback
        traceback.print_exc()

def cleanup_test_data():
    """Clean up test data."""
    print("\n" + "="*60)
    print("CLEANING UP TEST DATA")
    print("="*60)

    # Delete test orders
    test_orders = Order.objects.filter(
        email__in=['anonymous@example.com', 'testcustomer@example.com', 'widget@test.com']
    )
    count = test_orders.count()
    test_orders.delete()
    print(f"   Deleted {count} test orders")

    # Delete test checkouts
    test_checkouts = SumUpCheckout.objects.filter(
        order__isnull=True
    ).delete()
    print(f"   Cleaned up orphaned checkouts")

def main():
    print("="*60)
    print("PAYMENT FLOW INTEGRATION TEST")
    print("="*60)

    # Create test data
    organizer, customer, event, artist_profile = create_test_data()

    # Test anonymous checkout
    test_anonymous_checkout()

    # Test customer checkout
    test_customer_checkout()

    # Test widget payment
    test_widget_payment()

    # Cleanup
    cleanup_test_data()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()