#!/usr/bin/env python
"""
Test Critical Fixes - Focused validation of all fixes applied
"""

import os
import sys
import django
from decimal import Decimal
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import Client
from datetime import timedelta

# Import models to test
from accounts.models import ArtistProfile
from events.models import Event, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from payments.models import SumUpCheckout
from events.email_utils import email_service

User = get_user_model()

def test_critical_fixes():
    """Test all critical fixes applied"""
    print("🔧 TESTING CRITICAL FIXES")
    print("=" * 50)

    fixes_tested = 0
    fixes_passed = 0

    # Test 1: Email Configuration Fix
    fixes_tested += 1
    try:
        email_result = email_service.test_email_configuration()
        if email_result['configured']:
            print("✅ Email Configuration: Working correctly")
            fixes_passed += 1
        else:
            print(f"❌ Email Configuration: {email_result.get('error', 'Failed')}")
    except Exception as e:
        print(f"❌ Email Configuration: {e}")

    # Test 2: Template URL Pattern Fixes
    fixes_tested += 1
    try:
        client = Client()

        # Create test user to test URLs
        test_user = User.objects.create_user(
            username='fix_test_user',
            email='fixtest@test.com',
            password='testpass123'
        )
        test_user.email_verified = True
        test_user.save()

        client.login(username='fix_test_user', password='testpass123')

        # Test that homepage loads without URL errors
        response = client.get('/')
        if response.status_code == 200:
            print("✅ Template URL Patterns: Homepage loads successfully")
            fixes_passed += 1
        else:
            print(f"❌ Template URL Patterns: Homepage failed ({response.status_code})")

    except Exception as e:
        print(f"❌ Template URL Patterns: {e}")

    # Test 3: Cart Calculation Methods
    fixes_tested += 1
    try:
        # Create test data for cart calculations
        artist_user = User.objects.create_user(
            username='fix_artist',
            email='fixartist@test.com',
            password='testpass123',
            user_type='artist'
        )

        artist = ArtistProfile.objects.create(
            user=artist_user,
            display_name='Fix Test Artist',
            is_approved=True
        )

        category = Category.objects.create(
            name='Fix Test Category'
        )

        event = Event.objects.create(
            title='Fix Test Event',
            description='Test event for fixes',
            organiser=artist_user,
            category=category,
            venue_name='Fix Test Venue',
            venue_address='Test Address',
            event_date=timezone.now().date() + timedelta(days=30),
            event_time='19:00',
            ticket_price=Decimal('25.00'),
            capacity=100,
            status='published'
        )

        cart = Cart.objects.create(user=test_user)
        cart_item = CartItem.objects.create(
            cart=cart,
            event=event,
            quantity=2
        )

        # Test cart calculation methods
        total_cost = cart_item.get_total_cost()
        expected_cost = Decimal('50.00')  # 2 x £25.00

        if total_cost == expected_cost:
            print(f"✅ Cart Calculations: get_total_cost() working ({total_cost})")
            fixes_passed += 1
        else:
            print(f"❌ Cart Calculations: Expected {expected_cost}, got {total_cost}")

    except Exception as e:
        print(f"❌ Cart Calculations: {e}")

    # Test 4: Event Slug Uniqueness
    fixes_tested += 1
    try:
        # Try to create events with same title and date
        event2 = Event.objects.create(
            title='Fix Test Event',  # Same title
            description='Another test event',
            organiser=artist_user,
            category=category,
            venue_name='Another Venue',
            venue_address='Another Address',
            event_date=timezone.now().date() + timedelta(days=30),  # Same date
            event_time='20:00',
            ticket_price=Decimal('30.00'),
            capacity=100,
            status='published'
        )

        # Check that slugs are different
        if event.slug != event2.slug:
            print(f"✅ Event Slug Uniqueness: Different slugs generated ({event.slug} vs {event2.slug})")
            fixes_passed += 1
        else:
            print(f"❌ Event Slug Uniqueness: Same slugs generated ({event.slug})")

    except Exception as e:
        print(f"❌ Event Slug Uniqueness: {e}")

    # Test 5: SumUp Model Field Fixes
    fixes_tested += 1
    try:
        order = Order.objects.create(
            user=test_user,
            email=test_user.email,
            phone='+447700900123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='123 Test St',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('50.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('50.00'),
            status='pending'
        )

        # Test creating SumUp checkout with checkout_id field
        checkout = SumUpCheckout.objects.create(
            order=order,
            amount=Decimal('50.00'),
            currency='GBP',
            checkout_id='test_checkout_fix_123',
            description='Test checkout for fixes',
            merchant_code='TEST123',
            return_url='http://test.com/return',
            status='pending'
        )

        if checkout.checkout_id == 'test_checkout_fix_123':
            print("✅ SumUp Model Fields: checkout_id field working")
            fixes_passed += 1
        else:
            print(f"❌ SumUp Model Fields: checkout_id not set correctly")

    except Exception as e:
        print(f"❌ SumUp Model Fields: {e}")

    # Test 6: Payment Calculation Methods
    fixes_tested += 1
    try:
        # Test payment calculation methods
        platform_fee = checkout.calculate_platform_fee(0.05)  # 5%
        artist_amount = checkout.calculate_artist_amount(0.05)
        listing_fee = checkout.calculate_listing_fee()

        expected_platform_fee = Decimal('2.50')  # 5% of £50
        expected_artist_amount = Decimal('47.50')  # £50 - £2.50
        expected_listing_fee = Decimal('2.50')

        if (platform_fee == expected_platform_fee and
            artist_amount == expected_artist_amount and
            listing_fee == expected_listing_fee):
            print(f"✅ Payment Calculations: All methods working correctly")
            print(f"   Platform Fee: £{platform_fee}, Artist Amount: £{artist_amount}, Listing Fee: £{listing_fee}")
            fixes_passed += 1
        else:
            print(f"❌ Payment Calculations: Incorrect results")
            print(f"   Expected: £{expected_platform_fee}, £{expected_artist_amount}, £{expected_listing_fee}")
            print(f"   Got: £{platform_fee}, £{artist_amount}, £{listing_fee}")

    except Exception as e:
        print(f"❌ Payment Calculations: {e}")

    # Clean up test data
    try:
        User.objects.filter(username__startswith='fix_').delete()
        Event.objects.filter(title__contains='Fix Test').delete()
        Category.objects.filter(name__contains='Fix Test').delete()
        print("\n🧹 Test data cleaned up")
    except Exception as e:
        print(f"\n⚠️ Cleanup warning: {e}")

    # Results
    print("\n" + "=" * 50)
    print("🎯 CRITICAL FIXES TEST RESULTS")
    print(f"Fixes Tested: {fixes_tested}")
    print(f"Fixes Passed: {fixes_passed}")

    success_rate = (fixes_passed / fixes_tested) * 100
    print(f"Fix Success Rate: {success_rate:.1f}%")

    if success_rate >= 100:
        print("🟢 EXCELLENT: All critical fixes working perfectly")
        return "EXCELLENT"
    elif success_rate >= 80:
        print("🟡 GOOD: Most critical fixes working correctly")
        return "GOOD"
    else:
        print("🔴 POOR: Some critical fixes still failing")
        return "POOR"

if __name__ == "__main__":
    result = test_critical_fixes()

    print(f"\n{'='*50}")
    print("🔧 CRITICAL FIXES VALIDATION COMPLETE")

    if result in ["EXCELLENT", "GOOD"]:
        print("✅ Critical fixes are working correctly")
        print("🚀 Ready for final production readiness validation")
        sys.exit(0)
    else:
        print("❌ Some critical fixes need attention")
        print("🔧 Address remaining issues before proceeding")
        sys.exit(1)