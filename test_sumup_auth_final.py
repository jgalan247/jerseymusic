#!/usr/bin/env python3
"""
Test the complete SumUp authentication flow.
"""

import os
import sys
import django
from decimal import Decimal
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from payments import sumup
import json

def test_authentication():
    """Test getting an access token."""
    print("=" * 60)
    print("Testing SumUp Authentication")
    print("=" * 60)

    try:
        token = sumup.get_platform_access_token()
        print(f"✅ Successfully got access token: {token[:20]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        return False

def test_checkout_creation():
    """Test creating a checkout with authentication."""
    print("\n" + "=" * 60)
    print("Testing Checkout Creation")
    print("=" * 60)

    # Generate unique reference
    checkout_ref = f"test_{uuid.uuid4().hex[:8]}"

    try:
        result = sumup.create_checkout_simple(
            amount=10.00,
            currency="GBP",
            reference=checkout_ref,
            description="Test checkout with auth",
            return_url="https://86a7ab44d9e2.ngrok-free.app/payments/success/"
        )

        print(f"✅ Checkout created successfully!")
        print(f"   Reference: {checkout_ref}")
        print(f"   Checkout ID: {result.get('id', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        print(f"   Checkout URL: {result.get('checkout_url', 'N/A')}")

        return True, result.get('id')
    except Exception as e:
        print(f"❌ Failed to create checkout: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text[:500]}")
        return False, None

def test_checkout_status(checkout_id):
    """Test getting checkout status."""
    print("\n" + "=" * 60)
    print("Testing Checkout Status Retrieval")
    print("=" * 60)

    if not checkout_id:
        print("⚠️  No checkout ID available")
        return False

    try:
        result = sumup.get_checkout_status(checkout_id)
        print(f"✅ Successfully retrieved checkout status")
        print(f"   Checkout ID: {checkout_id}")
        print(f"   Status: {result.get('status', 'N/A')}")
        print(f"   Amount: {result.get('amount', 'N/A')} {result.get('currency', '')}")
        return True
    except Exception as e:
        print(f"❌ Failed to get checkout status: {e}")
        return False

def test_environment():
    """Test environment configuration."""
    print("=" * 60)
    print("Environment Configuration")
    print("=" * 60)

    config = {
        'CLIENT_ID': settings.SUMUP_CLIENT_ID,
        'CLIENT_SECRET': settings.SUMUP_CLIENT_SECRET[:10] + '...' if settings.SUMUP_CLIENT_SECRET else None,
        'MERCHANT_CODE': settings.SUMUP_MERCHANT_CODE,
        'MERCHANT_ID': settings.SUMUP_MERCHANT_ID,
        'API_KEY': settings.SUMUP_API_KEY[:20] + '...' if settings.SUMUP_API_KEY else None,
        'BASE_URL': settings.SUMUP_BASE_URL,
        'API_URL': settings.SUMUP_API_URL,
    }

    for key, value in config.items():
        status = "✅" if value else "❌"
        print(f"{status} {key:15} = {value or '[NOT SET]'}")

    return all([
        settings.SUMUP_CLIENT_ID,
        settings.SUMUP_CLIENT_SECRET,
        settings.SUMUP_MERCHANT_CODE
    ])

def main():
    """Run all tests."""
    print("SumUp Complete Authentication Flow Test")
    print("Using ngrok URL: https://86a7ab44d9e2.ngrok-free.app")
    print()

    # Test 1: Environment
    env_ok = test_environment()

    # Test 2: Authentication
    auth_ok = test_authentication() if env_ok else False

    # Test 3: Checkout creation
    checkout_ok = False
    checkout_id = None
    if auth_ok:
        checkout_ok, checkout_id = test_checkout_creation()

    # Test 4: Checkout status
    status_ok = test_checkout_status(checkout_id) if checkout_ok else False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    tests = [
        ("Environment Configuration", env_ok),
        ("Authentication", auth_ok),
        ("Checkout Creation", checkout_ok),
        ("Status Retrieval", status_ok),
    ]

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! SumUp authentication is working correctly.")
        print("\nNext steps:")
        print("1. Try purchasing tickets through the web interface")
        print("2. Monitor Django logs for any errors")
        print("3. Check SumUp dashboard for incoming checkouts")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        if not env_ok:
            print("\nFix environment variables first:")
            print("- Ensure SUMUP_MERCHANT_CODE is set")
            print("- Check CLIENT_ID and CLIENT_SECRET are correct")
        elif not auth_ok:
            print("\nAuthentication issues:")
            print("- Verify credentials are for the correct environment")
            print("- Check if using sandbox vs production API")
        elif not checkout_ok:
            print("\nCheckout creation issues:")
            print("- Verify merchant code is valid")
            print("- Check API endpoint URLs")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)