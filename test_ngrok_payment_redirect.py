#!/usr/bin/env python3
"""
Test the complete payment flow with corrected ngrok configuration.
Verifies ngrok is running on port 8000 and redirects work properly.
"""

import os
import sys
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.conf import settings
from events.models import Event
from decimal import Decimal


def test_ngrok_configuration():
    """Test ngrok is properly configured on port 8000."""
    print("🔧 Testing Ngrok Configuration")
    print("=" * 60)

    # Check ngrok status
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            tunnels = response.json().get('tunnels', [])
            if tunnels:
                tunnel = tunnels[0]
                public_url = tunnel['public_url']
                config = tunnel['config']
                addr = config.get('addr', 'unknown')

                print(f"✅ Ngrok is running:")
                print(f"   - Public URL: {public_url}")
                print(f"   - Local port: {addr}")
                print(f"   - Expected: localhost:8000")

                if '8000' in str(addr):
                    print(f"   ✅ Correctly configured on port 8000")
                else:
                    print(f"   ❌ ERROR: Running on wrong port! Should be 8000")
                    return False, None

                return True, public_url
            else:
                print("❌ No ngrok tunnels found")
                return False, None
    except Exception as e:
        print(f"❌ Cannot connect to ngrok: {e}")
        return False, None


def test_django_configuration(ngrok_url):
    """Test Django is configured with correct ngrok URL."""
    print(f"\n📝 Testing Django Configuration")
    print("=" * 60)

    # Check .env URLs
    print(f"🔍 Environment Variables:")
    print(f"   - SITE_URL: {settings.SITE_URL}")
    print(f"   - SUMUP_REDIRECT_URI: {settings.SUMUP_REDIRECT_URI}")
    print(f"   - SUMUP_SUCCESS_URL: {settings.SUMUP_SUCCESS_URL}")
    print(f"   - SUMUP_FAIL_URL: {settings.SUMUP_FAIL_URL}")

    # Extract domain from URLs
    expected_domain = ngrok_url.replace('https://', '').replace('http://', '')

    all_correct = True
    for name, value in [
        ('SITE_URL', settings.SITE_URL),
        ('SUMUP_REDIRECT_URI', settings.SUMUP_REDIRECT_URI),
        ('SUMUP_SUCCESS_URL', settings.SUMUP_SUCCESS_URL),
        ('SUMUP_FAIL_URL', settings.SUMUP_FAIL_URL)
    ]:
        if expected_domain in str(value):
            print(f"   ✅ {name} has correct ngrok domain")
        else:
            print(f"   ❌ {name} has wrong domain (not {expected_domain})")
            all_correct = False

    return all_correct


def test_payment_redirect_flow():
    """Test the complete payment redirect flow."""
    print(f"\n💳 Testing Payment Redirect Flow")
    print("=" * 60)

    client = Client()

    # Get a test event
    event = Event.objects.filter(status='published').first()
    if not event:
        print("❌ No published events found")
        return False

    print(f"✅ Using event: {event.title} (£{event.ticket_price})")

    # Step 1: Add to cart
    print(f"\n1️⃣ Adding to cart...")
    response = client.post(f'/cart/add/{event.id}/', {
        'quantity': 1
    }, follow=True)

    if response.status_code == 200:
        print("   ✅ Added to cart")
    else:
        print(f"   ❌ Failed to add to cart: {response.status_code}")
        return False

    # Step 2: Checkout
    print(f"\n2️⃣ Processing checkout...")
    response = client.post('/payments/simple-checkout/', {
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'Customer',
        'phone': '07700900123'
    }, follow=False)

    if response.status_code == 302:
        redirect_url = response.get('Location', '')
        print(f"   ✅ Checkout redirected to: {redirect_url}")

        if '/redirect/checkout/' in redirect_url:
            # Extract order ID
            order_id = redirect_url.split('/redirect/checkout/')[1].strip('/')
            print(f"   ✅ Order created with ID: {order_id}")

            # Step 3: Test SumUp redirect
            print(f"\n3️⃣ Testing SumUp redirect...")
            response = client.get(redirect_url, follow=False)

            if response.status_code == 302:
                sumup_url = response.get('Location', '')
                if 'checkout.sumup.com' in sumup_url:
                    print(f"   ✅ Successfully redirects to SumUp")
                    print(f"   🔗 SumUp URL: {sumup_url}")
                    return True
                else:
                    print(f"   ❌ Unexpected redirect: {sumup_url}")
                    return False
            else:
                print(f"   ❌ SumUp redirect failed: {response.status_code}")
                return False
        else:
            print(f"   ❌ Unexpected redirect path: {redirect_url}")
            return False
    else:
        print(f"   ❌ Checkout failed: {response.status_code}")
        return False


def main():
    """Main test function."""
    print("🚀 Ngrok Payment Redirect Configuration Test")
    print("=" * 60)

    # Test ngrok configuration
    ngrok_ok, ngrok_url = test_ngrok_configuration()
    if not ngrok_ok:
        print(f"\n❌ NGROK CONFIGURATION ERROR")
        print(f"🔧 Fix: Kill ngrok and restart with: ngrok http 8000")
        return False

    # Test Django configuration
    django_ok = test_django_configuration(ngrok_url)
    if not django_ok:
        print(f"\n⚠️ DJANGO CONFIGURATION WARNING")
        print(f"🔧 Some URLs may still use old ngrok domain")

    # Test payment flow
    flow_ok = test_payment_redirect_flow()

    # Summary
    print(f"\n" + "=" * 60)
    print(f"📊 TEST RESULTS SUMMARY")
    print(f"=" * 60)

    if ngrok_ok and django_ok and flow_ok:
        print(f"✅ COMPLETE SUCCESS!")
        print(f"   - Ngrok running on correct port 8000")
        print(f"   - Django configured with correct URLs")
        print(f"   - Payment redirect flow working")
        print(f"   - Ready for payment testing!")
        print(f"\n🎯 Next Steps:")
        print(f"1. Use the SumUp URL generated above")
        print(f"2. Enter official SumUp test card: 4200000000000042")
        print(f"3. Complete payment and verify redirect back to {ngrok_url}")
        return True
    else:
        print(f"❌ CONFIGURATION ISSUES FOUND")
        if not ngrok_ok:
            print(f"   ❌ Ngrok not running on port 8000")
        if not django_ok:
            print(f"   ⚠️ Some Django URLs incorrect")
        if not flow_ok:
            print(f"   ❌ Payment flow not working")
        print(f"\n🔧 Troubleshooting:")
        print(f"1. Ensure ngrok is running: ngrok http 8000")
        print(f"2. Update .env with new ngrok URL")
        print(f"3. Restart Django server")
        print(f"4. Verify ALLOWED_HOSTS includes ngrok domain")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)