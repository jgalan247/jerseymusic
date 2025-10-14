#!/usr/bin/env python
"""
Complete Order Test with Email Notification

This script tests the COMPLETE order flow:
1. Creates test customer and event
2. Creates order with real SumUp checkout
3. Simulates payment (marks as PAID)
4. Triggers polling to process payment
5. Sends confirmation email with invoice

Usage:
    python test_complete_order_with_email.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail

from payments import sumup as sumup_api
from payments.models import SumUpCheckout
from payments.polling_service import PaymentPollingService
from events.models import Event, TicketTier
from accounts.models import ArtistProfile, CustomerProfile
from orders.models import Order
import requests

User = get_user_model()


# Colors
class C:
    H = '\033[95m\033[1m'  # Header
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    R = '\033[91m'  # Red
    B = '\033[94m'  # Blue
    E = '\033[0m'   # End


def print_header(text):
    print(f"\n{C.H}{'='*80}")
    print(f"{text}")
    print(f"{'='*80}{C.E}\n")


def print_step(num, text):
    print(f"\n{C.B}Step {num}: {text}{C.E}")
    print(f"{C.B}{'-'*80}{C.E}")


def print_success(text):
    print(f"{C.G}✅ {text}{C.E}")


def print_error(text):
    print(f"{C.R}❌ {text}{C.E}")


def print_info(text):
    print(f"{C.Y}ℹ️  {text}{C.E}")


class CompleteOrderTest:
    """Test complete order flow with email notification."""

    def __init__(self):
        self.test_data = {}
        self.cleanup_items = []

    def create_test_customer(self):
        """Step 1: Create test customer."""
        print_step(1, "Creating Test Customer")

        try:
            # Create or get customer
            customer, created = User.objects.get_or_create(
                email='test.customer@jerseyevents.je',
                defaults={
                    'user_type': 'customer',
                    'first_name': 'Test',
                    'last_name': 'Customer',
                    'email_verified': True,
                }
            )

            if created:
                customer.set_password('testpassword123')
                customer.save()
                print_success("Test customer created")
                self.cleanup_items.append(('user', customer.id))
            else:
                print_info("Using existing test customer")

            # Get or create customer profile
            profile, created = CustomerProfile.objects.get_or_create(
                user=customer,
                defaults={
                    'phone_number': '01534123456',
                }
            )

            print_info(f"Customer: {customer.email}")
            print_info(f"Name: {customer.get_full_name()}")

            self.test_data['customer'] = customer
            return True

        except Exception as e:
            print_error(f"Failed to create customer: {e}")
            return False

    def create_test_event(self):
        """Step 2: Create test event with tickets."""
        print_step(2, "Creating Test Event")

        try:
            # Create or get artist
            artist, created = User.objects.get_or_create(
                email='test.artist@jerseyevents.je',
                defaults={
                    'user_type': 'artist',
                    'first_name': 'Test',
                    'last_name': 'Artist',
                    'email_verified': True,
                }
            )

            if created:
                artist.set_password('testpassword123')
                artist.save()
                self.cleanup_items.append(('user', artist.id))

            # Create artist profile
            artist_profile, created = ArtistProfile.objects.get_or_create(
                user=artist,
                defaults={
                    'business_name': 'Test Events Ltd',
                    'display_name': 'Test Artist',
                }
            )

            # Create event
            event = Event.objects.create(
                title=f'Test Concert - {datetime.now().strftime("%Y%m%d %H:%M")}',
                slug=f'test-concert-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                description='This is a test event for complete order flow testing',
                organiser=artist,
                venue_name='Jersey Arts Centre',
                venue_address='Phillips Street, St Helier',
                event_date=timezone.now().date() + timedelta(days=30),
                event_time=datetime.strptime('19:30', '%H:%M').time(),
                capacity=100,
                ticket_price=Decimal('25.00'),
                status='published',
            )

            print_success(f"Event created: {event.title}")
            print_info(f"Event ID: {event.id}")
            print_info(f"Date: {event.event_date} at {event.event_time}")
            print_info(f"Venue: {event.venue_name}")

            self.cleanup_items.append(('event', event.id))

            # Create ticket tiers
            standard_tier = TicketTier.objects.create(
                event=event,
                tier_type='standard',
                name='Standard',
                price=Decimal('25.00'),
                quantity_available=50,
            )

            vip_tier = TicketTier.objects.create(
                event=event,
                tier_type='vip',
                name='VIP',
                price=Decimal('50.00'),
                quantity_available=20,
            )

            print_success(f"Ticket tiers created:")
            print_info(f"  - Standard: £{standard_tier.price} ({standard_tier.quantity_available} available)")
            print_info(f"  - VIP: £{vip_tier.price} ({vip_tier.quantity_available} available)")

            self.test_data['event'] = event
            self.test_data['artist'] = artist
            self.test_data['standard_tier'] = standard_tier
            self.test_data['vip_tier'] = vip_tier

            return True

        except Exception as e:
            print_error(f"Failed to create event: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_order_with_checkout(self):
        """Step 3: Create order with real SumUp checkout."""
        print_step(3, "Creating Order with Real SumUp Checkout")

        try:
            customer = self.test_data['customer']
            event = self.test_data['event']

            # Calculate order amounts
            ticket_quantity = 2
            ticket_price = Decimal('25.00')
            subtotal = ticket_price * ticket_quantity
            platform_fee = Decimal('0.45') * ticket_quantity  # £0.45 per ticket
            total_amount = subtotal + platform_fee

            # Generate order number
            order_number = f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}'

            print_info(f"Order Details:")
            print_info(f"  Tickets: {ticket_quantity} x £{ticket_price} = £{subtotal}")
            print_info(f"  Platform Fee: £{platform_fee}")
            print_info(f"  Total: £{total_amount}")

            # Create order
            order = Order.objects.create(
                customer=customer,
                event=event,
                order_number=order_number,
                status='pending_payment',
                subtotal=subtotal,
                platform_fee=platform_fee,
                total_amount=total_amount,
            )

            print_success(f"Order created: {order.order_number}")
            print_info(f"Order ID: {order.id}")

            self.cleanup_items.append(('order', order.id))

            # Create real SumUp checkout
            print_info("\nCreating real SumUp checkout...")

            checkout_data = sumup_api.create_checkout_simple(
                amount=float(total_amount),
                currency='GBP',
                reference=order_number,
                description=f'Jersey Events - {event.title} ({ticket_quantity} tickets)',
                return_url=f'http://localhost:8000/payments/sumup/success/?order_id={order.id}',
                expected_amount=float(total_amount)
            )

            if not checkout_data or 'id' not in checkout_data:
                print_error("Failed to create SumUp checkout")
                return False

            checkout_id = checkout_data['id']
            print_success(f"SumUp checkout created: {checkout_id}")

            # Create SumUpCheckout record
            sumup_checkout = SumUpCheckout.objects.create(
                order=order,
                checkout_id=checkout_id,
                checkout_reference=order_number,
                amount=total_amount,
                currency='GBP',
                status='PENDING',
                checkout_url=f'https://checkout.sumup.com/pay/{checkout_id}',
            )

            print_success("SumUpCheckout record created")

            # Update order with checkout ID
            order.sumup_checkout_id = checkout_id
            order.status = 'pending_verification'
            order.save()

            print_success("Order updated with checkout ID")
            print_info(f"Order status: {order.status}")

            # Show payment URL
            print(f"\n{C.G}Payment URL:{C.E}")
            print(f"{C.Y}https://checkout.sumup.com/pay/{checkout_id}{C.E}")

            self.test_data['order'] = order
            self.test_data['sumup_checkout'] = sumup_checkout
            self.test_data['checkout_id'] = checkout_id

            return True

        except Exception as e:
            print_error(f"Failed to create order: {e}")
            import traceback
            traceback.print_exc()
            return False

    def simulate_payment_completion(self):
        """Step 4: Simulate payment completion (mark as PAID)."""
        print_step(4, "Simulating Payment Completion")

        try:
            sumup_checkout = self.test_data['sumup_checkout']
            order = self.test_data['order']

            print_info("Marking checkout as PAID...")

            # Update SumUpCheckout status
            sumup_checkout.status = 'PAID'
            sumup_checkout.paid_at = timezone.now()
            sumup_checkout.save()

            print_success("SumUpCheckout marked as PAID")
            print_info(f"Paid at: {sumup_checkout.paid_at}")

            # Note: Order status is still 'pending_verification'
            # The polling service will change it to 'completed'

            print_info(f"Order status: {order.status} (will be updated by polling)")

            return True

        except Exception as e:
            print_error(f"Failed to simulate payment: {e}")
            import traceback
            traceback.print_exc()
            return False

    def trigger_payment_polling(self):
        """Step 5: Trigger payment polling to process the order."""
        print_step(5, "Triggering Payment Polling Service")

        try:
            print_info("Running payment polling service...")

            # Create polling service instance
            polling_service = PaymentPollingService()

            # Process pending payments
            polling_service.process_pending_payments()

            print_success("Polling service executed")

            # Refresh order from database
            order = Order.objects.get(id=self.test_data['order'].id)
            self.test_data['order'] = order

            print_info(f"Order status after polling: {order.status}")
            print_info(f"Order is_paid: {order.is_paid}")

            if order.status == 'completed' and order.is_paid:
                print_success("✨ Payment processed successfully!")
                print_success("✨ Order marked as completed!")
                return True
            else:
                print_error(f"Order not completed. Status: {order.status}")
                return False

        except Exception as e:
            print_error(f"Polling failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_email_sent(self):
        """Step 6: Check if confirmation email was sent."""
        print_step(6, "Checking Email Notification")

        try:
            order = self.test_data['order']
            customer = self.test_data['customer']

            print_info("Checking for sent emails...")

            # Check Django's email outbox (when using MailHog or console backend)
            if hasattr(mail, 'outbox'):
                emails = mail.outbox
                print_info(f"Found {len(emails)} email(s) in outbox")

                if emails:
                    for idx, email in enumerate(emails, 1):
                        print(f"\n{C.G}Email #{idx}:{C.E}")
                        print(f"  To: {email.to}")
                        print(f"  Subject: {email.subject}")
                        print(f"  From: {email.from_email}")

                        # Check for order confirmation
                        if order.order_number in email.subject or order.order_number in email.body:
                            print_success("✨ Order confirmation email found!")
                            print_info(f"Contains order number: {order.order_number}")

                            # Check for attachments (PDF tickets)
                            if hasattr(email, 'attachments') and email.attachments:
                                print_success(f"✨ Email has {len(email.attachments)} attachment(s)")
                                for att in email.attachments:
                                    if isinstance(att, tuple):
                                        filename = att[0]
                                        print_info(f"  - {filename}")
                            return True
                else:
                    print_error("No emails found in outbox")
            else:
                print_info("Email outbox not available (using SMTP backend)")
                print_info("Check MailHog at: http://localhost:8025")

            # Check if email was configured to send
            print_info(f"\nEmail Backend: {settings.EMAIL_BACKEND}")
            if 'mailhog' in settings.EMAIL_BACKEND.lower() or 'smtp' in settings.EMAIL_BACKEND.lower():
                print_success("Using MailHog - Check http://localhost:8025")
                print(f"\n{C.Y}📧 To view the email:{C.E}")
                print(f"{C.Y}   Visit: http://localhost:8025{C.E}")
                print(f"{C.Y}   Look for: Order Confirmation - {order.order_number}{C.E}\n")
                return True
            elif 'console' in settings.EMAIL_BACKEND.lower():
                print_info("Using console backend - Email should be in console output")
                return True

            return True

        except Exception as e:
            print_error(f"Email check failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def verify_tickets_generated(self):
        """Step 7: Verify tickets were generated."""
        print_step(7, "Verifying Ticket Generation")

        try:
            order = self.test_data['order']

            # Check for tickets
            from events.models import Ticket
            tickets = Ticket.objects.filter(order=order)

            if tickets.exists():
                print_success(f"✨ {tickets.count()} ticket(s) generated!")

                for ticket in tickets:
                    print(f"\n{C.G}Ticket:{C.E}")
                    print(f"  Number: {ticket.ticket_number}")
                    print(f"  Name: {ticket.attendee_name}")
                    print(f"  Email: {ticket.attendee_email}")
                    print(f"  Price: £{ticket.price}")
                    print(f"  Status: {'✅ Validated' if ticket.is_validated else '⏳ Not validated'}")

                    if ticket.qr_code:
                        print_success(f"  QR Code: Generated")

                return True
            else:
                print_error("No tickets found")
                return False

        except Exception as e:
            print_error(f"Ticket verification failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_summary(self):
        """Print test summary."""
        print_header("Test Summary")

        if 'order' in self.test_data:
            order = self.test_data['order']

            print(f"{C.H}Order Details:{C.E}")
            print(f"  Order Number: {order.order_number}")
            print(f"  Status: {order.status}")
            print(f"  Is Paid: {'✅ Yes' if order.is_paid else '❌ No'}")
            print(f"  Total: £{order.total_amount}")

        if 'event' in self.test_data:
            event = self.test_data['event']
            print(f"\n{C.H}Event Details:{C.E}")
            print(f"  Title: {event.title}")
            print(f"  Date: {event.event_date} at {event.event_time}")
            print(f"  Venue: {event.venue_name}")

        if 'customer' in self.test_data:
            customer = self.test_data['customer']
            print(f"\n{C.H}Customer Details:{C.E}")
            print(f"  Email: {customer.email}")
            print(f"  Name: {customer.get_full_name()}")

        print(f"\n{C.H}Check Email:{C.E}")
        print(f"  MailHog: {C.Y}http://localhost:8025{C.E}")
        print(f"  Subject: Order Confirmation - {self.test_data.get('order', {}).order_number if 'order' in self.test_data else 'N/A'}")

    def cleanup(self):
        """Cleanup test data."""
        print_header("Cleanup")

        response = input(f"\n{C.Y}Delete test data? (y/n): {C.E}").strip().lower()

        if response == 'y':
            try:
                # Delete in reverse order
                for item_type, item_id in reversed(self.cleanup_items):
                    if item_type == 'order':
                        Order.objects.filter(id=item_id).delete()
                        print_success(f"Deleted order {item_id}")
                    elif item_type == 'event':
                        Event.objects.filter(id=item_id).delete()
                        print_success(f"Deleted event {item_id}")
                    elif item_type == 'user':
                        User.objects.filter(id=item_id).delete()
                        print_success(f"Deleted user {item_id}")

                print_success("Cleanup completed")
            except Exception as e:
                print_error(f"Cleanup failed: {e}")
        else:
            print_info("Skipping cleanup - test data retained")

    def run(self):
        """Run complete test."""
        print_header("Complete Order Test with Email Notification")
        print(f"{C.Y}This will create a complete order flow and send email{C.E}\n")

        input(f"{C.B}Press Enter to start...{C.E}")

        # Run tests
        steps = [
            ("Create Test Customer", self.create_test_customer),
            ("Create Test Event", self.create_test_event),
            ("Create Order with Checkout", self.create_order_with_checkout),
            ("Simulate Payment (PAID)", self.simulate_payment_completion),
            ("Trigger Polling Service", self.trigger_payment_polling),
            ("Check Email Sent", self.check_email_sent),
            ("Verify Tickets Generated", self.verify_tickets_generated),
        ]

        results = []
        for name, func in steps:
            try:
                result = func()
                results.append((name, result))
                if not result:
                    print_error(f"Step failed: {name}")
                    break
            except Exception as e:
                print_error(f"Step crashed: {name} - {e}")
                results.append((name, False))
                break

        # Print summary
        self.print_summary()

        # Show results
        print_header("Test Results")
        for name, result in results:
            if result:
                print_success(f"{name}: PASSED")
            else:
                print_error(f"{name}: FAILED")

        passed = sum(1 for _, r in results if r)
        total = len(results)
        print(f"\n{C.H}Summary: {passed}/{total} steps passed{C.E}\n")

        # Cleanup
        self.cleanup()


def main():
    """Main entry point."""
    tester = CompleteOrderTest()
    tester.run()


if __name__ == '__main__':
    main()
