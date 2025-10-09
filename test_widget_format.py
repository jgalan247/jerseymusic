#!/usr/bin/env python
"""Test SumUp widget parameter formats and compare against documentation."""

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
from payments.widget_service import SumUpWidgetService
from payments import sumup as sumup_api
import uuid

def test_widget_parameter_formats():
    """Test all widget parameter formats against SumUp requirements."""
    print("\n" + "="*60)
    print("TESTING WIDGET PARAMETER FORMATS")
    print("="*60)

    # Test different parameter formats
    test_cases = [
        {
            "name": "Standard amount",
            "amount": 30.00,
            "expected_type": float,
            "valid": True
        },
        {
            "name": "Integer amount",
            "amount": 30,
            "expected_type": (int, float),
            "valid": True
        },
        {
            "name": "Decimal amount",
            "amount": Decimal('30.00'),
            "expected_type": (int, float),
            "valid": True
        },
        {
            "name": "String amount",
            "amount": "30.00",
            "expected_type": str,
            "valid": False
        }
    ]

    print(f"\n🔍 Testing amount format variations:")
    for test_case in test_cases:
        amount = test_case["amount"]
        converted_amount = float(amount) if isinstance(amount, (int, float, Decimal)) else amount

        print(f"\n   Test: {test_case['name']}")
        print(f"   Input: {amount} ({type(amount).__name__})")
        print(f"   Converted: {converted_amount} ({type(converted_amount).__name__})")
        print(f"   Expected valid: {test_case['valid']}")

        if isinstance(converted_amount, (int, float)):
            print(f"   ✅ Valid format")
        else:
            print(f"   ❌ Invalid format")

def test_checkout_id_format():
    """Test checkout ID format."""
    print("\n" + "="*60)
    print("TESTING CHECKOUT ID FORMAT")
    print("="*60)

    # Create a real checkout to get actual ID format
    try:
        checkout_ref = f"format_test_{uuid.uuid4().hex[:8]}"
        checkout_data = sumup_api.create_checkout_simple(
            amount=1.00,
            currency="GBP",
            reference=checkout_ref,
            description="Format test checkout",
            return_url=f"{settings.SITE_URL}/test/",
            redirect_url=f"{settings.SITE_URL}/test/"
        )

        checkout_id = checkout_data.get('id')
        print(f"\n📋 Real checkout ID analysis:")
        print(f"   Checkout ID: {checkout_id}")
        print(f"   Length: {len(checkout_id)}")
        print(f"   Type: {type(checkout_id).__name__}")

        # Check format
        if isinstance(checkout_id, str) and len(checkout_id) >= 30:
            print(f"   ✅ Format valid")
        else:
            print(f"   ❌ Format invalid")

        # Check if it's a UUID
        try:
            import uuid
            uuid.UUID(checkout_id)
            print(f"   ✅ Valid UUID format")
        except ValueError:
            print(f"   ⚠️  Not standard UUID format (but may be valid)")

        return checkout_id

    except Exception as e:
        print(f"   ❌ Failed to create test checkout: {e}")
        return None

def test_currency_format():
    """Test currency format."""
    print("\n" + "="*60)
    print("TESTING CURRENCY FORMAT")
    print("="*60)

    currency_tests = [
        {"currency": "GBP", "valid": True, "description": "Standard ISO code"},
        {"currency": "gbp", "valid": False, "description": "Lowercase"},
        {"currency": "£", "valid": False, "description": "Symbol"},
        {"currency": "GPB", "valid": False, "description": "Typo"},
        {"currency": "USD", "valid": True, "description": "Different currency"},
    ]

    print(f"\n🔍 Testing currency formats:")
    for test in currency_tests:
        currency = test["currency"]
        valid = test["valid"]
        desc = test["description"]

        print(f"\n   Currency: '{currency}' ({desc})")
        print(f"   Length: {len(currency)}")
        print(f"   Expected valid: {valid}")

        if len(currency) == 3 and currency.isupper() and currency.isalpha():
            print(f"   ✅ Format valid")
        else:
            print(f"   ❌ Format invalid")

def test_widget_javascript_config():
    """Test widget JavaScript configuration format."""
    print("\n" + "="*60)
    print("TESTING WIDGET JAVASCRIPT CONFIGURATION")
    print("="*60)

    # Create sample configuration
    sample_config = {
        'checkout_id': 'ab123456-cd78-90ef-1234-567890abcdef',
        'amount': 30.00,
        'currency': 'GBP',
        'description': 'Test checkout',
        'merchant_code': 'M28WNZCB',
        'sdk_url': 'https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js',
        'success_url': f"{settings.SITE_URL}/payments/widget/success/",
        'site_url': settings.SITE_URL
    }

    print(f"\n📋 JavaScript configuration format:")

    # Generate JavaScript code
    js_config = f"""
SumUpCard.mount({{
    id: 'sumup-widget',
    checkoutId: '{sample_config['checkout_id']}',
    showSubmitButton: true,
    showFooter: true,
    amount: {sample_config['amount']},
    currency: '{sample_config['currency']}',
    locale: 'en-GB',
    onResponse: function (type, body) {{
        console.log('Response:', type, body);
    }},
    onLoad: function() {{
        console.log('Widget loaded');
    }}
}});
"""

    print(js_config)

    # Validate configuration
    print(f"\n🔍 Configuration validation:")

    checks = [
        ("checkoutId is string", isinstance(sample_config['checkout_id'], str)),
        ("amount is numeric", isinstance(sample_config['amount'], (int, float))),
        ("currency is 3-char string", isinstance(sample_config['currency'], str) and len(sample_config['currency']) == 3),
        ("SDK URL is HTTPS", sample_config['sdk_url'].startswith('https://')),
        ("Success URL is HTTPS", sample_config['success_url'].startswith('https://') or sample_config['success_url'].startswith('http://localhost')),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")

def test_sdk_url_accessibility():
    """Test if SumUp SDK URL is accessible."""
    print("\n" + "="*60)
    print("TESTING SDK URL ACCESSIBILITY")
    print("="*60)

    sdk_url = "https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js"

    print(f"\n🔍 Testing SDK URL: {sdk_url}")

    try:
        response = requests.get(sdk_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content-Length: {len(response.content)} bytes")

        if response.status_code == 200:
            print(f"   ✅ SDK accessible")

            # Check if it's JavaScript
            content_type = response.headers.get('Content-Type', '')
            if 'javascript' in content_type or 'text/javascript' in content_type:
                print(f"   ✅ Content type is JavaScript")
            else:
                print(f"   ⚠️  Content type is not JavaScript: {content_type}")

            # Check if content looks like JavaScript
            content = response.text[:200]
            if 'function' in content.lower() or 'var' in content.lower():
                print(f"   ✅ Content looks like JavaScript")
            else:
                print(f"   ⚠️  Content doesn't look like JavaScript")

        else:
            print(f"   ❌ SDK not accessible")

    except requests.exceptions.Timeout:
        print(f"   ❌ SDK request timed out")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ SDK request failed: {e}")

def test_merchant_code_format():
    """Test merchant code format."""
    print("\n" + "="*60)
    print("TESTING MERCHANT CODE FORMAT")
    print("="*60)

    merchant_code = settings.SUMUP_MERCHANT_CODE

    print(f"\n📋 Merchant code analysis:")
    print(f"   Code: {merchant_code}")
    print(f"   Length: {len(merchant_code)}")
    print(f"   Type: {type(merchant_code).__name__}")

    # Validate format
    checks = [
        ("Is string", isinstance(merchant_code, str)),
        ("Has content", bool(merchant_code)),
        ("Reasonable length", 5 <= len(merchant_code) <= 20),
        ("Alphanumeric", merchant_code.replace('_', '').replace('-', '').isalnum()),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")

def main():
    print("="*60)
    print("SUMUP WIDGET PARAMETER FORMAT TEST")
    print("="*60)

    # Test all parameter formats
    test_widget_parameter_formats()
    test_checkout_id_format()
    test_currency_format()
    test_merchant_code_format()
    test_widget_javascript_config()
    test_sdk_url_accessibility()

    print("\n" + "="*60)
    print("PARAMETER FORMAT TEST COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()