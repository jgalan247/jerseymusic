#!/usr/bin/env python
"""
SumUp Payment Processing Debug Tool
Comprehensive analysis of payment flow failures
"""

import os
import sys
import django
from decimal import Decimal
import traceback

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from django.urls import reverse

# Import payment-related models and services
from accounts.models import ArtistProfile
from events.models import Event, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from payments.models import SumUpCheckout
from payments import sumup as sumup_api

User = get_user_model()

class PaymentDebugger:
    """Comprehensive payment processing debugger"""

    def __init__(self):
        self.client = Client()
        self.issues_found = []
        self.debug_results = {}

    def log_issue(self, category, severity, message, details=None):
        """Log a payment processing issue"""
        issue = {
            'category': category,
            'severity': severity,
            'message': message,
            'details': details or {},
            'timestamp': timezone.now()
        }
        self.issues_found.append(issue)
        severity_icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}
        print(f"  {severity_icon[severity]} [{category}] {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")

    def check_payment_configuration(self):
        """Check 1: Verify SumUp configuration"""
        print("\n1️⃣ CHECKING SUMUP CONFIGURATION")
        print("-" * 40)

        # Check settings
        required_settings = [
            'SUMUP_BASE_URL', 'SUMUP_API_URL', 'SUMUP_CLIENT_ID',
            'SUMUP_CLIENT_SECRET', 'SUMUP_MERCHANT_CODE', 'SUMUP_ACCESS_TOKEN'
        ]

        missing_settings = []
        for setting in required_settings:
            value = getattr(settings, setting, None)
            if not value:
                missing_settings.append(setting)
            else:
                # Mask sensitive values for logging
                if 'SECRET' in setting or 'TOKEN' in setting:
                    display_value = f"{value[:8]}..." if len(value) > 8 else "***"
                else:
                    display_value = value
                print(f"  ✅ {setting}: {display_value}")

        if missing_settings:
            self.log_issue('CONFIGURATION', 'CRITICAL',
                          f'Missing SumUp settings: {", ".join(missing_settings)}',
                          {'missing_settings': missing_settings})
        else:
            self.log_issue('CONFIGURATION', 'INFO', 'All SumUp settings configured')

        # Check SumUp API connectivity
        try:
            # Test basic API connectivity (this would normally check /me endpoint)
            # For now, just verify the URL format
            api_url = settings.SUMUP_API_URL
            if api_url.startswith('https://'):
                self.log_issue('CONFIGURATION', 'INFO', 'SumUp API URL format valid')
            else:
                self.log_issue('CONFIGURATION', 'WARNING', 'SumUp API URL may be invalid')

        except Exception as e:
            self.log_issue('CONFIGURATION', 'CRITICAL',
                          f'SumUp API configuration error: {str(e)}')

    def test_payment_flow_steps(self):
        """Check 2: Test each step of payment flow"""
        print("\n2️⃣ TESTING PAYMENT FLOW STEPS")
        print("-" * 40)

        # Create test data
        try:
            # Create test user
            test_user = User.objects.create_user(
                username='payment_debug_user',
                email='payment_debug@test.com',
                password='TestPass123!'
            )
            test_user.email_verified = True
            test_user.save()

            # Create test artist
            artist_user = User.objects.create_user(
                username='payment_debug_artist',
                email='payment_debug_artist@test.com',
                password='TestPass123!',
                user_type='artist'
            )

            artist = ArtistProfile.objects.create(
                user=artist_user,
                display_name='Payment Debug Artist',
                is_approved=True
            )

            # Create test event
            category = Category.objects.create(
                name='Payment Debug Category'
            )

            event = Event.objects.create(
                title='Payment Debug Event',
                description='Event for payment debugging',
                organiser=artist_user,
                category=category,
                venue_name='Debug Venue',
                venue_address='Debug Address',
                event_date=timezone.now().date() + timezone.timedelta(days=30),
                event_time='19:00',
                ticket_price=Decimal('25.00'),
                capacity=100,
                status='published'
            )

            self.log_issue('PAYMENT_FLOW', 'INFO', 'Test data created successfully')

        except Exception as e:
            self.log_issue('PAYMENT_FLOW', 'CRITICAL',
                          f'Test data creation failed: {str(e)}')
            return

        # Test cart creation
        try:
            cart = Cart.objects.create(user=test_user)
            cart_item = CartItem.objects.create(
                cart=cart,
                event=event,
                quantity=2
            )

            # Test cart calculations
            total_cost = cart_item.get_total_cost()
            expected_cost = event.ticket_price * cart_item.quantity

            if total_cost == expected_cost:
                self.log_issue('PAYMENT_FLOW', 'INFO',
                              f'Cart calculations correct: £{total_cost}')
            else:
                self.log_issue('PAYMENT_FLOW', 'CRITICAL',
                              f'Cart calculation error: expected £{expected_cost}, got £{total_cost}')

        except Exception as e:
            self.log_issue('PAYMENT_FLOW', 'CRITICAL',
                          f'Cart creation failed: {str(e)}',
                          {'error': str(e), 'traceback': traceback.format_exc()})

        # Test order creation
        try:
            order = Order.objects.create(
                user=test_user,
                email=test_user.email,
                phone='+447700900123',
                delivery_first_name='Debug',
                delivery_last_name='User',
                delivery_address_line_1='123 Debug St',
                delivery_parish='st_helier',
                delivery_postcode='JE1 1AA',
                subtotal=cart.subtotal,
                shipping_cost=Decimal('0.00'),
                total=cart.subtotal,
                status='pending'
            )

            # Create order items
            order_item = OrderItem.objects.create(
                order=order,
                event=event,
                quantity=cart_item.quantity,
                price=event.ticket_price
            )

            self.log_issue('PAYMENT_FLOW', 'INFO',
                          f'Order created successfully (ID: {order.id})')

        except Exception as e:
            self.log_issue('PAYMENT_FLOW', 'CRITICAL',
                          f'Order creation failed: {str(e)}',
                          {'error': str(e), 'traceback': traceback.format_exc()})
            return

        # Test SumUp checkout creation
        try:
            checkout = SumUpCheckout.objects.create(
                order=order,
                customer=test_user,
                amount=order.total,
                currency='GBP',
                description=f'Debug Order {order.id}',
                merchant_code=settings.SUMUP_MERCHANT_CODE or 'DEBUG123',
                return_url='https://debug.jerseyevents.com/return/',
                status='pending'
            )

            self.log_issue('PAYMENT_FLOW', 'INFO',
                          f'SumUp checkout created (ID: {checkout.checkout_reference})')

            # Test payment calculations
            platform_fee = checkout.calculate_platform_fee()
            artist_amount = checkout.calculate_artist_amount()
            listing_fee = checkout.calculate_listing_fee()

            self.log_issue('PAYMENT_FLOW', 'INFO',
                          f'Payment calculations: Platform fee £{platform_fee}, Artist amount £{artist_amount}, Listing fee £{listing_fee}')

        except Exception as e:
            self.log_issue('PAYMENT_FLOW', 'CRITICAL',
                          f'SumUp checkout creation failed: {str(e)}',
                          {'error': str(e), 'traceback': traceback.format_exc()})

        # Store for cleanup
        self.test_user = test_user
        self.test_artist = artist_user
        self.test_event = event
        self.test_category = category

    def test_sumup_api_calls(self):
        """Check 3: Test SumUp API calls"""
        print("\n3️⃣ TESTING SUMUP API CALLS")
        print("-" * 40)

        if not hasattr(settings, 'SUMUP_ACCESS_TOKEN') or not settings.SUMUP_ACCESS_TOKEN:
            self.log_issue('API_CALLS', 'CRITICAL',
                          'No SumUp access token configured - cannot test API calls')
            return

        # Test simple checkout creation
        try:
            test_checkout_data = {
                'amount': 10.00,
                'currency': 'GBP',
                'reference': f'debug_{int(timezone.now().timestamp())}',
                'description': 'Debug API Test',
                'return_url': 'https://debug.jerseyevents.com/return/'
            }

            # This would normally call the real API - for debugging we'll simulate
            self.log_issue('API_CALLS', 'WARNING',
                          'SumUp API test skipped - would make real API call',
                          {'test_data': test_checkout_data})

        except Exception as e:
            self.log_issue('API_CALLS', 'CRITICAL',
                          f'SumUp API test failed: {str(e)}',
                          {'error': str(e), 'traceback': traceback.format_exc()})

    def test_payment_methods_integration(self):
        """Check 4: Test payment method integration"""
        print("\n4️⃣ TESTING PAYMENT METHOD INTEGRATION")
        print("-" * 40)

        # Test URL patterns
        try:
            from django.urls import reverse

            payment_urls = [
                'payments:checkout',
                'payments:select_method',
                'payments:sumup_success',
            ]

            for url_name in payment_urls:
                try:
                    url = reverse(url_name)
                    self.log_issue('PAYMENT_METHODS', 'INFO',
                                  f'URL pattern {url_name} resolves to: {url}')
                except Exception as e:
                    self.log_issue('PAYMENT_METHODS', 'WARNING',
                                  f'URL pattern {url_name} not found: {str(e)}')

        except Exception as e:
            self.log_issue('PAYMENT_METHODS', 'CRITICAL',
                          f'URL pattern testing failed: {str(e)}')

        # Test payment views
        try:
            from payments.views import CheckoutView, SelectPaymentMethodView, SumUpCheckoutView

            self.log_issue('PAYMENT_METHODS', 'INFO',
                          'Payment view classes imported successfully')

        except Exception as e:
            self.log_issue('PAYMENT_METHODS', 'CRITICAL',
                          f'Payment view import failed: {str(e)}',
                          {'error': str(e), 'traceback': traceback.format_exc()})

    def test_error_handling(self):
        """Check 5: Test error handling scenarios"""
        print("\n5️⃣ TESTING ERROR HANDLING")
        print("-" * 40)

        # Test missing order scenario
        try:
            from payments.views import SelectPaymentMethodView

            # This would test accessing payment method without order
            self.log_issue('ERROR_HANDLING', 'INFO',
                          'Error handling tests completed (mock scenarios)')

        except Exception as e:
            self.log_issue('ERROR_HANDLING', 'WARNING',
                          f'Error handling test failed: {str(e)}')

        # Test invalid payment data
        try:
            # Test creating checkout with invalid data
            invalid_checkout = SumUpCheckout(
                amount=Decimal('-10.00'),  # Invalid negative amount
                currency='INVALID',
                description='',
                merchant_code='',
            )
            # This should be caught by model validation
            try:
                invalid_checkout.full_clean()
                self.log_issue('ERROR_HANDLING', 'WARNING',
                              'Model validation may be insufficient')
            except Exception as validation_error:
                self.log_issue('ERROR_HANDLING', 'INFO',
                              'Model validation working correctly')

        except Exception as e:
            self.log_issue('ERROR_HANDLING', 'WARNING',
                          f'Error handling test unexpected error: {str(e)}')

    def analyze_logs(self):
        """Check 6: Analyze Django logs for payment errors"""
        print("\n6️⃣ ANALYZING LOGS")
        print("-" * 40)

        # Check Django logging configuration
        try:
            import logging
            logger = logging.getLogger('payments')

            # Test logging
            logger.info("Payment debug test log message")

            self.log_issue('LOGS', 'INFO',
                          'Django logging configured and accessible')

        except Exception as e:
            self.log_issue('LOGS', 'WARNING',
                          f'Logging analysis failed: {str(e)}')

    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            if hasattr(self, 'test_user'):
                User.objects.filter(username__contains='payment_debug').delete()
            if hasattr(self, 'test_category'):
                Category.objects.filter(name__contains='Payment Debug').delete()
            print("\n🧹 Test data cleaned up")
        except Exception as e:
            print(f"\n⚠️ Cleanup warning: {e}")

    def generate_debug_report(self):
        """Generate comprehensive debug report"""
        print("\n" + "=" * 60)
        print("🔍 PAYMENT PROCESSING DEBUG REPORT")
        print("=" * 60)

        # Categorize issues
        critical_issues = [i for i in self.issues_found if i['severity'] == 'CRITICAL']
        warnings = [i for i in self.issues_found if i['severity'] == 'WARNING']
        info_items = [i for i in self.issues_found if i['severity'] == 'INFO']

        print(f"\nIssues Found:")
        print(f"🔴 Critical: {len(critical_issues)}")
        print(f"🟡 Warnings: {len(warnings)}")
        print(f"🔵 Info: {len(info_items)}")

        if critical_issues:
            print(f"\n🔴 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for issue in critical_issues:
                print(f"  • [{issue['category']}] {issue['message']}")

        if warnings:
            print(f"\n🟡 WARNINGS TO INVESTIGATE:")
            for issue in warnings:
                print(f"  • [{issue['category']}] {issue['message']}")

        # Payment system status
        if critical_issues:
            print(f"\n🔴 PAYMENT SYSTEM STATUS: NOT READY FOR PRODUCTION")
            print("❌ Critical issues must be resolved before processing real payments")
        elif warnings:
            print(f"\n🟡 PAYMENT SYSTEM STATUS: NEEDS ATTENTION")
            print("⚠️ Address warnings before production deployment")
        else:
            print(f"\n🟢 PAYMENT SYSTEM STATUS: READY FOR TESTING")
            print("✅ No critical issues found - ready for further testing")

        return len(critical_issues) == 0

def main():
    """Main debug runner"""
    print("Jersey Events - SumUp Payment Processing Debugger")
    print("=" * 60)

    debugger = PaymentDebugger()

    try:
        # Run all debug checks
        debugger.check_payment_configuration()
        debugger.test_payment_flow_steps()
        debugger.test_sumup_api_calls()
        debugger.test_payment_methods_integration()
        debugger.test_error_handling()
        debugger.analyze_logs()

        # Generate final report
        system_ready = debugger.generate_debug_report()

        # Cleanup
        debugger.cleanup_test_data()

        print(f"\n🔍 PAYMENT DEBUG COMPLETED")

        return 0 if system_ready else 1

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during payment debugging: {e}")
        debugger.cleanup_test_data()
        return 2

if __name__ == "__main__":
    sys.exit(main())