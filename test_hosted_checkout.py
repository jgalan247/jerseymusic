#!/usr/bin/env python3
"""Test hosted checkout creation with Django."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from payments import sumup as sumup_api
from django.conf import settings

def test_hosted_checkout():
    """Test creating a hosted checkout."""
    print("=" * 60)
    print("TESTING HOSTED CHECKOUT CREATION")
    print("=" * 60)

    try:
        # Create hosted checkout
        checkout_data = sumup_api.create_checkout_simple(
            amount=25.00,
            currency='GBP',
            reference=f"hosted_test_{int(time.time())}",
            description="Hosted checkout test",
            return_url="http://localhost:8000/success",
            redirect_url="http://localhost:8000/success",
            enable_hosted_checkout=True
        )

        print(f"✅ Hosted checkout created!")
        print(f"Checkout ID: {checkout_data.get('id')}")
        print(f"Hosted URL: {checkout_data.get('hosted_checkout_url', 'NOT_PROVIDED')}")
        print(f"Status: {checkout_data.get('status')}")

        # Construct fallback URL
        checkout_id = checkout_data.get('id')
        if checkout_id:
            fallback_url = f"https://checkout.sumup.com/pay/{checkout_id}"
            print(f"Fallback URL: {fallback_url}")

        print("\n📋 Test URLs:")
        print(f"1. Widget test: http://localhost:8000/test_dual_payment_approach.html")
        print(f"2. Hosted test: {checkout_data.get('hosted_checkout_url', fallback_url)}")

        return True

    except Exception as e:
        print(f"❌ Hosted checkout creation failed: {e}")
        return False

if __name__ == '__main__':
    import time
    test_hosted_checkout()