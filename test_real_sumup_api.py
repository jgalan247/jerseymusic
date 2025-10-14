#!/usr/bin/env python
"""
Real SumUp API Test Script

This script tests the ACTUAL SumUp API with real credentials.
NO SIMULATION - This makes real API calls to SumUp.

Usage:
    python test_real_sumup_api.py
"""

import os
import sys
import django
import requests
import json
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from payments import sumup as sumup_api
from events.models import Event, TicketTier
from accounts.models import ArtistProfile, CustomerProfile
from orders.models import Order

User = get_user_model()


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.END}\n")


def print_step(number, text):
    """Print step number and description."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}Step {number}: {text}{Colors.END}")
    print(f"{Colors.CYAN}{'-' * 80}{Colors.END}")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_data(label, value):
    """Print labeled data."""
    print(f"{Colors.BOLD}{label}:{Colors.END} {value}")


class RealSumUpTester:
    """Tests real SumUp API functionality."""

    def __init__(self):
        self.results = []
        self.test_data = {}

    def check_credentials(self):
        """Verify SumUp credentials are configured."""
        print_step(1, "Checking SumUp Credentials")

        required_settings = {
            'SUMUP_CLIENT_ID': settings.SUMUP_CLIENT_ID,
            'SUMUP_CLIENT_SECRET': settings.SUMUP_CLIENT_SECRET,
            'SUMUP_MERCHANT_CODE': settings.SUMUP_MERCHANT_CODE,
            'SUMUP_API_BASE_URL': getattr(settings, 'SUMUP_API_BASE_URL', None),
        }

        all_present = True
        for key, value in required_settings.items():
            if value and value not in ['your_', 'change-this']:
                print_success(f"{key}: {value[:20]}..." if len(str(value)) > 20 else f"{key}: {value}")
            else:
                print_error(f"{key}: NOT CONFIGURED")
                all_present = False

        if all_present:
            print_success("All credentials are configured")
            return True
        else:
            print_error("Some credentials are missing")
            return False

    def test_platform_token(self):
        """Test retrieving platform access token."""
        print_step(2, "Testing Platform Access Token Retrieval")

        try:
            print_info("Requesting access token from SumUp API...")
            print_info(f"Client ID: {settings.SUMUP_CLIENT_ID[:20]}...")

            # Call the real API
            token = sumup_api.get_platform_access_token()

            if token:
                print_success("Platform access token retrieved successfully")
                print_data("Token (first 20 chars)", token[:20] + "...")
                print_data("Token length", len(token))
                self.test_data['platform_token'] = token
                return True
            else:
                print_error("Failed to retrieve access token")
                return False

        except Exception as e:
            print_error(f"Token retrieval failed: {e}")
            print_info(f"Error type: {type(e).__name__}")
            import traceback
            print(traceback.format_exc())
            return False

    def test_create_checkout(self):
        """Test creating a real checkout with SumUp."""
        print_step(3, "Creating Real SumUp Checkout")

        try:
            # Prepare checkout data
            amount = Decimal('5.00')  # Small test amount
            currency = 'GBP'
            reference = f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
            description = 'Jersey Events Test Checkout'
            return_url = settings.SUMUP_RETURN_URL or 'http://localhost:8000/payments/sumup/success/'

            print_info("Creating checkout with real SumUp API...")
            print_data("Amount", f"£{amount}")
            print_data("Currency", currency)
            print_data("Reference", reference)
            print_data("Description", description)
            print_data("Return URL", return_url)

            # Create checkout using real API
            checkout_data = sumup_api.create_checkout_simple(
                amount=float(amount),
                currency=currency,
                reference=reference,
                description=description,
                return_url=return_url,
                expected_amount=float(amount)
            )

            if checkout_data and 'id' in checkout_data:
                print_success("Checkout created successfully!")
                print_data("Checkout ID", checkout_data.get('id'))
                print_data("Status", checkout_data.get('status', 'unknown'))

                if 'checkout_url' in checkout_data:
                    print_data("Payment URL", checkout_data['checkout_url'])
                    print()
                    print(f"{Colors.BOLD}{Colors.GREEN}To complete payment, visit:{Colors.END}")
                    print(f"{Colors.CYAN}{checkout_data['checkout_url']}{Colors.END}")
                    print()

                if 'date' in checkout_data:
                    print_data("Created at", checkout_data['date'])

                # Store for later testing
                self.test_data['checkout_id'] = checkout_data.get('id')
                self.test_data['checkout_data'] = checkout_data

                return True
            else:
                print_error("Checkout creation returned no data")
                print_data("Response", checkout_data)
                return False

        except Exception as e:
            print_error(f"Checkout creation failed: {e}")
            print_info(f"Error type: {type(e).__name__}")
            import traceback
            print(traceback.format_exc())
            return False

    def test_get_checkout_status(self):
        """Test retrieving checkout status."""
        print_step(4, "Retrieving Checkout Status")

        if 'checkout_id' not in self.test_data:
            print_warning("No checkout ID available, skipping status check")
            return False

        checkout_id = self.test_data['checkout_id']

        try:
            print_info(f"Retrieving status for checkout: {checkout_id}")

            # Get checkout status using real API
            url = f"{settings.SUMUP_API_BASE_URL}/checkouts/{checkout_id}"
            token = self.test_data.get('platform_token')

            if not token:
                token = sumup_api.get_platform_access_token()

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                status_data = response.json()
                print_success("Checkout status retrieved successfully")
                print_data("Status", status_data.get('status', 'unknown'))
                print_data("Amount", f"£{status_data.get('amount', 0)}")
                print_data("Currency", status_data.get('currency', 'N/A'))
                print_data("Reference", status_data.get('merchant_code', 'N/A'))

                if status_data.get('transactions'):
                    print_info("Transactions:")
                    for tx in status_data['transactions']:
                        print(f"  - Type: {tx.get('type')}, Status: {tx.get('status')}")

                return True
            else:
                print_warning(f"Status check returned {response.status_code}")
                print_data("Response", response.text[:200])
                return False

        except Exception as e:
            print_error(f"Status retrieval failed: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def test_merchant_info(self):
        """Test retrieving merchant information."""
        print_step(5, "Retrieving Merchant Information")

        try:
            print_info("Fetching merchant information from SumUp...")

            # Get merchant info using real API
            merchant_info = sumup_api.get_merchant_info()

            if merchant_info:
                print_success("Merchant information retrieved successfully")

                if isinstance(merchant_info, dict):
                    print_data("Merchant Code", merchant_info.get('merchant_code', 'N/A'))
                    print_data("Country", merchant_info.get('country_code', 'N/A'))
                    print_data("Currency", merchant_info.get('default_currency', 'N/A'))

                    if 'merchant_profile' in merchant_info:
                        profile = merchant_info['merchant_profile']
                        if 'business_name' in profile:
                            print_data("Business Name", profile['business_name'])
                else:
                    print_data("Merchant Info", merchant_info)

                return True
            else:
                print_warning("No merchant information returned")
                return False

        except Exception as e:
            print_error(f"Merchant info retrieval failed: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def test_with_database_order(self):
        """Test creating checkout for a real database order."""
        print_step(6, "Testing with Database Order")

        try:
            print_info("Creating test order in database...")

            # Get or create test customer
            customer, created = User.objects.get_or_create(
                email='test.customer@jerseyevents.je',
                defaults={
                    'user_type': 'customer',
                    'first_name': 'Test',
                    'last_name': 'Customer',
                }
            )
            if created:
                customer.set_password('testpassword123')
                customer.save()
                print_success("Test customer created")
            else:
                print_info("Using existing test customer")

            # Get or create test artist
            artist, created = User.objects.get_or_create(
                email='test.artist@jerseyevents.je',
                defaults={
                    'user_type': 'artist',
                    'first_name': 'Test',
                    'last_name': 'Artist',
                }
            )
            if created:
                artist.set_password('testpassword123')
                artist.save()
                print_success("Test artist created")
            else:
                print_info("Using existing test artist")

            # Get or create artist profile
            artist_profile, created = ArtistProfile.objects.get_or_create(
                user=artist,
                defaults={
                    'business_name': 'Test Events Company',
                    'display_name': 'Test Artist',
                }
            )
            if created:
                print_success("Test artist profile created")

            # Create test event
            event = Event.objects.create(
                title=f'Test Event - {datetime.now().strftime("%Y%m%d %H:%M")}',
                description='This is a test event for SumUp payment testing',
                artist=artist,
                event_date=timezone.now().date() + timedelta(days=30),
                event_time=datetime.strptime('19:00', '%H:%M').time(),
                venue_name='Test Venue',
                venue_address='123 Test Street',
                venue_town_city='St Helier',
                venue_postcode='JE2 3XX',
                capacity=100,
                status='published',
            )
            print_success(f"Test event created: {event.title}")
            print_data("Event ID", event.id)

            # Create ticket tier
            ticket_tier = TicketTier.objects.create(
                event=event,
                name='Standard',
                price=Decimal('25.00'),
                quantity_available=50,
            )
            print_success(f"Ticket tier created: {ticket_tier.name} - £{ticket_tier.price}")

            # Create test order
            order = Order.objects.create(
                customer=customer,
                event=event,
                order_number=f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                status='pending_payment',
                subtotal=Decimal('50.00'),
                platform_fee=Decimal('0.90'),
                total_amount=Decimal('50.90'),
            )
            print_success(f"Test order created: {order.order_number}")
            print_data("Order ID", order.id)
            print_data("Total Amount", f"£{order.total_amount}")

            # Now create checkout for this order
            print_info("\nCreating SumUp checkout for order...")

            checkout_data = sumup_api.create_checkout_simple(
                amount=float(order.total_amount),
                currency='GBP',
                reference=order.order_number,
                description=f'Tickets for {event.title}',
                return_url=f"{settings.SUMUP_RETURN_URL}?order_id={order.id}",
                expected_amount=float(order.total_amount)
            )

            if checkout_data and 'id' in checkout_data:
                print_success("Checkout created for order!")
                print_data("Checkout ID", checkout_data['id'])

                # Update order with checkout ID
                order.sumup_checkout_id = checkout_data['id']
                order.save()
                print_success("Order updated with checkout ID")

                if 'checkout_url' in checkout_data:
                    print()
                    print(f"{Colors.BOLD}{Colors.GREEN}Payment URL for this order:{Colors.END}")
                    print(f"{Colors.CYAN}{checkout_data['checkout_url']}{Colors.END}")
                    print()
                    print_info("To complete the payment:")
                    print(f"  1. Visit the URL above")
                    print(f"  2. Use test card: 4242 4242 4242 4242")
                    print(f"  3. CVV: 123, Expiry: 12/25")
                    print()

                self.test_data['test_order'] = order
                self.test_data['test_event'] = event

                return True
            else:
                print_error("Failed to create checkout for order")
                return False

        except Exception as e:
            print_error(f"Database order test failed: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def print_summary(self):
        """Print test summary."""
        print_header("Test Summary")

        if self.test_data:
            print(f"{Colors.BOLD}Test Data Created:{Colors.END}\n")

            if 'platform_token' in self.test_data:
                print_success(f"Platform Token: {self.test_data['platform_token'][:20]}...")

            if 'checkout_id' in self.test_data:
                print_success(f"Checkout ID: {self.test_data['checkout_id']}")

            if 'checkout_data' in self.test_data:
                checkout = self.test_data['checkout_data']
                if 'checkout_url' in checkout:
                    print()
                    print(f"{Colors.BOLD}Payment URL:{Colors.END}")
                    print(f"{Colors.CYAN}{checkout['checkout_url']}{Colors.END}")
                    print()

            if 'test_order' in self.test_data:
                order = self.test_data['test_order']
                print_success(f"Test Order: {order.order_number}")
                print_data("  Order ID", order.id)
                print_data("  Amount", f"£{order.total_amount}")

            if 'test_event' in self.test_data:
                event = self.test_data['test_event']
                print_success(f"Test Event: {event.title}")
                print_data("  Event ID", event.id)

        print()
        print(f"{Colors.BOLD}Next Steps:{Colors.END}")
        print("1. Visit the payment URL above in your browser")
        print("2. Complete payment using test card: 4242 4242 4242 4242")
        print("3. After payment, check order status in admin or run polling:")
        print(f"   {Colors.CYAN}python manage.py run_payment_polling --verbose{Colors.END}")
        print()

    def cleanup(self):
        """Offer to cleanup test data."""
        print_header("Cleanup")

        if not self.test_data:
            print_info("No test data to cleanup")
            return

        print("Test data was created. Would you like to clean it up?")
        print("(Order, Event, and User records)")

        response = input(f"\n{Colors.YELLOW}Cleanup test data? (y/n): {Colors.END}").strip().lower()

        if response == 'y':
            try:
                if 'test_order' in self.test_data:
                    order = self.test_data['test_order']
                    order.delete()
                    print_success("Test order deleted")

                if 'test_event' in self.test_data:
                    event = self.test_data['test_event']
                    event.delete()
                    print_success("Test event deleted")

                # Optionally delete test users
                response = input(f"\n{Colors.YELLOW}Also delete test users? (y/n): {Colors.END}").strip().lower()
                if response == 'y':
                    User.objects.filter(email__in=[
                        'test.customer@jerseyevents.je',
                        'test.artist@jerseyevents.je'
                    ]).delete()
                    print_success("Test users deleted")

                print_success("Cleanup completed")

            except Exception as e:
                print_error(f"Cleanup failed: {e}")
        else:
            print_info("Skipping cleanup - test data retained")

    def run(self):
        """Run all tests."""
        print_header("Real SumUp API Test Suite")
        print(f"{Colors.BOLD}This will test the ACTUAL SumUp API with real credentials{Colors.END}")
        print(f"{Colors.YELLOW}NO SIMULATION - Real API calls will be made{Colors.END}")
        print()

        input(f"{Colors.CYAN}Press Enter to start testing...{Colors.END}")

        # Run tests
        tests = [
            ("Credentials Check", self.check_credentials),
            ("Platform Token", self.test_platform_token),
            ("Create Checkout", self.test_create_checkout),
            ("Checkout Status", self.test_get_checkout_status),
            ("Merchant Info", self.test_merchant_info),
            ("Database Order", self.test_with_database_order),
        ]

        results = []
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, result))
            except Exception as e:
                print_error(f"Test '{name}' crashed: {e}")
                results.append((name, False))

        # Print summary
        self.print_summary()

        # Show results
        print_header("Test Results")
        for name, result in results:
            if result:
                print_success(f"{name}: PASSED")
            else:
                print_error(f"{name}: FAILED")

        passed = sum(1 for _, result in results if result)
        total = len(results)
        print()
        print(f"{Colors.BOLD}Summary: {passed}/{total} tests passed{Colors.END}")

        # Cleanup
        self.cleanup()


def main():
    """Main entry point."""
    tester = RealSumUpTester()
    tester.run()


if __name__ == '__main__':
    main()
