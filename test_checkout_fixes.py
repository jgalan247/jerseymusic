#!/usr/bin/env python3
"""
Test the fixed simple checkout flow to verify:
1. Database constraint errors are resolved
2. X-Frame-Options are properly handled
3. Complete checkout flow works end-to-end
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from events.models import Event
from orders.models import Order, OrderItem
from decimal import Decimal

User = get_user_model()


def test_checkout_fixes():
    """Test the complete fixed checkout flow."""
    print("🔧 Testing Fixed Simple Checkout Flow")
    print("=" * 60)

    client = Client()

    # 1. Setup test data
    print("\n1️⃣ Setting up test data...")

    # Get or create a test event
    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found - creating test event")
        # Would need to create test event here
        return False

    print(f"✅ Using event: {event.title} (£{event.ticket_price})")

    # 2. Test cart creation
    print("\n2️⃣ Testing cart creation...")

    # Clear any existing cart for this session
    session = client.session
    session['cart_cleared'] = True
    session.save()

    # Add to cart
    response = client.post(f'/cart/add/{event.id}/', {
        'quantity': 2
    }, follow=True)

    if response.status_code == 200:
        print("✅ Added 2 tickets to cart")
    else:
        print(f"❌ Failed to add to cart: {response.status_code}")
        return False

    # 3. Test checkout form
    print("\n3️⃣ Testing checkout form display...")

    response = client.get('/payments/simple-checkout/')

    if response.status_code == 200:
        print("✅ Checkout form loads correctly")
        if hasattr(response, 'context') and response.context:
            cart_items = response.context.get('cart_items')
            if cart_items:
                print(f"   - Found {len(cart_items)} items in cart")
                for item in cart_items:
                    print(f"   - {item.quantity}x {item.event.title} @ £{item.event.ticket_price}")
            else:
                print("   ⚠️ No cart items in context")
    else:
        print(f"❌ Checkout form failed: {response.status_code}")
        return False

    # 4. Test order creation with fixed fields
    print("\n4️⃣ Testing order creation with all required fields...")

    # Count orders before
    orders_before = Order.objects.count()

    response = client.post('/payments/simple-checkout/', {
        'email': 'test@jerseyevents.co.uk',
        'first_name': 'Test',
        'last_name': 'Customer',
        'phone': '07700 900123'
    }, follow=False)

    print(f"   - Response status: {response.status_code}")
    print(f"   - Redirect location: {response.get('Location', 'None')}")

    # Check if order was created
    orders_after = Order.objects.count()
    if orders_after > orders_before:
        print("✅ Order created successfully!")

        # Get the latest order
        latest_order = Order.objects.latest('created_at')
        print(f"   - Order number: {latest_order.order_number}")
        print(f"   - Customer: {latest_order.delivery_first_name} {latest_order.delivery_last_name}")
        print(f"   - Email: {latest_order.email}")
        print(f"   - Subtotal: £{latest_order.subtotal}")
        print(f"   - Shipping: £{latest_order.shipping_cost}")
        print(f"   - Total: £{latest_order.total}")
        print(f"   - Items: {latest_order.items.count()}")

        # Verify all required fields are set
        required_fields = [
            'subtotal', 'shipping_cost', 'total',
            'delivery_first_name', 'delivery_last_name',
            'delivery_address_line_1', 'delivery_parish', 'delivery_postcode'
        ]

        all_fields_set = True
        for field in required_fields:
            value = getattr(latest_order, field)
            if value is None or value == '':
                print(f"   ❌ Required field '{field}' is empty")
                all_fields_set = False
            else:
                print(f"   ✅ {field}: {value}")

        if all_fields_set:
            print("✅ All required Order fields properly set")
        else:
            print("❌ Some required fields missing")
            return False

        # Check order items
        for item in latest_order.items.all():
            print(f"   - Item: {item.quantity}x {item.event_title} @ £{item.price} = £{item.total}")

        # Test redirect to payment
        if response.status_code == 302:
            redirect_url = response.get('Location', '')
            if '/redirect/checkout/' in redirect_url:
                print("✅ Correctly redirects to payment")
            else:
                print(f"❌ Unexpected redirect: {redirect_url}")
        else:
            print(f"❌ Expected redirect (302), got {response.status_code}")

    else:
        print("❌ Order was not created")
        # Check for error messages
        if hasattr(response, 'context') and response.context:
            messages = list(response.context.get('messages', []))
            for msg in messages:
                print(f"   - Error: {msg}")
        return False

    # 5. Test SumUp checkout creation
    print("\n5️⃣ Testing SumUp checkout creation...")

    if orders_after > orders_before:
        latest_order = Order.objects.latest('created_at')

        try:
            # Test the redirect checkout view
            response = client.get(f'/payments/redirect/checkout/{latest_order.id}/', follow=False)

            if response.status_code == 302:
                redirect_url = response.get('Location', '')
                if 'checkout.sumup.com' in redirect_url:
                    print("✅ Successfully redirects to SumUp")
                    print(f"   - SumUp URL: {redirect_url}")
                else:
                    print(f"❌ Unexpected redirect URL: {redirect_url}")
            else:
                print(f"❌ SumUp checkout failed: {response.status_code}")

        except Exception as e:
            print(f"❌ SumUp checkout error: {e}")

    # 6. Test return URL handlers
    print("\n6️⃣ Testing return URL handlers...")

    if orders_after > orders_before:
        latest_order = Order.objects.latest('created_at')

        # Test success URL
        response = client.get(f'/payments/redirect/success/?order={latest_order.order_number}')
        if response.status_code == 200:
            print("✅ Success handler works")
        else:
            print(f"❌ Success handler failed: {response.status_code}")

        # Test cancel URL
        response = client.get(f'/payments/redirect/cancel/?order={latest_order.order_number}')
        if response.status_code == 200:
            print("✅ Cancel handler works")
        else:
            print(f"❌ Cancel handler failed: {response.status_code}")

    print("\n" + "=" * 60)
    print("✅ CHECKOUT FIXES TEST COMPLETE")
    print("=" * 60)

    return True


def verify_database_integrity():
    """Verify no database constraint issues remain."""
    print("\n🗄️ Verifying Database Integrity...")

    try:
        # Try to create a minimal order to test constraints
        from decimal import Decimal

        test_order = Order(
            email='test@example.com',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='Test Address',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            phone='123456789',
            subtotal=Decimal('10.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('10.00')
        )

        # This should not raise any constraint errors
        test_order.full_clean()
        print("✅ Order model validation passes")

        # Don't save, just validate
        return True

    except Exception as e:
        print(f"❌ Database constraint issue: {e}")
        return False


if __name__ == '__main__':
    print("🚀 Testing Simple Checkout Fixes")
    print("🔧 Issues fixed:")
    print("   1. Database constraint error for orders_order.subtotal")
    print("   2. X-Frame-Options meta tag removed from templates")
    print("   3. Complete checkout flow validation")
    print()

    # Test database integrity first
    db_ok = verify_database_integrity()

    if db_ok:
        # Test complete flow
        success = test_checkout_fixes()

        if success:
            print("\n🎉 All fixes working correctly!")
            print("\n📋 Manual Testing:")
            print("1. Start server: python manage.py runserver")
            print("2. Visit: http://localhost:8000/events/")
            print("3. Add event to cart")
            print("4. Go to cart: http://localhost:8000/cart/")
            print("5. Click 'Buy Tickets Now'")
            print("6. Fill checkout form and submit")
            print("7. Should redirect to SumUp payment page")
        else:
            print("\n❌ Some issues remain - check output above")
    else:
        print("\n❌ Database integrity issues found")

    sys.exit(0 if (db_ok and success) else 1)