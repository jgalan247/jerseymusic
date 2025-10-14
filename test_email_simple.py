#!/usr/bin/env python
"""
Simple Complete Order Test with Email

Creates a minimal order, marks as PAID, triggers polling, sends email.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from payments import sumup as sumup_api
from payments.models import SumUpCheckout
from payments.polling_service import PaymentPollingService
from events.models import Event, TicketTier
from orders.models import Order, OrderItem

User = get_user_model()

print("\n" + "="*80)
print("Complete Order Test with Email Notification")
print("="*80 + "\n")

# Step 1: Get test customer
print("Step 1: Getting test customer...")
customer = User.objects.filter(email='test.customer@jerseyevents.je').first()
if not customer:
    customer = User.objects.create_user(
        email='test.customer@jerseyevents.je',
        password='testpass123',
        first_name='Test',
        last_name='Customer',
        user_type='customer',
        email_verified=True
    )
    print("✅ Customer created")
else:
    print("✅ Using existing customer")

# Step 2: Get test event
print("\nStep 2: Getting test event...")
event = Event.objects.filter(status='published').first()
if not event:
    print("❌ No published events found. Creating one...")
    artist = User.objects.filter(user_type='artist').first()
    if not artist:
        artist = User.objects.create_user(
            email='test.artist@jerseyevents.je',
            password='testpass123',
            first_name='Test',
            last_name='Artist',
            user_type='artist',
            email_verified=True
        )

    event = Event.objects.create(
        title=f'Test Event {datetime.now().strftime("%Y%m%d%H%M")}',
        slug=f'test-event-{datetime.now().strftime("%Y%m%d%H%M")}',
        description='Test event',
        organiser=artist,
        venue_name='Test Venue',
        venue_address='Test Address',
        event_date=timezone.now().date() + timedelta(days=30),
        event_time=datetime.strptime('19:00', '%H:%M').time(),
        capacity=100,
        ticket_price=Decimal('25.00'),
        status='published'
    )
    print(f"✅ Event created: {event.title}")
else:
    print(f"✅ Using event: {event.title}")

# Step 3: Create order
print("\nStep 3: Creating order...")
order_number = f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
subtotal = Decimal('50.00')
total = Decimal('50.90')  # Including fees

order = Order.objects.create(
    order_number=order_number,
    user=customer,
    email=customer.email,
    status='pending_payment',
    subtotal=subtotal,
    shipping_cost=Decimal('0.00'),
    tax_amount=Decimal('0.90'),  # Platform fee
    total=total,
    payment_method='sumup',
    is_paid=False,
)

print(f"✅ Order created: {order.order_number}")
print(f"   Total: £{order.total}")

# Create order item
order_item = OrderItem.objects.create(
    order=order,
    event=event,
    event_title=event.title,
    event_organiser=event.organiser.get_full_name(),
    event_date=event.event_date,
    venue_name=event.venue_name,
    quantity=2,
    price=Decimal('25.00'),
    total=Decimal('50.00'),
)

print(f"✅ Order item created: {order_item.quantity} tickets")

# Step 4: Create SumUp checkout
print("\nStep 4: Creating real SumUp checkout...")

try:
    checkout_data = sumup_api.create_checkout_simple(
        amount=float(order.total),
        currency='GBP',
        reference=order.order_number,
        description=f'Jersey Events - {event.title}',
        return_url='http://localhost:8000/payments/success/',
        expected_amount=float(order.total)
    )

    checkout_id = checkout_data['id']
    print(f"✅ Checkout created: {checkout_id}")

    # Create checkout record
    sumup_checkout = SumUpCheckout.objects.create(
        order=order,
        checkout_id=checkout_id,
        checkout_reference=order.order_number,
        amount=order.total,
        currency='GBP',
        status='PENDING',
    )

    # Update order
    order.transaction_id = checkout_id
    order.status = 'pending_verification'
    order.save()

    print(f"✅ Order updated with checkout ID")

except Exception as e:
    print(f"❌ Checkout creation failed: {e}")
    sys.exit(1)

# Step 5: Simulate payment (mark as PAID)
print("\nStep 5: Simulating payment completion...")
sumup_checkout.status = 'PAID'
sumup_checkout.paid_at = timezone.now()
sumup_checkout.save()

print("✅ Checkout marked as PAID")
print(f"   Paid at: {sumup_checkout.paid_at}")

# Step 6: Trigger polling
print("\nStep 6: Triggering payment polling...")
polling_service = PaymentPollingService()
polling_service.process_pending_payments()

# Refresh order
order.refresh_from_db()

print(f"✅ Polling complete")
print(f"   Order status: {order.status}")
print(f"   Is paid: {order.is_paid}")

if order.status == 'completed' and order.is_paid:
    print("\n" + "="*80)
    print("✨ SUCCESS! Order completed and paid!")
    print("="*80)

    # Check for tickets
    from events.models import Ticket
    tickets = Ticket.objects.filter(order=order)
    if tickets.exists():
        print(f"\n✅ {tickets.count()} ticket(s) generated!")
        for ticket in tickets:
            print(f"   - {ticket.ticket_number}: {ticket.attendee_name}")

    # Check email
    print("\n📧 Email Notification:")
    print(f"   Check MailHog: http://localhost:8025")
    print(f"   Subject: Order Confirmation - {order.order_number}")
    print(f"   Recipient: {customer.email}")

else:
    print("\n❌ Order not completed")
    print(f"   Status: {order.status}")
    print(f"   Is paid: {order.is_paid}")

print("\n" + "="*80)
print("Test Complete!")
print("="*80)

print(f"\nOrder ID: {order.id}")
print(f"Order Number: {order.order_number}")
print(f"Status: {order.status}")
print(f"Total: £{order.total}")

# Cleanup prompt
cleanup = input("\nDelete test data? (y/n): ").strip().lower()
if cleanup == 'y':
    order.delete()
    print("✅ Order deleted")
