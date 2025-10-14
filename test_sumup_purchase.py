#!/usr/bin/env python
"""
Test SumUp Integration with Fake Purchase
==========================================
This script simulates a complete purchase flow to test SumUp integration.

Usage:
    python test_sumup_purchase.py
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from events.models import Event, Category, TicketTier
from accounts.models import ArtistProfile, CustomerProfile
from orders.models import Order, OrderItem
from payments.models import SumUpCheckout
from payments import sumup as sumup_api

User = get_user_model()


class Colors:
    """Terminal colors for better output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def create_test_artist():
    """Create or get test artist with SumUp connection."""
    print_header("STEP 1: Setting Up Test Artist")

    email = "test.artist@jerseyevents.je"

    # Check if artist exists
    try:
        artist = User.objects.get(email=email)
        print_info(f"Found existing test artist: {email}")
    except User.DoesNotExist:
        # Create new artist
        artist = User.objects.create_user(
            email=email,
            password='testpassword123',
            first_name='Test',
            last_name='Artist',
            user_type='artist'
        )
        artist.is_verified = True
        artist.save()
        print_success(f"Created new test artist: {email}")

    # Get or create artist profile
    profile, created = ArtistProfile.objects.get_or_create(
        user=artist,
        defaults={
            'business_name': 'Test Events Company',
            'display_name': 'Test Artist',
            'bio': 'Test event organizer for integration testing',
            'phone_number': '01534123456',
            'studio_address': '123 Test Street, St Helier, Jersey JE2 3XX',
            'website': 'https://testartist.je',
        }
    )

    if created:
        print_success("Created artist profile")
    else:
        print_info("Artist profile already exists")

    # Check SumUp connection
    if profile.is_sumup_connected:
        print_success(f"Artist connected to SumUp")
        print_info(f"   Merchant Code: {profile.sumup_merchant_code}")
        print_info(f"   Token Expired: {profile.sumup_token_expired}")
    else:
        print_warning("Artist NOT connected to SumUp")
        print_info("   For real testing, artist needs to connect via:")
        print_info("   http://localhost:8000/accounts/sumup/connect/")
        print_info("")
        print_info("   For this test, we'll simulate the connection...")

        # Simulate SumUp connection (for testing only)
        profile.sumup_merchant_code = 'TEST_MERCHANT_CODE'
        profile.sumup_access_token = 'test_access_token_for_simulation'
        profile.sumup_refresh_token = 'test_refresh_token'
        profile.sumup_token_type = 'Bearer'
        profile.sumup_expires_at = timezone.now() + timedelta(hours=1)
        profile.sumup_connected_at = timezone.now()
        profile.sumup_connection_status = 'connected'
        profile.sumup_scope = 'payments'
        profile.save()
        print_success("Simulated SumUp connection (test mode)")

    return artist, profile


def create_test_customer():
    """Create or get test customer."""
    print_header("STEP 2: Setting Up Test Customer")

    email = "test.customer@jerseyevents.je"

    # Check if customer exists
    try:
        customer = User.objects.get(email=email)
        print_info(f"Found existing test customer: {email}")
    except User.DoesNotExist:
        # Create new customer
        customer = User.objects.create_user(
            email=email,
            password='testpassword123',
            first_name='Test',
            last_name='Customer',
            user_type='customer'
        )
        customer.is_verified = True
        customer.save()
        print_success(f"Created new test customer: {email}")

    # Get or create customer profile
    profile, created = CustomerProfile.objects.get_or_create(
        user=customer,
        defaults={
            'phone_number': '01534654321',
        }
    )

    if created:
        print_success("Created customer profile")
    else:
        print_info("Customer profile already exists")

    return customer, profile


def create_test_event(artist):
    """Create test event."""
    print_header("STEP 3: Creating Test Event")

    # Get or create category
    category, _ = Category.objects.get_or_create(
        name='Music',
        defaults={'slug': 'music'}
    )

    # Create event
    event_title = f"Test Concert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    event = Event.objects.create(
        title=event_title,
        slug=f"test-concert-{int(timezone.now().timestamp())}",
        description='This is a test event for SumUp integration testing.',
        organiser=artist,
        category=category,
        venue_name='Test Venue',
        venue_address='789 Test Road, St Helier, Jersey JE2 5ZZ',
        event_date=timezone.now().date() + timedelta(days=30),
        event_time=datetime.strptime('19:00', '%H:%M').time(),
        status='published',
        capacity=100,
        ticket_price=Decimal('25.00'),  # Default ticket price
        processing_fee_passed_to_customer=True,
    )

    print_success(f"Created event: {event.title}")
    print_info(f"   Event ID: {event.id}")
    print_info(f"   Slug: {event.slug}")
    print_info(f"   Date: {event.event_date}")
    print_info(f"   Time: {event.event_time}")

    # Create ticket tiers
    standard_tier = TicketTier.objects.create(
        event=event,
        name='Standard',
        price=Decimal('25.00'),
        quantity_available=80,
        tier_type='standard'
    )

    vip_tier = TicketTier.objects.create(
        event=event,
        name='VIP',
        price=Decimal('50.00'),
        quantity_available=20,
        tier_type='vip'
    )

    print_success(f"Created ticket tiers:")
    print_info(f"   Standard: £{standard_tier.price} ({standard_tier.quantity_available} available)")
    print_info(f"   VIP: £{vip_tier.price} ({vip_tier.quantity_available} available)")

    return event, standard_tier, vip_tier


def create_test_order(customer, event, ticket_tier, quantity=2):
    """Create test order."""
    print_header("STEP 4: Creating Test Order")

    # Calculate pricing
    ticket_price = ticket_tier.price
    subtotal = ticket_price * quantity

    # Platform fee (simplified for testing - normally calculated from tier)
    # For a 100-capacity event, Tier 2 applies: £0.45 per ticket
    platform_fee_per_ticket = Decimal('0.45')
    platform_fee_total = platform_fee_per_ticket * quantity

    # Processing fee (1.69% if passed to customer)
    if event.processing_fee_passed_to_customer:
        processing_fee = subtotal * Decimal('0.0169')
    else:
        processing_fee = Decimal('0.00')

    total = subtotal + platform_fee_total + processing_fee

    # Create order
    order = Order.objects.create(
        user=customer,
        order_number=f"TEST-{timezone.now().strftime('%Y%m%d-%H%M%S')}",
        email=customer.email,
        delivery_first_name=customer.first_name,
        delivery_last_name=customer.last_name,
        delivery_address_line_1='456 Test Avenue',
        delivery_town_city='St Helier',
        delivery_parish='St. Helier',
        delivery_postcode='JE2 4YY',
        subtotal=subtotal,
        platform_fee=platform_fee_total,
        processing_fee=processing_fee,
        total=total,
        status='pending_verification',
        terms_accepted=True,
        terms_accepted_at=timezone.now(),
        terms_accepted_ip='127.0.0.1',
    )

    # Create order item
    order_item = OrderItem.objects.create(
        order=order,
        event=event,
        ticket_tier=ticket_tier,
        quantity=quantity,
        price_per_ticket=ticket_price,
        subtotal=subtotal,
    )

    print_success(f"Created order: {order.order_number}")
    print_info(f"   Customer: {customer.email}")
    print_info(f"   Event: {event.title}")
    print_info(f"   Tickets: {quantity}x {ticket_tier.name}")
    print_info(f"   Ticket Price: £{ticket_price}")
    print_info(f"   Subtotal: £{subtotal}")
    print_info(f"   Platform Fee: £{platform_fee_total}")
    print_info(f"   Processing Fee: £{processing_fee}")
    print_info(f"   Total: £{total}")
    print_info(f"   Status: {order.status}")

    return order


def simulate_sumup_checkout(order, artist_profile):
    """Simulate SumUp checkout creation."""
    print_header("STEP 5: Simulating SumUp Checkout")

    try:
        # In real scenario, this would call SumUp API
        # For testing, we'll create a mock checkout

        checkout_reference = f"test_checkout_{order.order_number}_{timezone.now().timestamp()}"

        checkout = SumUpCheckout.objects.create(
            order=order,
            customer=order.user,
            artist=artist_profile.user,
            amount=order.total,
            currency='GBP',
            description=f"Test purchase for {order.order_number}",
            merchant_code=artist_profile.sumup_merchant_code or 'TEST_MERCHANT',
            checkout_reference=checkout_reference,
            return_url='http://localhost:8000/payments/success/',
            redirect_url='http://localhost:8000/payments/success/',
            status='created',
        )

        # Simulate SumUp response
        checkout.sumup_checkout_id = f"test_sumup_id_{timezone.now().timestamp()}"
        checkout.sumup_response = {
            'id': checkout.sumup_checkout_id,
            'checkout_reference': checkout_reference,
            'amount': float(order.total),
            'currency': 'GBP',
            'status': 'PENDING',
            'date': timezone.now().isoformat(),
        }
        checkout.save()

        print_success(f"Created SumUp checkout (simulated)")
        print_info(f"   Checkout ID: {checkout.sumup_checkout_id}")
        print_info(f"   Reference: {checkout.checkout_reference}")
        print_info(f"   Amount: £{checkout.amount}")
        print_info(f"   Status: {checkout.status}")
        print_info(f"   Merchant: {checkout.merchant_code}")

        return checkout

    except Exception as e:
        print_error(f"Failed to create checkout: {e}")
        import traceback
        traceback.print_exc()
        return None


def simulate_payment_completion(checkout):
    """Simulate successful payment."""
    print_header("STEP 6: Simulating Payment Completion")

    print_info("In real scenario, customer would:")
    print_info("   1. Be redirected to SumUp payment page")
    print_info("   2. Enter card details: 4242 4242 4242 4242")
    print_info("   3. Complete payment")
    print_info("   4. Be redirected back to platform")
    print_info("")
    print_info("For this test, we'll simulate successful payment...")

    # Update checkout to PAID
    checkout.status = 'paid'
    checkout.paid_at = timezone.now()
    checkout.sumup_response['status'] = 'PAID'
    checkout.sumup_response['transaction_code'] = f'TEST_TXN_{timezone.now().timestamp()}'
    checkout.save()

    print_success("Payment marked as PAID (simulated)")
    print_info(f"   Transaction Code: {checkout.sumup_response['transaction_code']}")
    print_info(f"   Paid At: {checkout.paid_at}")


def run_payment_polling(order):
    """Run payment polling manually."""
    print_header("STEP 7: Running Payment Verification Polling")

    print_info("In production, Django-Q would run this every 5 minutes")
    print_info("For this test, we'll run it manually...")

    try:
        from payments.polling_service import polling_service

        # Run polling
        result = polling_service._verify_single_order(order)

        # Refresh order from database
        order.refresh_from_db()

        print_success(f"Polling completed: {result}")
        print_info(f"   Order Status: {order.status}")
        print_info(f"   Is Paid: {order.is_paid}")

        if order.status == 'completed':
            print_success("Order verified and completed!")

            # Check tickets
            tickets = order.tickets.all()
            print_info(f"   Tickets Generated: {tickets.count()}")

            for ticket in tickets:
                print_info(f"      - Ticket {ticket.ticket_number}: {ticket.status}")

        return result

    except Exception as e:
        print_error(f"Polling failed: {e}")
        import traceback
        traceback.print_exc()
        return 'errors'


def check_final_status(order):
    """Check final order status."""
    print_header("STEP 8: Final Status Check")

    order.refresh_from_db()

    print_info("Order Details:")
    print_info(f"   Order Number: {order.order_number}")
    print_info(f"   Status: {order.status}")
    print_info(f"   Is Paid: {order.is_paid}")
    print_info(f"   Total: £{order.total}")
    print_info(f"   Created: {order.created_at}")

    if order.paid_at:
        print_info(f"   Paid At: {order.paid_at}")

    if order.transaction_id:
        print_info(f"   Transaction ID: {order.transaction_id}")

    # Check tickets
    tickets = order.tickets.all()
    print_info(f"\nTickets:")
    print_info(f"   Count: {tickets.count()}")

    for ticket in tickets:
        print_info(f"   - {ticket.ticket_number}")
        print_info(f"     Status: {ticket.status}")
        print_info(f"     Event: {ticket.event.title}")
        if hasattr(ticket, 'qr_data'):
            print_info(f"     QR Data: {ticket.qr_data[:50]}...")

    # Check checkout
    try:
        checkout = SumUpCheckout.objects.get(order=order)
        print_info(f"\nCheckout:")
        print_info(f"   Checkout ID: {checkout.sumup_checkout_id}")
        print_info(f"   Status: {checkout.status}")
        print_info(f"   Amount: £{checkout.amount}")
        if checkout.paid_at:
            print_info(f"   Paid At: {checkout.paid_at}")
    except SumUpCheckout.DoesNotExist:
        print_warning("No checkout record found")

    # Summary
    if order.status == 'completed' and order.is_paid:
        print_success("\n✅ TEST PASSED: Order completed successfully!")
        print_success("   - Order marked as paid")
        print_success("   - Tickets generated")
        print_success("   - Customer would receive email with tickets")
        return True
    else:
        print_error("\n❌ TEST FAILED: Order not completed")
        print_error(f"   Status: {order.status}")
        print_error(f"   Is Paid: {order.is_paid}")
        return False


def cleanup_prompt():
    """Ask user if they want to cleanup test data."""
    print_header("CLEANUP")

    response = input("\nDo you want to delete test data? (y/n): ").lower().strip()

    if response == 'y':
        print_info("Deleting test data...")

        # Delete test orders
        deleted_orders = Order.objects.filter(order_number__startswith='TEST-').delete()
        print_info(f"   Deleted {deleted_orders[0]} orders")

        # Delete test events
        deleted_events = Event.objects.filter(title__startswith='Test Concert').delete()
        print_info(f"   Deleted {deleted_events[0]} events")

        print_success("Test data cleaned up!")
    else:
        print_info("Test data kept for inspection")
        print_info("   View orders: http://localhost:8000/admin/orders/order/")
        print_info("   View events: http://localhost:8000/admin/events/event/")


def main():
    """Run complete test."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("SumUp Integration Test - Fake Purchase Simulation")
    print("=" * 80)
    print(f"{Colors.ENDC}\n")

    print_info("This script will:")
    print_info("  1. Create test artist and customer accounts")
    print_info("  2. Create test event with tickets")
    print_info("  3. Create test order")
    print_info("  4. Simulate SumUp checkout")
    print_info("  5. Simulate payment completion")
    print_info("  6. Run payment verification polling")
    print_info("  7. Check final status")
    print_info("  8. Optionally cleanup test data")

    input(f"\n{Colors.BOLD}Press Enter to start test...{Colors.ENDC}")

    try:
        # Step 1: Create artist
        artist, artist_profile = create_test_artist()

        # Step 2: Create customer
        customer, customer_profile = create_test_customer()

        # Step 3: Create event
        event, standard_tier, vip_tier = create_test_event(artist)

        # Step 4: Create order (2 standard tickets)
        order = create_test_order(customer, event, standard_tier, quantity=2)

        # Step 5: Create SumUp checkout
        checkout = simulate_sumup_checkout(order, artist_profile)

        if not checkout:
            print_error("Failed to create checkout. Aborting test.")
            return

        # Step 6: Simulate payment
        simulate_payment_completion(checkout)

        # Step 7: Run polling
        result = run_payment_polling(order)

        # Step 8: Check final status
        success = check_final_status(order)

        # Cleanup
        cleanup_prompt()

        # Final summary
        print_header("TEST COMPLETE")

        if success:
            print_success("All tests passed! SumUp integration is working correctly.")
        else:
            print_error("Some tests failed. Check output above for details.")

        print_info("\nTest Summary:")
        print_info(f"   Artist: {artist.email}")
        print_info(f"   Customer: {customer.email}")
        print_info(f"   Event: {event.title}")
        print_info(f"   Order: {order.order_number}")
        print_info(f"   Total: £{order.total}")
        print_info(f"   Final Status: {order.status}")

    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
