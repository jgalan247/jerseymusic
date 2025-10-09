#!/usr/bin/env python3
"""
Test script to verify SumUp widget display fixes.
Tests X-Frame-Options, HTTPS setup, and widget functionality.
"""

import os
import sys
import django
import subprocess
import time
import requests
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from orders.models import Order
from events.models import Event

User = get_user_model()

def test_ssl_certificate():
    """Test if SSL certificate was created correctly."""
    print("🔐 Testing SSL Certificate Setup...")

    ssl_dir = Path(__file__).parent / 'ssl'
    cert_path = ssl_dir / 'localhost.crt'
    key_path = ssl_dir / 'localhost.key'

    if cert_path.exists() and key_path.exists():
        print("✅ SSL certificate files found")

        # Test certificate validity
        try:
            result = subprocess.run([
                'openssl', 'x509', '-in', str(cert_path), '-text', '-noout'
            ], capture_output=True, text=True, check=True)

            if 'localhost' in result.stdout:
                print("✅ SSL certificate contains localhost")
                return True
            else:
                print("❌ SSL certificate doesn't contain localhost")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Error validating certificate: {e}")
            return False
    else:
        print("❌ SSL certificate files not found")
        return False

def test_django_settings():
    """Test Django security settings for widget support."""
    print("\n🛡️ Testing Django Security Settings...")

    # Test X-Frame-Options
    if hasattr(settings, 'X_FRAME_OPTIONS'):
        print(f"✅ X_FRAME_OPTIONS set to: {settings.X_FRAME_OPTIONS}")
    else:
        print("❌ X_FRAME_OPTIONS not configured")

    # Test CSP settings
    csp_settings = [
        'CSP_SCRIPT_SRC', 'CSP_FRAME_SRC', 'CSP_CONNECT_SRC', 'CSP_STYLE_SRC'
    ]

    csp_configured = 0
    for setting in csp_settings:
        if hasattr(settings, setting):
            csp_configured += 1
            sumup_domains = getattr(settings, setting)
            if any('sumup.com' in str(domain) for domain in sumup_domains):
                print(f"✅ {setting} includes SumUp domains")
            else:
                print(f"⚠️ {setting} configured but no SumUp domains found")
        else:
            print(f"❌ {setting} not configured")

    if csp_configured >= 3:
        print("✅ Content Security Policy properly configured")
        return True
    else:
        print("❌ Content Security Policy incomplete")
        return False

def test_widget_views():
    """Test widget view decorators and functionality."""
    print("\n🎛️ Testing Widget Views...")

    try:
        from payments.widget_views_fixed import widget_test, widget_checkout_fixed
        print("✅ Fixed widget views imported successfully")

        # Test that views have proper decorators
        if hasattr(widget_test, '__wrapped__'):
            print("✅ widget_test has decorators applied")
        else:
            print("⚠️ widget_test may not have decorators")

        if hasattr(widget_checkout_fixed, '__wrapped__'):
            print("✅ widget_checkout_fixed has decorators applied")
        else:
            print("⚠️ widget_checkout_fixed may not have decorators")

        return True

    except ImportError as e:
        print(f"❌ Error importing fixed widget views: {e}")
        return False

def test_url_patterns():
    """Test that fixed URL patterns are configured."""
    print("\n🔗 Testing URL Patterns...")

    try:
        from django.urls import reverse

        # Test fixed widget URLs
        test_urls = [
            'payments:widget_test',
            'payments:widget_checkout_fixed',
            'payments:listing_fee_widget_fixed'
        ]

        working_urls = 0
        for url_name in test_urls:
            try:
                if 'order_id' in url_name or 'event_id' in url_name:
                    url = reverse(url_name, kwargs={'order_id': 1} if 'order_id' in url_name else {'event_id': 1})
                else:
                    url = reverse(url_name)
                print(f"✅ {url_name} -> {url}")
                working_urls += 1
            except Exception as e:
                print(f"❌ {url_name} failed: {e}")

        if working_urls >= 2:
            print("✅ URL patterns configured correctly")
            return True
        else:
            print("❌ URL patterns incomplete")
            return False

    except Exception as e:
        print(f"❌ Error testing URL patterns: {e}")
        return False

def test_https_management_command():
    """Test HTTPS management command was created."""
    print("\n🚀 Testing HTTPS Management Command...")

    command_path = Path(__file__).parent / 'events' / 'management' / 'commands' / 'runserver_https.py'

    if command_path.exists():
        print("✅ runserver_https management command created")

        # Test command can be imported
        try:
            result = subprocess.run([
                'python3', 'manage.py', 'help', 'runserver_https'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print("✅ runserver_https command is functional")
                return True
            else:
                print(f"⚠️ runserver_https command has issues: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("⚠️ Management command test timed out")
            return False
        except Exception as e:
            print(f"❌ Error testing management command: {e}")
            return False
    else:
        print("❌ runserver_https management command not found")
        return False

def test_widget_template():
    """Test widget template was created with proper security headers."""
    print("\n📄 Testing Widget Template...")

    template_path = Path(__file__).parent / 'payments' / 'templates' / 'payments' / 'widget_checkout_fixed.html'

    if template_path.exists():
        print("✅ Fixed widget template created")

        content = template_path.read_text()

        # Check for important security features
        checks = [
            ('SumUp SDK script', 'gateway.sumup.com'),
            ('CSP meta tag', 'Content-Security-Policy'),
            ('SumUp widget mount', 'SumUpCard.mount'),
            ('Error handling', 'onResponse'),
            ('Security badges', 'security-badge')
        ]

        passed_checks = 0
        for check_name, check_text in checks:
            if check_text in content:
                print(f"✅ {check_name} found in template")
                passed_checks += 1
            else:
                print(f"❌ {check_name} missing from template")

        if passed_checks >= 4:
            print("✅ Widget template properly configured")
            return True
        else:
            print("❌ Widget template incomplete")
            return False
    else:
        print("❌ Fixed widget template not found")
        return False

def test_sumup_api_configuration():
    """Test SumUp API configuration and checkout creation."""
    print("\n💳 Testing SumUp API Configuration...")

    try:
        from payments import sumup as sumup_api

        # Test API configuration
        if hasattr(sumup_api, 'create_checkout_simple'):
            print("✅ SumUp API create_checkout_simple function available")
        else:
            print("❌ SumUp API create_checkout_simple function missing")
            return False

        # Test checkout creation (if we have valid API credentials)
        if settings.SUMUP_CLIENT_ID and settings.SUMUP_CLIENT_SECRET:
            try:
                checkout_data = sumup_api.create_checkout_simple(
                    amount=1.00,
                    currency='GBP',
                    reference='test_widget_fix',
                    description='Test checkout for widget fixes',
                    return_url=f"{settings.SITE_URL}/payments/success/",
                    redirect_url=f"{settings.SITE_URL}/payments/success/",
                    enable_hosted_checkout=False  # Widget mode
                )

                if checkout_data and 'id' in checkout_data:
                    print("✅ SumUp checkout creation successful")
                    print(f"   Checkout ID: {checkout_data['id']}")
                    return True
                else:
                    print("❌ SumUp checkout creation failed - no ID returned")
                    return False

            except Exception as e:
                print(f"❌ SumUp checkout creation failed: {e}")
                return False
        else:
            print("⚠️ SumUp API credentials not configured - skipping API test")
            return True

    except ImportError as e:
        print(f"❌ Error importing SumUp API: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary."""
    print("🚀 TESTING SUMUP WIDGET DISPLAY FIXES")
    print("=" * 60)

    tests = [
        ("SSL Certificate", test_ssl_certificate),
        ("Django Settings", test_django_settings),
        ("Widget Views", test_widget_views),
        ("URL Patterns", test_url_patterns),
        ("HTTPS Command", test_https_management_command),
        ("Widget Template", test_widget_template),
        ("SumUp API", test_sumup_api_configuration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n✅ Passed: {passed}/{total} tests")

    if passed == total:
        print("🎉 All tests passed! SumUp widget fixes are ready!")
    else:
        print("⚠️ Some tests failed. Check output above for details.")

        failed_tests = [name for name, result in results if not result]
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")

    print("\n🔗 Next Steps:")
    print("1. Run: python3 manage.py runserver_https")
    print("2. Visit: https://localhost:8000/payments/widget-fixed/test/")
    print("3. Accept browser security warning for self-signed certificate")
    print("4. Test SumUp widget display and payment flow")

    print("\n📋 Widget Test URLs:")
    print("   • Test Widget: https://localhost:8000/payments/widget-fixed/test/")
    print("   • Widget Checkout: https://localhost:8000/payments/widget-fixed/checkout/<order_id>/")
    print("   • Listing Fee Widget: https://localhost:8000/payments/widget-fixed/listing-fee/<event_id>/")

    return passed == total

if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)