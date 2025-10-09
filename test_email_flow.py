#!/usr/bin/env python3
"""
Test script to verify the complete email flow for ticket confirmations.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/Users/josegalan/Documents/jersey_music')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.backends.db import SessionStore
from accounts.models import User
from events.models import Event
from orders.models import Order, OrderItem
from payments.ticket_email_service import ticket_email_service
from payments.redirect_success_fixed import redirect_success_fixed
from django.utils import timezone
from decimal import Decimal
import logging

# Setup logging to see email output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('payment_debug')

def create_test_order():
    """Create a test order with event and items."""
    print("📦 Creating test order...")

    # Create test user (customer)
    try:
        user = User.objects.get(email='test.customer@example.com')
        print(f"   Using existing user: {user.email}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            email='test.customer@example.com',
            first_name='John',
            last_name='Doe'
        )
        print(f"   Created new user: {user.email}")

    # Create test organiser
    try:
        organiser = User.objects.get(email='organiser@example.com')
        print(f"   Using existing organiser: {organiser.email}")
    except User.DoesNotExist:
        organiser = User.objects.create_user(
            email='organiser@example.com',
            first_name='Event',
            last_name='Organiser'
        )
        print(f"   Created new organiser: {organiser.email}")

    # Create test event
    try:
        event = Event.objects.get(title='Test Music Event')
        print(f"   Using existing event: {event.title}")
    except Event.DoesNotExist:
        event = Event.objects.create(
            title='Test Music Event',
            description='A fantastic music event for testing',
            organiser=organiser,
            event_date=timezone.now().date(),
            event_time=timezone.now().time(),
            venue_name='Jersey Test Venue',
            venue_address='123 Test Street, St. Helier, Jersey',
            ticket_price=Decimal('25.00'),
            capacity=100,
            status='published'
        )
        print(f"   Created new event: {event.title}")

    # Create test order
    order = Order.objects.create(
        user=user,
        email='test.customer@example.com',
        phone='+44 7700 900123',
        delivery_first_name='John',
        delivery_last_name='Doe',
        delivery_address_line_1='456 Test Lane',
        delivery_parish='st_helier',
        delivery_postcode='JE1 1AA',
        subtotal=Decimal('50.00'),
        shipping_cost=Decimal('0.00'),
        total=Decimal('50.00'),
        status='pending',
        is_paid=False
    )

    # Create order items
    order_item = OrderItem.objects.create(
        order=order,
        event=event,
        event_title=event.title,
        event_organiser=organiser.get_full_name(),
        event_date=event.event_date,
        venue_name=event.venue_name,
        quantity=2,
        price=Decimal('25.00'),
        total=Decimal('50.00')
    )

    print(f"   ✅ Created order {order.order_number} with {order_item.quantity} tickets")
    return order

def test_email_service_directly():
    """Test the email service directly."""
    print("\n📧 Testing email service directly...")

    order = create_test_order()

    try:
        success = ticket_email_service.send_ticket_confirmation(order)

        if success:
            print("   ✅ Email service returned success")
        else:
            print("   ❌ Email service returned failure")

    except Exception as e:
        print(f"   ❌ Error in email service: {e}")
        import traceback
        traceback.print_exc()

def test_success_view_flow():
    """Test the complete success view flow including email."""
    print("\n🔄 Testing complete success view flow...")

    order = create_test_order()

    # Create request factory
    factory = RequestFactory()

    # Create GET request with order parameter (simulating SumUp redirect)
    request = factory.get(f'/payments/success/?order={order.order_number}')

    # Add session
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()

    try:
        response = redirect_success_fixed(request)
        print(f"   ✅ Success view returned status: {response.status_code}")

        # Check if order was processed
        order.refresh_from_db()
        if order.is_paid:
            print(f"   ✅ Order {order.order_number} marked as paid")
        else:
            print(f"   ❌ Order {order.order_number} still not paid")

    except Exception as e:
        print(f"   ❌ Error in success view: {e}")
        import traceback
        traceback.print_exc()

def test_qr_code_generation():
    """Test QR code generation specifically."""
    print("\n🔲 Testing QR code generation...")

    order = create_test_order()

    try:
        qr_images = ticket_email_service._generate_qr_codes_for_order(order)

        print(f"   ✅ Generated {len(qr_images)} QR codes")

        for i, qr_data in enumerate(qr_images, 1):
            print(f"      QR {i}: ticket_id={qr_data['ticket_id']}, cid={qr_data['cid']}")
            print(f"              image_size={len(qr_data['image'])} bytes")

    except Exception as e:
        print(f"   ❌ Error generating QR codes: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests."""
    print("🧪 TESTING EMAIL FLOW FOR JERSEY EVENTS")
    print("=" * 50)

    # Test QR code generation
    test_qr_code_generation()

    # Test email service directly
    test_email_service_directly()

    # Test complete success view flow
    test_success_view_flow()

    print("\n" + "=" * 50)
    print("✅ Email flow testing complete!")
    print("\nTo check console email output, look for:")
    print("- Email messages in Django console (if EMAIL_BACKEND=console)")
    print("- MailHog interface at http://localhost:8025/ (if using MailHog)")
    print("- Log messages with '📧' emoji indicating email operations")

if __name__ == '__main__':
    main()