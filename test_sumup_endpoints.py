#!/usr/bin/env python
"""Test all SumUp API endpoints to verify they use correct versioned URLs."""

import os
import sys
import django
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from payments import sumup as sumup_api

def test_endpoint_configuration():
    """Test that all endpoint configurations are correct."""
    print("\n" + "="*60)
    print("TESTING ENDPOINT CONFIGURATION")
    print("="*60)

    print(f"\n📋 SumUp Configuration:")
    print(f"   BASE_URL: {settings.SUMUP_BASE_URL}")
    print(f"   API_URL: {settings.SUMUP_API_URL}")
    print(f"   Merchant Code: {settings.SUMUP_MERCHANT_CODE}")

    # Check if API_URL includes version
    if "/v0.1" in settings.SUMUP_API_URL:
        print("✅ API_URL correctly includes /v0.1 version")
    else:
        print("❌ API_URL missing /v0.1 version")
        return False

    # Expected endpoints
    expected_endpoints = {
        "Token": f"{settings.SUMUP_BASE_URL}/token",
        "OAuth": f"{settings.SUMUP_BASE_URL}/authorize",
        "Checkouts": f"{settings.SUMUP_API_URL}/checkouts",
        "Me": f"{settings.SUMUP_API_URL}/me",
        "Transactions": f"{settings.SUMUP_API_URL}/me/transactions/history"
    }

    print(f"\n📋 Expected API Endpoints:")
    for name, url in expected_endpoints.items():
        print(f"   {name}: {url}")

    return True

def test_checkouts_endpoint():
    """Test checkouts endpoint (uses API_URL with version)."""
    print("\n" + "="*60)
    print("TESTING CHECKOUTS ENDPOINT")
    print("="*60)

    try:
        url = f"{settings.SUMUP_API_URL}/checkouts"
        print(f"🔍 Testing URL: {url}")

        # Test checkout creation via sumup.py wrapper
        print(f"\n📋 Testing via sumup.create_checkout_simple()...")

        checkout_ref = f"endpoint_test_{uuid.uuid4().hex[:8]}"
        checkout_data = sumup_api.create_checkout_simple(
            amount=12.34,
            currency="GBP",
            reference=checkout_ref,
            description="Endpoint test checkout",
            return_url=f"{settings.SITE_URL}/test/",
            redirect_url=f"{settings.SITE_URL}/test/"
        )

        print(f"✅ Checkout created successfully")
        print(f"   Checkout ID: {checkout_data.get('id')}")
        print(f"   Amount: {checkout_data.get('amount')} {checkout_data.get('currency')}")
        print(f"   Status: {checkout_data.get('status')}")

        return True

    except Exception as e:
        print(f"❌ Checkouts endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("SUMUP ENDPOINT VERIFICATION TEST")
    print("="*60)

    # Test configuration
    if not test_endpoint_configuration():
        print("\n❌ Endpoint configuration failed. Exiting.")
        return

    # Test checkouts endpoint
    test_checkouts_endpoint()

    print("\n" + "="*60)
    print("ENDPOINT VERIFICATION COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()