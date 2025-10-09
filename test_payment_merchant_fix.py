#!/usr/bin/env python3
"""
Test script to verify SumUp payment processing with proper merchant code.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from events.models import Event, Venue
from accounts.models import User, ArtistProfile
from payments.models import SumUpCheckout
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def test_merchant_code_settings():
    """Test that merchant code is properly configured."""
    print("=" * 60)
    print("Testing Merchant Code Configuration")
    print("=" * 60)

    merchant_code = getattr(settings, 'SUMUP_MERCHANT_CODE', None)
    merchant_id = getattr(settings, 'SUMUP_MERCHANT_ID', None)

    print(f"SUMUP_MERCHANT_CODE: {merchant_code}")
    print(f"SUMUP_MERCHANT_ID: {merchant_id}")

    if merchant_code:
        print("✅ Merchant code is configured")
        return True
    else:
        print("❌ Merchant code is not configured")
        return False

def create_test_data():
    """Create test data for payment flow."""
    print("\n" + "=" * 60)
    print("Creating Test Data")
    print("=" * 60)

    # Create test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_email_verified': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    print(f"✅ Test user: {user.email}")

    # Create test artist
    artist_user, created = User.objects.get_or_create(
        email='artist@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Artist',
            'is_email_verified': True
        }
    )
    if created:
        artist_user.set_password('testpass123')
        artist_user.save()
    print(f"✅ Test artist: {artist_user.email}")

    # Create artist profile
    artist_profile, created = ArtistProfile.objects.get_or_create(
        user=artist_user,
        defaults={
            'display_name': 'Test Artist',
            'bio': 'Test artist for payment testing',
            'sumup_merchant_code': settings.SUMUP_MERCHANT_CODE or 'M28WNZCB'
        }
    )
    print(f"✅ Artist profile: {artist_profile.display_name}")

    # Create venue
    venue, created = Venue.objects.get_or_create(
        name='Test Venue',
        defaults={
            'address': '123 Test Street',
            'parish': 'st_helier',
            'postcode': 'JE1 1AA'
        }
    )
    print(f"✅ Test venue: {venue.name}")

    # Create event
    event, created = Event.objects.get_or_create(
        title='Test Event',
        organiser=artist_user,
        venue=venue,
        defaults={
            'description': 'Test event for payment testing',
            'event_date': timezone.now().date() + timedelta(days=30),
            'start_time': timezone.now().time(),
            'price': Decimal('25.00'),
            'max_attendees': 100,
            'status': 'published'
        }
    )
    print(f"✅ Test event: {event.title}")

    return user, artist_user, artist_profile, venue, event

def test_checkout_creation(user, event):
    """Test SumUp checkout creation with merchant code."""
    print("\n" + "=" * 60)
    print("Testing Checkout Creation")
    print("=" * 60)

    try:
        # Create test order
        order = Order.objects.create(
            user=user,
            email=user.email,
            phone='01534123456',
            delivery_first_name=user.first_name,
            delivery_last_name=user.last_name,
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('25.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('25.00'),
            status='pending'
        )
        print(f"✅ Order created: {order.order_number}")

        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            event=event,
            event_title=event.title,
            event_organiser=event.organiser.get_full_name(),
            event_date=event.event_date,
            venue_name=event.venue.name,
            quantity=1,
            price=event.price
        )
        print(f"✅ Order item created: {order_item}")

        # Test SumUp checkout creation
        checkout = SumUpCheckout.objects.create(
            order=order,
            customer=user,
            amount=order.total,
            currency='GBP',
            description=f'Order {order.order_number}',
            merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
            return_url='https://86a7ab44d9e2.ngrok-free.app/payments/success/',
            status='created'
        )
        print(f"✅ SumUp checkout created: {checkout.checkout_reference}")
        print(f"   Merchant Code: {checkout.merchant_code}")
        print(f"   Amount: £{checkout.amount}")
        print(f"   Status: {checkout.status}")

        return True, checkout

    except Exception as e:
        print(f"❌ Checkout creation failed: {e}")
        return False, None

def test_payment_endpoints():
    """Test that payment endpoints are accessible."""
    print("\n" + "=" * 60)
    print("Testing Payment Endpoints")
    print("=" * 60)

    from django.urls import reverse
    from django.test import Client

    client = Client()

    # Test endpoints
    endpoints = [
        ('payments:success', 'Success page'),
        ('payments:cancel', 'Cancel page'),
        ('payments:fail', 'Fail page'),
    ]

    for url_name, description in endpoints:
        try:
            url = reverse(url_name)
            response = client.get(url)
            if response.status_code < 500:
                print(f"✅ {description:20} - {url:30} [{response.status_code}]")
            else:
                print(f"❌ {description:20} - {url:30} [Error: {response.status_code}]")
        except Exception as e:
            print(f"❌ {description:20} - {url:30} [Exception: {e}]")

def main():
    """Run all tests."""
    print("Testing SumUp Payment Processing with Merchant Code")
    print("Using ngrok URL: https://86a7ab44d9e2.ngrok-free.app")

    # Test 1: Configuration
    config_ok = test_merchant_code_settings()

    # Test 2: Create test data
    try:
        user, artist_user, artist_profile, venue, event = create_test_data()
        data_ok = True
    except Exception as e:
        print(f"❌ Test data creation failed: {e}")
        data_ok = False

    # Test 3: Checkout creation
    checkout_ok = False
    if data_ok:
        checkout_ok, checkout = test_checkout_creation(user, event)

    # Test 4: Endpoint accessibility
    test_payment_endpoints()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    tests = [
        ("Merchant Code Configuration", config_ok),
        ("Test Data Creation", data_ok),
        ("Checkout Creation", checkout_ok),
    ]

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:30} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! SumUp payment processing should work.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)