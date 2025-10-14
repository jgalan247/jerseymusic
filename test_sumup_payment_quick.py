#!/usr/bin/env python
"""
Quick SumUp Payment Test - Real API

Tests actual SumUp payment functionality with real API calls.
Creates a simple checkout and provides payment URL.

Usage:
    python test_sumup_payment_quick.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from payments import sumup as sumup_api
from datetime import datetime
import requests


def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text}")
    print(f"{'='*80}\n")


def print_success(text):
    print(f"✅ {text}")


def print_error(text):
    print(f"❌ {text}")


def print_info(text):
    print(f"ℹ️  {text}")


def test_platform_token():
    """Test 1: Get platform access token."""
    print_header("Test 1: Platform Access Token")

    try:
        print_info("Requesting platform token from SumUp...")
        token = sumup_api.get_platform_access_token()

        if token:
            print_success(f"Token retrieved: {token[:20]}...")
            print_info(f"Token length: {len(token)} characters")
            return token
        else:
            print_error("No token returned")
            return None

    except Exception as e:
        print_error(f"Token retrieval failed: {e}")
        return None


def test_create_checkout(token):
    """Test 2: Create a real checkout."""
    print_header("Test 2: Create Real Checkout")

    try:
        # Checkout details
        amount = 5.00  # £5.00 test amount
        currency = 'GBP'
        reference = f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        description = 'Jersey Events - Test Payment'
        return_url = 'http://localhost:8000/payments/sumup/success/'

        print_info(f"Amount: £{amount}")
        print_info(f"Reference: {reference}")
        print_info(f"Description: {description}")

        # Create checkout
        print_info("\nCalling SumUp API to create checkout...")

        checkout_data = sumup_api.create_checkout_simple(
            amount=amount,
            currency=currency,
            reference=reference,
            description=description,
            return_url=return_url,
            expected_amount=amount
        )

        if checkout_data and 'id' in checkout_data:
            print_success("Checkout created successfully!")
            print()
            print(f"Checkout ID: {checkout_data['id']}")
            print(f"Status: {checkout_data.get('status', 'unknown')}")
            print(f"Amount: £{checkout_data.get('amount', 0)}")
            print(f"Currency: {checkout_data.get('currency', 'N/A')}")

            if 'checkout_url' in checkout_data:
                print()
                print("="*80)
                print("PAYMENT URL:")
                print(checkout_data['checkout_url'])
                print("="*80)
                print()
                print_info("To complete payment:")
                print("  1. Open the URL above in your browser")
                print("  2. Use test card: 4242 4242 4242 4242")
                print("  3. CVV: 123, Expiry: 12/25 (any future date)")
                print()

            return checkout_data
        else:
            print_error("Checkout creation failed")
            print(f"Response: {checkout_data}")
            return None

    except Exception as e:
        print_error(f"Checkout creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_checkout_status(checkout_id, token):
    """Test 3: Check checkout status."""
    print_header("Test 3: Check Checkout Status")

    try:
        print_info(f"Checking status for checkout: {checkout_id}")

        # Use SumUp API directly
        api_url = settings.SUMUP_API_URL if hasattr(settings, 'SUMUP_API_URL') else 'https://api.sumup.com/v0.1'
        url = f"{api_url}/checkouts/{checkout_id}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            status_data = response.json()
            print_success("Status retrieved successfully")
            print()
            print(f"Status: {status_data.get('status', 'unknown')}")
            print(f"Amount: £{status_data.get('amount', 0)}")
            print(f"Currency: {status_data.get('currency', 'N/A')}")
            print(f"Reference: {status_data.get('merchant_code', 'N/A')}")

            if status_data.get('transactions'):
                print("\nTransactions:")
                for tx in status_data['transactions']:
                    print(f"  - {tx.get('type')}: {tx.get('status')}")
                    if tx.get('amount'):
                        print(f"    Amount: £{tx['amount']}")

            return status_data
        else:
            print_error(f"Status check failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None

    except Exception as e:
        print_error(f"Status check failed: {e}")
        return None


def main():
    """Run all tests."""
    print_header("SumUp Payment Test - Real API")
    print("This will make REAL API calls to SumUp")
    print()

    # Check credentials
    print_info("Checking credentials...")
    if not settings.SUMUP_CLIENT_ID or not settings.SUMUP_CLIENT_SECRET:
        print_error("SumUp credentials not configured in .env")
        return

    print_success(f"Client ID: {settings.SUMUP_CLIENT_ID[:20]}...")
    print_success(f"Merchant Code: {settings.SUMUP_MERCHANT_CODE}")
    print()

    input("Press Enter to start testing...")

    # Test 1: Platform token
    token = test_platform_token()
    if not token:
        print_error("Cannot continue without token")
        return

    # Test 2: Create checkout
    checkout = test_create_checkout(token)
    if not checkout:
        print_error("Cannot continue without checkout")
        return

    checkout_id = checkout.get('id')

    # Test 3: Check status
    print()
    input("Press Enter to check checkout status...")
    test_checkout_status(checkout_id, token)

    # Summary
    print_header("Test Complete")
    print_success("All API tests completed!")
    print()
    print("Summary:")
    print(f"  - Checkout ID: {checkout_id}")
    print(f"  - Amount: £{checkout.get('amount', 0)}")
    if 'checkout_url' in checkout:
        print()
        print("Payment URL:")
        print(checkout['checkout_url'])
    print()
    print_info("To verify payment:")
    print("  1. Complete payment using the URL above")
    print("  2. Wait a few minutes")
    print("  3. Run the payment polling service:")
    print("     python manage.py run_payment_polling --verbose")
    print()


if __name__ == '__main__':
    main()
