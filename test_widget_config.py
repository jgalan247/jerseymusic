#!/usr/bin/env python
"""Test SumUp widget configuration and parameters."""

import os
import sys
import django
import json
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from payments.widget_service import SumUpWidgetService
from payments.models import SumUpCheckout
from orders.models import Order, OrderItem
from events.models import Event
from accounts.models import User, ArtistProfile
import uuid

def test_widget_configuration():
    """Test widget configuration parameters."""
    print("\n" + "="*60)
    print("TESTING WIDGET CONFIGURATION PARAMETERS")
    print("="*60)

    # Create test data
    organizer = User.objects.filter(user_type='artist').first()
    if not organizer:
        print("❌ No organizer found. Creating test organizer...")
        organizer = User.objects.create_user(
            email=f"testorg{uuid.uuid4().hex[:6]}@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Organizer",
            user_type="artist",
            email_verified=True
        )
        # Create artist profile
        ArtistProfile.objects.create(
            user=organizer,
            display_name="Test Artist",
            sumup_merchant_code=settings.SUMUP_MERCHANT_CODE
        )

    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found")
        return

    # Create test order
    order = Order.objects.create(
        order_number=f"WIDGET-TEST-{uuid.uuid4().hex[:6]}",
        email="widgettest@example.com",
        phone="+44 7700 900123",
        delivery_first_name="Widget",
        delivery_last_name="Test",
        delivery_address_line_1="123 Test Street",
        delivery_parish="st_helier",
        delivery_postcode="JE2 3AB",
        subtotal=Decimal('30.00'),
        shipping_cost=Decimal('0.00'),
        total=Decimal('30.00'),
        status='pending'
    )

    OrderItem.objects.create(
        order=order,
        event=event,
        price=event.ticket_price,
        quantity=2
    )

    print(f"✅ Created test order: {order.order_number}")
    print(f"   Order total: £{order.total}")

    # Test widget service
    widget_service = SumUpWidgetService()

    try:
        # Create checkout for widget
        print(f"\n🔍 Creating widget checkout...")
        checkout, checkout_data = widget_service.create_checkout_for_widget(order=order)

        print(f"✅ Checkout created successfully!")
        print(f"   Checkout ID: {checkout.sumup_checkout_id}")
        print(f"   Amount: £{checkout.amount}")
        print(f"   Currency: {checkout.currency}")
        print(f"   Merchant Code: {checkout.merchant_code}")

        # Get widget configuration
        print(f"\n🔍 Getting widget configuration...")
        widget_config = widget_service.get_widget_config(checkout)

        print(f"\n📋 Widget Configuration:")
        for key, value in widget_config.items():
            print(f"   {key}: {value}")

        # Validate widget parameters
        print(f"\n🔍 Validating widget parameters...")

        # Check required parameters
        required_params = ['checkout_id', 'amount', 'currency', 'description', 'merchant_code', 'sdk_url']
        missing_params = []
        for param in required_params:
            if param not in widget_config or not widget_config[param]:
                missing_params.append(param)

        if missing_params:
            print(f"❌ Missing required parameters: {missing_params}")
        else:
            print(f"✅ All required parameters present")

        # Check parameter formats
        print(f"\n🔍 Checking parameter formats...")

        # Amount should be numeric
        if isinstance(widget_config['amount'], (int, float)):
            print(f"✅ Amount format correct: {widget_config['amount']} ({type(widget_config['amount']).__name__})")
        else:
            print(f"❌ Amount format incorrect: {widget_config['amount']} ({type(widget_config['amount']).__name__})")

        # Currency should be string
        if isinstance(widget_config['currency'], str) and len(widget_config['currency']) == 3:
            print(f"✅ Currency format correct: {widget_config['currency']}")
        else:
            print(f"❌ Currency format incorrect: {widget_config['currency']}")

        # Checkout ID should be string UUID
        if isinstance(widget_config['checkout_id'], str) and len(widget_config['checkout_id']) > 30:
            print(f"✅ Checkout ID format correct: {widget_config['checkout_id'][:20]}...")
        else:
            print(f"❌ Checkout ID format incorrect: {widget_config['checkout_id']}")

        # SDK URL should be valid
        if widget_config['sdk_url'].startswith('https://gateway.sumup.com'):
            print(f"✅ SDK URL correct: {widget_config['sdk_url']}")
        else:
            print(f"❌ SDK URL incorrect: {widget_config['sdk_url']}")

        return widget_config, checkout

    except Exception as e:
        print(f"❌ Widget test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

    finally:
        # Cleanup
        try:
            order.delete()
            print(f"\n🧹 Cleaned up test order")
        except:
            pass

def test_javascript_initialization():
    """Test the JavaScript initialization code."""
    print("\n" + "="*60)
    print("TESTING JAVASCRIPT INITIALIZATION")
    print("="*60)

    # Create a sample widget config for testing
    sample_config = {
        'checkout_id': 'test-checkout-12345-abcde-67890',
        'amount': 30.00,
        'currency': 'GBP',
        'description': 'Test widget checkout',
        'merchant_code': 'M28WNZCB',
        'sdk_url': 'https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js',
        'success_url': f"{settings.SITE_URL}/payments/widget/success/?order=TEST-123456",
        'site_url': settings.SITE_URL
    }

    print(f"📋 Sample JavaScript initialization:")
    print(f"""
SumUpCard.mount({{
    id: 'sumup-widget',
    checkoutId: '{sample_config['checkout_id']}',
    showSubmitButton: true,
    showFooter: true,
    amount: {sample_config['amount']},
    currency: '{sample_config['currency']}',
    locale: 'en-GB',
    onResponse: function (type, body) {{
        // Handle response
    }},
    onLoad: function() {{
        // Handle load
    }}
}});
""")

    # Check configuration validity
    print(f"\n🔍 Configuration validation:")
    print(f"   SDK URL: {sample_config['sdk_url']}")
    print(f"   Checkout ID length: {len(sample_config['checkout_id'])}")
    print(f"   Amount type: {type(sample_config['amount']).__name__}")
    print(f"   Currency: {sample_config['currency']}")

    return sample_config

def test_widget_endpoints():
    """Test widget-related endpoints."""
    print("\n" + "="*60)
    print("TESTING WIDGET ENDPOINTS")
    print("="*60)

    endpoints = {
        "SDK URL": "https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js",
        "Success URL": f"{settings.SITE_URL}/payments/widget/success/",
        "Cancel URL": f"{settings.SITE_URL}/payments/widget/cancel/",
        "Base Site URL": settings.SITE_URL
    }

    print(f"📋 Widget endpoints:")
    for name, url in endpoints.items():
        print(f"   {name}: {url}")

    # Test SDK URL accessibility
    print(f"\n🔍 Testing SDK URL accessibility...")
    try:
        import requests
        response = requests.head(endpoints["SDK URL"], timeout=10)
        if response.status_code == 200:
            print(f"✅ SDK URL accessible: {response.status_code}")
        else:
            print(f"⚠️  SDK URL returned: {response.status_code}")
    except Exception as e:
        print(f"❌ SDK URL test failed: {e}")

def check_widget_requirements():
    """Check all widget requirements."""
    print("\n" + "="*60)
    print("CHECKING WIDGET REQUIREMENTS")
    print("="*60)

    requirements = {
        "SUMUP_MERCHANT_CODE": settings.SUMUP_MERCHANT_CODE,
        "SUMUP_API_KEY": settings.SUMUP_API_KEY[:10] + "..." if settings.SUMUP_API_KEY else None,
        "SITE_URL": settings.SITE_URL,
        "DEBUG": settings.DEBUG
    }

    print(f"📋 Widget requirements:")
    for name, value in requirements.items():
        if value:
            print(f"   ✅ {name}: {value}")
        else:
            print(f"   ❌ {name}: Not configured")

def main():
    print("="*60)
    print("SUMUP WIDGET CONFIGURATION TEST")
    print("="*60)

    # Check requirements
    check_widget_requirements()

    # Test widget configuration
    widget_config, checkout = test_widget_configuration()

    # Test JavaScript initialization
    test_javascript_initialization()

    # Test widget endpoints
    test_widget_endpoints()

    print("\n" + "="*60)
    print("WIDGET CONFIGURATION TEST COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()