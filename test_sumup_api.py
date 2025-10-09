#!/usr/bin/env python
"""Test SumUp API integration with correct versioned endpoints."""

import os
import sys
import django
import json
import requests
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from payments import sumup as sumup_api
from datetime import datetime
import uuid

def test_api_endpoint_configuration():
    """Test that API endpoints are correctly configured."""
    print("\n" + "="*60)
    print("TESTING SUMUP API ENDPOINT CONFIGURATION")
    print("="*60)

    print(f"\nBase URL: {settings.SUMUP_BASE_URL}")
    print(f"API URL (with version): {settings.SUMUP_API_URL}")
    print(f"Expected checkout endpoint: {settings.SUMUP_API_URL}/checkouts")

    # Verify the URL structure
    if not settings.SUMUP_API_URL.endswith('/v0.1'):
        print("❌ WARNING: SUMUP_API_URL should end with /v0.1")
    else:
        print("✅ API URL correctly includes version /v0.1")

    return True

def test_authentication():
    """Test platform authentication."""
    print("\n" + "="*60)
    print("TESTING PLATFORM AUTHENTICATION")
    print("="*60)

    try:
        # Test getting platform access token
        if settings.SUMUP_API_KEY:
            print(f"✅ Using API Key authentication")
            print(f"   API Key: {settings.SUMUP_API_KEY[:10]}...")
            access_token = settings.SUMUP_API_KEY
        else:
            print("🔍 Attempting to get platform access token...")
            access_token = sumup_api.get_platform_access_token()
            print(f"✅ Access token obtained: {access_token[:20]}...")

        return access_token
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def test_checkout_creation_raw(access_token):
    """Test checkout creation with raw requests (matching curl example)."""
    print("\n" + "="*60)
    print("TESTING RAW CHECKOUT CREATION (MATCHING CURL)")
    print("="*60)

    # Generate unique reference
    checkout_ref = f"test_{uuid.uuid4().hex[:8]}"

    # Build request exactly as in curl example
    url = f"{settings.SUMUP_API_URL}/checkouts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "checkout_reference": checkout_ref,
        "amount": 10.00,
        "currency": "GBP",
        "merchant_code": settings.SUMUP_MERCHANT_CODE,
        "description": "Test checkout from Jersey Events"
    }

    print(f"\n📋 Request Details:")
    print(f"   URL: {url}")
    print(f"   Headers: {json.dumps(headers, indent=2)}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")

    try:
        print(f"\n🔍 Sending POST request...")
        response = requests.post(url, headers=headers, json=payload, timeout=20)

        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")

        if response.status_code == 201:
            data = response.json()
            print(f"\n✅ Checkout created successfully!")
            print(f"   Checkout ID: {data.get('id')}")
            print(f"   Checkout URL: {data.get('checkout_url')}")
            print(f"   Full response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            print(f"   Response body: {response.text}")
            return None

    except Exception as e:
        print(f"\n❌ Request failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_checkout_creation_via_api(access_token):
    """Test checkout creation using our API wrapper."""
    print("\n" + "="*60)
    print("TESTING CHECKOUT CREATION VIA API WRAPPER")
    print("="*60)

    # Generate unique reference
    checkout_ref = f"test_{uuid.uuid4().hex[:8]}"

    try:
        print(f"\n🔍 Creating checkout via sumup.create_checkout_simple...")

        checkout_data = sumup_api.create_checkout_simple(
            amount=15.00,
            currency="GBP",
            reference=checkout_ref,
            description="Test checkout via API wrapper",
            return_url=f"{settings.SITE_URL}/payments/success/test/",
            redirect_url=f"{settings.SITE_URL}/payments/success/test/"
        )

        print(f"\n✅ Checkout created successfully!")
        print(f"   Checkout ID: {checkout_data.get('id')}")
        print(f"   Checkout URL: {checkout_data.get('checkout_url')}")
        print(f"   Full response: {json.dumps(checkout_data, indent=2)}")
        return checkout_data

    except Exception as e:
        print(f"\n❌ Checkout creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_checkout_status(checkout_id, access_token):
    """Test getting checkout status."""
    print("\n" + "="*60)
    print("TESTING CHECKOUT STATUS RETRIEVAL")
    print("="*60)

    try:
        print(f"\n🔍 Getting status for checkout: {checkout_id}")

        # Try via API wrapper
        status = sumup_api.get_checkout_status(checkout_id)

        print(f"\n✅ Checkout status retrieved!")
        print(f"   Status: {status.get('status')}")
        print(f"   Amount: {status.get('amount')} {status.get('currency')}")
        print(f"   Full response: {json.dumps(status, indent=2)}")
        return status

    except Exception as e:
        print(f"\n❌ Status retrieval failed: {e}")
        return None

def check_merchant_code():
    """Check if merchant code is configured."""
    print("\n" + "="*60)
    print("CHECKING MERCHANT CODE CONFIGURATION")
    print("="*60)

    if not settings.SUMUP_MERCHANT_CODE:
        print("❌ SUMUP_MERCHANT_CODE not configured in .env file")
        print("   This is required for creating checkouts")
        return False
    else:
        print(f"✅ Merchant code configured: {settings.SUMUP_MERCHANT_CODE}")
        return True

def main():
    print("="*60)
    print("SUMUP API INTEGRATION TEST")
    print("="*60)

    # Check configuration
    if not test_api_endpoint_configuration():
        print("\n❌ API endpoint configuration issues detected")
        return

    # Check merchant code
    if not check_merchant_code():
        print("\n❌ Missing merchant code. Please add SUMUP_MERCHANT_CODE to .env file")
        return

    # Test authentication
    access_token = test_authentication()
    if not access_token:
        print("\n❌ Authentication failed. Cannot proceed with tests.")
        return

    # Test raw checkout creation (matching curl)
    checkout_data = test_checkout_creation_raw(access_token)

    if checkout_data:
        # Test status retrieval
        test_checkout_status(checkout_data['id'], access_token)

    # Test via API wrapper
    test_checkout_creation_via_api(access_token)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()