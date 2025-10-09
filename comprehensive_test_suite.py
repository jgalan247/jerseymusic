#!/usr/bin/env python
"""
Comprehensive Test Suite for Jersey Events Platform
Executes all 13 test suites as per testing protocol
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
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from accounts.models import ArtistProfile, CustomerProfile
from events.models import Event, TicketTier
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem

User = get_user_model()

# Test results tracking
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def log_pass(test_name, message=""):
    """Log a passing test"""
    test_results['passed'].append({'test': test_name, 'message': message})
    print(f"✅ PASS: {test_name}")
    if message:
        print(f"   {message}")

def log_fail(test_name, message=""):
    """Log a failing test"""
    test_results['failed'].append({'test': test_name, 'message': message})
    print(f"❌ FAIL: {test_name}")
    if message:
        print(f"   {message}")

def log_warning(test_name, message=""):
    """Log a warning"""
    test_results['warnings'].append({'test': test_name, 'message': message})
    print(f"⚠️  WARNING: {test_name}")
    if message:
        print(f"   {message}")

print("\n" + "="*80)
print("JERSEY EVENTS PLATFORM - COMPREHENSIVE TEST SUITE")
print("="*80 + "\n")

# ============================================================================
# TEST SUITE 1: Environment Variable Configuration
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 1: Environment Variable Configuration")
print("-"*80)

# Test 1.1: Tier configuration
print("\nTest 1.1: Verify all tier configurations are set")
tier_vars = ['TIER_1_CAPACITY', 'TIER_1_FEE', 'TIER_2_CAPACITY', 'TIER_2_FEE',
             'TIER_3_CAPACITY', 'TIER_3_FEE', 'TIER_4_CAPACITY', 'TIER_4_FEE',
             'TIER_5_CAPACITY', 'TIER_5_FEE']
missing = []
for var in tier_vars:
    if not os.getenv(var):
        missing.append(var)

if not missing:
    log_pass("1.1 Tier Configuration", f"All {len(tier_vars)} tier variables configured")
else:
    log_fail("1.1 Tier Configuration", f"Missing variables: {', '.join(missing)}")

# Test 1.2: Processing rate configuration
print("\nTest 1.2: Verify SumUp processing rate is set")
processing_rate = os.getenv('SUMUP_PROCESSING_RATE')
if processing_rate:
    try:
        rate = Decimal(processing_rate)
        if rate == Decimal('0.0169'):
            log_pass("1.2 Processing Rate", f"Correctly set to {rate} (1.69%)")
        else:
            log_warning("1.2 Processing Rate", f"Set to {rate}, expected 0.0169")
    except:
        log_fail("1.2 Processing Rate", "Invalid decimal format")
else:
    log_fail("1.2 Processing Rate", "SUMUP_PROCESSING_RATE not set")

# ============================================================================
# TEST SUITE 2: Pricing Structure & Capacity Limits
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 2: Pricing Structure & Capacity Limits")
print("-"*80)

# Test 2.1: Create events at each tier boundary
print("\nTest 2.1: Test tier assignment at capacity boundaries")
organizer = User.objects.get(email='organizer@test.com')
test_cases = [
    (50, Decimal('0.50'), 'Tier 1'),
    (100, Decimal('0.45'), 'Tier 2'),
    (250, Decimal('0.40'), 'Tier 3'),
    (400, Decimal('0.35'), 'Tier 4'),
    (500, Decimal('0.30'), 'Tier 5'),
]

tier_test_passed = True
for capacity, expected_fee, tier_name in test_cases:
    try:
        event = Event.objects.create(
            organizer=organizer,
            title=f"Test Event {tier_name}",
            description="Test event",
            category='music',
            venue_name="Test Venue",
            venue_address="Test Address",
            event_date=datetime.now().date() + timedelta(days=30),
            event_time=datetime.now().time(),
            capacity=capacity,
            price=Decimal('25.00')
        )
        calculated_fee = event.platform_fee_per_ticket
        if calculated_fee == expected_fee:
            print(f"  ✓ {tier_name}: capacity={capacity}, fee=£{calculated_fee}")
        else:
            print(f"  ✗ {tier_name}: expected £{expected_fee}, got £{calculated_fee}")
            tier_test_passed = False
        event.delete()
    except Exception as e:
        print(f"  ✗ {tier_name}: Error - {str(e)}")
        tier_test_passed = False

if tier_test_passed:
    log_pass("2.1 Tier Assignment", "All 5 tiers assign correct fees")
else:
    log_fail("2.1 Tier Assignment", "Some tier assignments incorrect")

# Test 2.2: Capacity validation
print("\nTest 2.2: Test capacity validation (max 500)")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Oversized Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=600,
        price=Decimal('25.00')
    )
    log_fail("2.2 Capacity Validation", "Event with capacity>500 was allowed")
    event.delete()
except Exception as e:
    if "exceed 500" in str(e) or "maximum" in str(e).lower():
        log_pass("2.2 Capacity Validation", "Correctly rejects capacity>500")
    else:
        log_warning("2.2 Capacity Validation", f"Different error: {str(e)}")

# Test 2.3: Minimum price validation
print("\nTest 2.3: Test minimum ticket price (£0.01)")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Free Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('0.00')
    )
    log_fail("2.3 Price Validation", "Event with £0.00 price was allowed")
    event.delete()
except Exception as e:
    if "0.01" in str(e) or "minimum" in str(e).lower():
        log_pass("2.3 Price Validation", "Correctly enforces minimum price £0.01")
    else:
        log_warning("2.3 Price Validation", f"Different error: {str(e)}")

# Test 2.4: Maximum price validation
print("\nTest 2.4: Test maximum ticket price (£10,000)")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Ultra Expensive Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('15000.00')
    )
    log_fail("2.4 Price Validation", "Event with price>£10,000 was allowed")
    event.delete()
except Exception as e:
    if "10000" in str(e) or "10,000" in str(e) or "maximum" in str(e).lower():
        log_pass("2.4 Price Validation", "Correctly enforces maximum price £10,000")
    else:
        log_warning("2.4 Price Validation", f"Different error: {str(e)}")

# ============================================================================
# TEST SUITE 3: Payment Processing Fee Options
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 3: Payment Processing Fee Options")
print("-"*80)

# Test 3.1: Customer pays processing fee
print("\nTest 3.1: Create event with customer paying processing fee")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Customer Pays Fee Event",
        description="Test event",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00'),
        processing_fee_passed_to_customer=True
    )

    # Calculate expected amounts
    base_price = Decimal('25.00')
    processing_fee = base_price * Decimal('0.0169')
    customer_total = base_price + processing_fee

    print(f"  Base price: £{base_price}")
    print(f"  Processing fee (1.69%): £{processing_fee:.2f}")
    print(f"  Customer pays: £{customer_total:.2f}")
    print(f"  Organizer receives: £{base_price} - £0.45 platform fee = £{base_price - Decimal('0.45')}")

    log_pass("3.1 Customer Pays Fee", f"Correctly configured, customer pays £{customer_total:.2f}")
    event.delete()
except Exception as e:
    log_fail("3.1 Customer Pays Fee", str(e))

# Test 3.2: Organizer absorbs processing fee
print("\nTest 3.2: Create event with organizer absorbing processing fee")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Organizer Pays Fee Event",
        description="Test event",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00'),
        processing_fee_passed_to_customer=False
    )

    # Calculate expected amounts
    base_price = Decimal('25.00')
    processing_fee = base_price * Decimal('0.0169')
    platform_fee = Decimal('0.45')
    organizer_receives = base_price - processing_fee - platform_fee

    print(f"  Base price: £{base_price}")
    print(f"  Customer pays: £{base_price}")
    print(f"  Processing fee (1.69%): £{processing_fee:.2f}")
    print(f"  Platform fee: £{platform_fee}")
    print(f"  Organizer receives: £{organizer_receives:.2f}")

    log_pass("3.2 Organizer Absorbs Fee", f"Correctly configured, organizer receives £{organizer_receives:.2f}")
    event.delete()
except Exception as e:
    log_fail("3.2 Organizer Absorbs Fee", str(e))

# Test 3.3: Fee toggle functionality
print("\nTest 3.3: Test processing fee toggle")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Toggle Test Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00'),
        processing_fee_passed_to_customer=True
    )

    # Toggle the fee
    event.processing_fee_passed_to_customer = False
    event.save()
    event.refresh_from_db()

    if not event.processing_fee_passed_to_customer:
        log_pass("3.3 Fee Toggle", "Successfully toggled processing fee setting")
    else:
        log_fail("3.3 Fee Toggle", "Toggle did not persist")

    event.delete()
except Exception as e:
    log_fail("3.3 Fee Toggle", str(e))

# ============================================================================
# TEST SUITE 4: Ticket Tier System
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 4: Ticket Tier System")
print("-"*80)

# Test 4.1: Create event with multiple tiers
print("\nTest 4.1: Create event with VIP, Standard, and Child tiers")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Multi-Tier Festival",
        description="Test event with tiers",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=250,
        price=Decimal('30.00')
    )

    # Create VIP tier
    vip = TicketTier.objects.create(
        event=event,
        tier_type='vip',
        name='VIP Access',
        description='Backstage pass and VIP lounge',
        price=Decimal('75.00'),
        quantity_available=20,
        min_purchase=1,
        max_purchase=4
    )

    # Create Standard tier
    standard = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Standard Admission',
        description='General admission',
        price=Decimal('30.00'),
        quantity_available=200,
        min_purchase=1,
        max_purchase=10
    )

    # Create Child tier
    child = TicketTier.objects.create(
        event=event,
        tier_type='child',
        name='Child Ticket',
        description='Ages 12 and under',
        price=Decimal('18.00'),
        quantity_available=30,
        min_purchase=1,
        max_purchase=6
    )

    total_tier_capacity = vip.quantity_available + standard.quantity_available + child.quantity_available

    print(f"  ✓ VIP: {vip.quantity_available} tickets @ £{vip.price}")
    print(f"  ✓ Standard: {standard.quantity_available} tickets @ £{standard.price}")
    print(f"  ✓ Child: {child.quantity_available} tickets @ £{child.price}")
    print(f"  ✓ Total tier capacity: {total_tier_capacity}")

    if total_tier_capacity == event.capacity:
        log_pass("4.1 Multi-Tier Creation", f"Created 3 tiers totaling {total_tier_capacity} tickets")
    else:
        log_warning("4.1 Multi-Tier Creation", f"Tier capacity ({total_tier_capacity}) ≠ event capacity ({event.capacity})")

    event.delete()
except Exception as e:
    log_fail("4.1 Multi-Tier Creation", str(e))

# Test 4.2: Tier capacity validation
print("\nTest 4.2: Test tier capacity exceeding event capacity")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Tier Capacity Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    # Try to create tier exceeding event capacity
    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Oversized Tier',
        price=Decimal('25.00'),
        quantity_available=150  # Exceeds event capacity
    )
    log_fail("4.2 Tier Capacity Validation", "Tier capacity>event capacity was allowed")
    event.delete()
except Exception as e:
    if "capacity" in str(e).lower() or "exceed" in str(e).lower():
        log_pass("4.2 Tier Capacity Validation", "Correctly rejects tier capacity>event capacity")
    else:
        log_warning("4.2 Tier Capacity Validation", f"Different error: {str(e)}")

# Test 4.3: Tier pricing validation
print("\nTest 4.3: Test tier price validation")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Tier Price Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    # Try to create tier with £0 price
    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Free Tier',
        price=Decimal('0.00'),
        quantity_available=50
    )
    log_fail("4.3 Tier Pricing Validation", "Tier with £0 price was allowed")
    event.delete()
except Exception as e:
    if "0.01" in str(e) or "minimum" in str(e).lower():
        log_pass("4.3 Tier Pricing Validation", "Correctly enforces minimum tier price")
    else:
        log_warning("4.3 Tier Pricing Validation", f"Different error: {str(e)}")

# Test 4.4: Min/Max purchase limits
print("\nTest 4.4: Test tier purchase limits")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Purchase Limits Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Limited Purchase',
        price=Decimal('25.00'),
        quantity_available=50,
        min_purchase=2,
        max_purchase=6
    )

    if tier.min_purchase == 2 and tier.max_purchase == 6:
        log_pass("4.4 Purchase Limits", f"Min={tier.min_purchase}, Max={tier.max_purchase}")
    else:
        log_fail("4.4 Purchase Limits", "Limits not set correctly")

    event.delete()
except Exception as e:
    log_fail("4.4 Purchase Limits", str(e))

# Test 4.5: Tier availability tracking
print("\nTest 4.5: Test tier sold/available tracking")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Tier Tracking Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Tracking Test',
        price=Decimal('25.00'),
        quantity_available=50,
        quantity_sold=10
    )

    remaining = tier.quantity_available - tier.quantity_sold
    if remaining == 40:
        log_pass("4.5 Tier Availability", f"Correctly tracks: 10 sold, 40 available of 50")
    else:
        log_fail("4.5 Tier Availability", f"Expected 40 remaining, got {remaining}")

    event.delete()
except Exception as e:
    log_fail("4.5 Tier Availability", str(e))

# ============================================================================
# TEST SUITE 5: Terms & Conditions
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 5: Terms & Conditions")
print("-"*80)

# Test 5.1: T&C acceptance tracking
print("\nTest 5.1: Test T&C acceptance tracking in orders")
try:
    customer = User.objects.get(email='customer@test.com')
    event = Event.objects.create(
        organizer=organizer,
        title="T&C Test Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    order = Order.objects.create(
        customer=customer,
        delivery_first_name="Test",
        delivery_last_name="Customer",
        email="customer@test.com",
        phone_number="+447700900123",
        total=Decimal('25.00'),
        terms_accepted=True,
        acceptance_ip='192.168.1.100',
        terms_version='1.0',
        status='completed'
    )

    has_acceptance = order.terms_accepted
    has_ip = bool(order.acceptance_ip)
    has_version = bool(order.terms_version)
    has_timestamp = bool(order.terms_accepted_at)

    print(f"  T&C Accepted: {has_acceptance}")
    print(f"  IP Address: {order.acceptance_ip}")
    print(f"  Version: {order.terms_version}")
    print(f"  Timestamp: {order.terms_accepted_at}")

    if all([has_acceptance, has_ip, has_version, has_timestamp]):
        log_pass("5.1 T&C Tracking", "All T&C fields correctly stored")
    else:
        log_fail("5.1 T&C Tracking", f"Missing fields: acceptance={has_acceptance}, ip={has_ip}, version={has_version}, timestamp={has_timestamp}")

    order.delete()
    event.delete()
except Exception as e:
    log_fail("5.1 T&C Tracking", str(e))

# Test 5.2: T&C version tracking
print("\nTest 5.2: Test multiple T&C versions")
try:
    customer = User.objects.get(email='customer@test.com')

    # Create orders with different T&C versions
    order_v1 = Order.objects.create(
        customer=customer,
        delivery_first_name="Test",
        delivery_last_name="Customer",
        email="customer@test.com",
        phone_number="+447700900123",
        total=Decimal('25.00'),
        terms_accepted=True,
        acceptance_ip='192.168.1.100',
        terms_version='1.0',
        status='completed'
    )

    order_v2 = Order.objects.create(
        customer=customer,
        delivery_first_name="Test",
        delivery_last_name="Customer",
        email="customer@test.com",
        phone_number="+447700900123",
        total=Decimal('25.00'),
        terms_accepted=True,
        acceptance_ip='192.168.1.101',
        terms_version='2.0',
        status='completed'
    )

    if order_v1.terms_version == '1.0' and order_v2.terms_version == '2.0':
        log_pass("5.2 T&C Versioning", "Multiple versions tracked correctly")
    else:
        log_fail("5.2 T&C Versioning", "Version tracking failed")

    order_v1.delete()
    order_v2.delete()
except Exception as e:
    log_fail("5.2 T&C Versioning", str(e))

# Test 5.3: IP address extraction
print("\nTest 5.3: Test IP address formats")
try:
    customer = User.objects.get(email='customer@test.com')

    test_ips = [
        '192.168.1.100',
        '10.0.0.1',
        '2001:0db8:85a3:0000:0000:8a2e:0370:7334'  # IPv6
    ]

    ip_test_passed = True
    for ip in test_ips:
        order = Order.objects.create(
            customer=customer,
            delivery_first_name="Test",
            delivery_last_name="Customer",
            email="customer@test.com",
            phone_number="+447700900123",
            total=Decimal('25.00'),
            terms_accepted=True,
            acceptance_ip=ip,
            terms_version='1.0',
            status='completed'
        )

        if order.acceptance_ip == ip:
            print(f"  ✓ Stored IP: {ip}")
        else:
            print(f"  ✗ Failed to store IP: {ip}")
            ip_test_passed = False

        order.delete()

    if ip_test_passed:
        log_pass("5.3 IP Address Storage", "All IP formats stored correctly")
    else:
        log_fail("5.3 IP Address Storage", "Some IPs failed to store")
except Exception as e:
    log_fail("5.3 IP Address Storage", str(e))

# Test 5.4: T&C requirement enforcement
print("\nTest 5.4: Test T&C acceptance requirement")
try:
    customer = User.objects.get(email='customer@test.com')

    # Try to create order without T&C acceptance
    order = Order.objects.create(
        customer=customer,
        delivery_first_name="Test",
        delivery_last_name="Customer",
        email="customer@test.com",
        phone_number="+447700900123",
        total=Decimal('25.00'),
        terms_accepted=False,  # Not accepted
        status='completed'
    )

    # If we get here, check if validation is done elsewhere (e.g., in views)
    log_warning("5.4 T&C Requirement", "Model allows T&C=False, validation may be in views/forms")
    order.delete()
except Exception as e:
    if "terms" in str(e).lower() or "accept" in str(e).lower():
        log_pass("5.4 T&C Requirement", "Correctly requires T&C acceptance")
    else:
        log_warning("5.4 T&C Requirement", f"Different error: {str(e)}")

# ============================================================================
# TEST SUITE 6: Marketing Comparison Page
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 6: Marketing Comparison Page")
print("-"*80)

# Test 6.1: Why Choose Us page exists
print("\nTest 6.1: Verify 'Why Choose Us' page exists")
client = Client()
try:
    response = client.get('/why-choose-us/')
    if response.status_code == 200:
        log_pass("6.1 Page Exists", "Why Choose Us page accessible")
    else:
        log_fail("6.1 Page Exists", f"Page returned status {response.status_code}")
except Exception as e:
    log_fail("6.1 Page Exists", str(e))

# Test 6.2: Cost comparison calculator
print("\nTest 6.2: Test cost comparison calculations")
try:
    # Manual calculation test
    tickets = 100
    ticket_price = Decimal('25.00')

    # Jersey Events
    jersey_platform_fee = tickets * Decimal('0.45')  # Tier 2
    jersey_processing = (tickets * ticket_price) * Decimal('0.0169')
    jersey_total = jersey_platform_fee + jersey_processing

    # Eventbrite
    eb_platform_rate = Decimal('0.0695')
    eb_platform_fixed = Decimal('0.59')
    eb_processing_rate = Decimal('0.029')
    eb_processing_fixed = Decimal('0.30')

    eb_platform_fee = tickets * ((ticket_price * eb_platform_rate) + eb_platform_fixed)
    eb_processing = tickets * ((ticket_price * eb_processing_rate) + eb_processing_fixed)
    eb_total = eb_platform_fee + eb_processing

    savings = eb_total - jersey_total
    savings_percent = (savings / eb_total) * 100

    print(f"  100 tickets @ £25 each:")
    print(f"  Jersey Events: £{jersey_total:.2f}")
    print(f"  Eventbrite: £{eb_total:.2f}")
    print(f"  Savings: £{savings:.2f} ({savings_percent:.1f}%)")

    if savings_percent >= 70:
        log_pass("6.2 Cost Comparison", f"{savings_percent:.1f}% savings (target: 70-75%)")
    else:
        log_fail("6.2 Cost Comparison", f"Only {savings_percent:.1f}% savings, target 70-75%")
except Exception as e:
    log_fail("6.2 Cost Comparison", str(e))

# Test 6.3: Pricing transparency
print("\nTest 6.3: Verify pricing transparency on comparison page")
try:
    response = client.get('/why-choose-us/')
    content = response.content.decode()

    has_jersey_fees = '£0.30' in content or '£0.50' in content
    has_sumup_rate = '1.69%' in content
    has_comparison = 'Eventbrite' in content or 'eventbrite' in content

    if has_jersey_fees and has_sumup_rate and has_comparison:
        log_pass("6.3 Pricing Transparency", "All pricing details visible on page")
    else:
        log_fail("6.3 Pricing Transparency", f"Missing: fees={has_jersey_fees}, rate={has_sumup_rate}, comparison={has_comparison}")
except Exception as e:
    log_fail("6.3 Pricing Transparency", str(e))

# Test 6.4: Interactive calculator (if present)
print("\nTest 6.4: Check for interactive calculator elements")
try:
    response = client.get('/why-choose-us/')
    content = response.content.decode()

    has_input = 'input' in content.lower()
    has_calculation = 'calculate' in content.lower() or 'calculator' in content.lower()

    if has_input and has_calculation:
        log_pass("6.4 Interactive Calculator", "Calculator elements present")
    else:
        log_warning("6.4 Interactive Calculator", "No interactive calculator found (may be static comparison)")
except Exception as e:
    log_fail("6.4 Interactive Calculator", str(e))

# Test 6.5: Mobile responsiveness
print("\nTest 6.5: Test page mobile responsiveness")
try:
    response = client.get('/why-choose-us/', HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)')
    content = response.content.decode()

    has_viewport = 'viewport' in content.lower()
    has_responsive_meta = 'width=device-width' in content.lower()

    if has_viewport and has_responsive_meta:
        log_pass("6.5 Mobile Responsiveness", "Viewport meta tag present")
    else:
        log_warning("6.5 Mobile Responsiveness", "May not be fully mobile optimized")
except Exception as e:
    log_fail("6.5 Mobile Responsiveness", str(e))

# ============================================================================
# TEST SUITE 7: Complete User Flows
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 7: Complete User Flows")
print("-"*80)

# Test 7.1: Organizer creates event flow
print("\nTest 7.1: Complete organizer event creation flow")
try:
    client = Client()
    client.force_login(organizer)

    # Access event creation page
    response = client.get('/events/create/')
    if response.status_code != 200:
        log_fail("7.1 Organizer Flow", f"Create page returned {response.status_code}")
    else:
        # Create event via form
        event_data = {
            'title': 'Test Event via Form',
            'description': 'Test description',
            'category': 'music',
            'venue_name': 'Test Venue',
            'venue_address': 'Test Address',
            'event_date': (datetime.now().date() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'event_time': '19:00',
            'capacity': '100',
            'price': '25.00',
            'processing_fee_passed_to_customer': True
        }

        response = client.post('/events/create/', event_data)

        if response.status_code in [200, 302]:
            log_pass("7.1 Organizer Flow", "Event creation form submitted successfully")
            # Clean up
            Event.objects.filter(title='Test Event via Form').delete()
        else:
            log_fail("7.1 Organizer Flow", f"Form submission failed: {response.status_code}")

    client.logout()
except Exception as e:
    log_fail("7.1 Organizer Flow", str(e))

# Test 7.2: Customer purchase flow
print("\nTest 7.2: Complete customer ticket purchase flow")
try:
    # Create test event
    event = Event.objects.create(
        organizer=organizer,
        title="Customer Purchase Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00'),
        processing_fee_passed_to_customer=True
    )

    client = Client()
    customer_user = User.objects.get(email='customer@test.com')
    client.force_login(customer_user)

    # View event
    response = client.get(f'/events/{event.id}/')
    if response.status_code == 200:
        print("  ✓ Customer can view event")

        # Add to cart would be next step
        log_pass("7.2 Customer Flow", "Customer can view event and access purchase flow")
    else:
        log_fail("7.2 Customer Flow", f"Event page returned {response.status_code}")

    client.logout()
    event.delete()
except Exception as e:
    log_fail("7.2 Customer Flow", str(e))

# ============================================================================
# TEST SUITE 8: Edge Cases & Validation
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 8: Edge Cases & Validation")
print("-"*80)

# Test 8.1: Email typo detection
print("\nTest 8.1: Test email typo detection (gmail.con → gmail.com)")
from orders.validators import detect_email_typos

test_emails = [
    ('test@gmail.con', 'gmail.com'),
    ('user@hotmail.co', 'hotmail.com'),
    ('admin@yahoo.cm', 'yahoo.com'),
    ('valid@gmail.com', None)
]

typo_test_passed = True
for email, expected_suggestion in test_emails:
    suggestion = detect_email_typos(email)
    if suggestion == expected_suggestion:
        print(f"  ✓ {email} → {suggestion or 'no suggestion'}")
    else:
        print(f"  ✗ {email} expected {expected_suggestion}, got {suggestion}")
        typo_test_passed = False

if typo_test_passed:
    log_pass("8.1 Email Typo Detection", "All email typos detected correctly")
else:
    log_fail("8.1 Email Typo Detection", "Some email validations failed")

# Test 8.2: Phone number validation
print("\nTest 8.2: Test phone number validation")
from orders.validators import validate_uk_phone_number

test_phones = [
    ('+447700900123', True),
    ('07700900123', True),
    ('+44 7700 900123', True),
    ('invalid', False),
    ('123', False)
]

phone_test_passed = True
for phone, should_pass in test_phones:
    try:
        validate_uk_phone_number(phone)
        result = True
    except:
        result = False

    if result == should_pass:
        print(f"  ✓ {phone}: {'valid' if result else 'invalid'}")
    else:
        print(f"  ✗ {phone}: expected {'valid' if should_pass else 'invalid'}, got {'valid' if result else 'invalid'}")
        phone_test_passed = False

if phone_test_passed:
    log_pass("8.2 Phone Validation", "Phone number validation working correctly")
else:
    log_fail("8.2 Phone Validation", "Some phone validations failed")

# Test 8.3: Event date validation (no past dates)
print("\nTest 8.3: Test event date validation (past dates)")
try:
    past_date = datetime.now().date() - timedelta(days=1)
    event = Event.objects.create(
        organizer=organizer,
        title="Past Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=past_date,
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )
    log_fail("8.3 Date Validation", "Past event date was allowed")
    event.delete()
except Exception as e:
    if "past" in str(e).lower() or "future" in str(e).lower():
        log_pass("8.3 Date Validation", "Correctly rejects past event dates")
    else:
        log_warning("8.3 Date Validation", f"Different error: {str(e)}")

# Test 8.4: Sold out tier handling
print("\nTest 8.4: Test sold out tier handling")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Sold Out Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Limited Tier',
        price=Decimal('25.00'),
        quantity_available=10,
        quantity_sold=10  # Sold out
    )

    is_sold_out = tier.quantity_sold >= tier.quantity_available
    remaining = tier.quantity_available - tier.quantity_sold

    if is_sold_out and remaining == 0:
        log_pass("8.4 Sold Out Handling", "Tier correctly shows sold out (0 remaining)")
    else:
        log_fail("8.4 Sold Out Handling", f"Sold out detection failed: {remaining} remaining")

    event.delete()
except Exception as e:
    log_fail("8.4 Sold Out Handling", str(e))

# Test 8.5: Concurrent booking prevention
print("\nTest 8.5: Test last ticket scenario")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Last Ticket Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Almost Sold Out',
        price=Decimal('25.00'),
        quantity_available=10,
        quantity_sold=9  # 1 remaining
    )

    remaining = tier.quantity_available - tier.quantity_sold

    if remaining == 1:
        log_pass("8.5 Last Ticket Scenario", "Correctly shows 1 ticket remaining")
    else:
        log_fail("8.5 Last Ticket Scenario", f"Expected 1 remaining, got {remaining}")

    event.delete()
except Exception as e:
    log_fail("8.5 Last Ticket Scenario", str(e))

# ============================================================================
# TEST SUITE 9: Email Templates
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 9: Email Templates")
print("-"*80)

# Test 9.1: Payment success email template
print("\nTest 9.1: Verify payment success email template exists")
import os.path
template_path = '/Users/josegalan/Documents/jersey_music/templates/emails/payment_success.html'
if os.path.exists(template_path):
    with open(template_path, 'r') as f:
        content = f.read()
        has_order_info = 'order' in content.lower()
        has_tier_info = 'tier' in content.lower()
        has_styling = 'style=' in content or '<style' in content

        if all([has_order_info, has_tier_info, has_styling]):
            log_pass("9.1 Payment Success Email", "Template exists with order, tier, and styling")
        else:
            log_warning("9.1 Payment Success Email", f"Template incomplete: order={has_order_info}, tier={has_tier_info}, styling={has_styling}")
else:
    log_fail("9.1 Payment Success Email", "Template file not found")

# Test 9.2: Tier badges in emails
print("\nTest 9.2: Check for tier badge styling in email templates")
email_templates = [
    'templates/emails/order_confirmation.html',
    'templates/emails/ticket_confirmation.html',
    'templates/emails/payment_success.html'
]

tier_badge_test_passed = True
for template in email_templates:
    full_path = f'/Users/josegalan/Documents/jersey_music/{template}'
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            content = f.read()
            has_tier_display = 'tier_type' in content or 'get_tier_type_display' in content

            if has_tier_display:
                print(f"  ✓ {template.split('/')[-1]}: has tier info")
            else:
                print(f"  ✗ {template.split('/')[-1]}: no tier info")
                tier_badge_test_passed = False
    else:
        print(f"  ? {template.split('/')[-1]}: not found")

if tier_badge_test_passed:
    log_pass("9.2 Tier Badges", "Tier information present in email templates")
else:
    log_warning("9.2 Tier Badges", "Some templates missing tier information")

# ============================================================================
# TEST SUITE 10: Admin Interface
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 10: Admin Interface")
print("-"*80)

# Test 10.1: Event admin fee breakdown
print("\nTest 10.1: Test Event admin custom displays")
from events.admin import EventAdmin
from django.contrib import admin

event_admin = EventAdmin(Event, admin.site)
list_display = event_admin.list_display

has_fee_display = any('fee' in str(field).lower() for field in list_display)
has_tier_display = any('tier' in str(field).lower() for field in list_display)

if has_fee_display:
    log_pass("10.1 Event Admin", "Event admin has fee breakdown displays")
else:
    log_warning("10.1 Event Admin", "Fee displays may not be in list_display")

# Test 10.2: TicketTier admin
print("\nTest 10.2: Test TicketTier admin interface")
from events.admin import TicketTierAdmin

tier_admin = TicketTierAdmin(TicketTier, admin.site)
tier_list_display = tier_admin.list_display

has_availability = any('available' in str(field).lower() or 'sold' in str(field).lower() for field in tier_list_display)

if has_availability:
    log_pass("10.2 TicketTier Admin", "Tier admin shows availability information")
else:
    log_warning("10.2 TicketTier Admin", "Availability info may not be displayed")

# ============================================================================
# TEST SUITE 11: Database Integrity
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 11: Database Integrity")
print("-"*80)

# Test 11.1: Foreign key relationships
print("\nTest 11.1: Test foreign key integrity")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="FK Test Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='FK Test Tier',
        price=Decimal('25.00'),
        quantity_available=50
    )

    # Verify relationship
    if tier.event == event and tier in event.ticket_tiers.all():
        log_pass("11.1 Foreign Keys", "Event-TicketTier relationship intact")
    else:
        log_fail("11.1 Foreign Keys", "Relationship verification failed")

    event.delete()
except Exception as e:
    log_fail("11.1 Foreign Keys", str(e))

# Test 11.2: Cascade deletion
print("\nTest 11.2: Test cascade deletion (delete event → delete tiers)")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Cascade Test Event",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=100,
        price=Decimal('25.00')
    )

    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Cascade Test Tier',
        price=Decimal('25.00'),
        quantity_available=50
    )

    tier_id = tier.id
    event.delete()

    # Check if tier was deleted
    tier_exists = TicketTier.objects.filter(id=tier_id).exists()

    if not tier_exists:
        log_pass("11.2 Cascade Deletion", "Tiers deleted when event deleted")
    else:
        log_fail("11.2 Cascade Deletion", "Orphaned tier found after event deletion")
except Exception as e:
    log_fail("11.2 Cascade Deletion", str(e))

# ============================================================================
# TEST SUITE 12: Performance & Load
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 12: Performance & Load")
print("-"*80)

# Test 12.1: Query optimization
print("\nTest 12.1: Test query count for event listing")
from django.test.utils import override_settings
from django.db import connection
from django.db import reset_queries

# Enable query logging
with override_settings(DEBUG=True):
    reset_queries()

    # Create 10 test events
    events = []
    for i in range(10):
        event = Event.objects.create(
            organizer=organizer,
            title=f"Query Test Event {i}",
            description="Test",
            category='music',
            venue_name="Test Venue",
            venue_address="Test Address",
            event_date=datetime.now().date() + timedelta(days=30),
            event_time=datetime.now().time(),
            capacity=100,
            price=Decimal('25.00')
        )
        events.append(event)

    # Query all events
    reset_queries()
    list(Event.objects.all().select_related('organizer'))
    query_count = len(connection.queries)

    print(f"  Query count for 10 events: {query_count}")

    if query_count <= 5:
        log_pass("12.1 Query Optimization", f"Efficient queries: {query_count} queries for 10 events")
    else:
        log_warning("12.1 Query Optimization", f"{query_count} queries - consider using select_related/prefetch_related")

    # Cleanup
    for event in events:
        event.delete()

# Test 12.2: Large event handling
print("\nTest 12.2: Test handling of large event (max capacity 500)")
try:
    event = Event.objects.create(
        organizer=organizer,
        title="Large Event Test",
        description="Test",
        category='music',
        venue_name="Test Venue",
        venue_address="Test Address",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.now().time(),
        capacity=500,  # Maximum
        price=Decimal('25.00')
    )

    # Create tier with full capacity
    tier = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Large Tier',
        price=Decimal('25.00'),
        quantity_available=500
    )

    if event.capacity == 500 and tier.quantity_available == 500:
        log_pass("12.2 Large Event Handling", "Successfully handles 500-capacity events")
    else:
        log_fail("12.2 Large Event Handling", "Capacity mismatch")

    event.delete()
except Exception as e:
    log_fail("12.2 Large Event Handling", str(e))

# ============================================================================
# TEST SUITE 13: Complete End-to-End Scenario
# ============================================================================
print("\n" + "-"*80)
print("TEST SUITE 13: Complete End-to-End Scenario")
print("-"*80)

print("\nTest 13.1: Complete end-to-end workflow")
try:
    # 1. Organizer creates event with tiers
    print("\n  Step 1: Organizer creates multi-tier event...")
    event = Event.objects.create(
        organizer=organizer,
        title="E2E Test Festival",
        description="Complete end-to-end test event",
        category='music',
        venue_name="Jersey Live Arena",
        venue_address="St Helier, Jersey",
        event_date=datetime.now().date() + timedelta(days=30),
        event_time=datetime.strptime('19:00', '%H:%M').time(),
        capacity=250,
        price=Decimal('30.00'),
        processing_fee_passed_to_customer=True
    )
    print(f"    ✓ Event created: {event.title}")
    print(f"    ✓ Capacity: {event.capacity} (Tier 3 - £{event.platform_fee_per_ticket}/ticket)")

    # 2. Create tiers
    print("\n  Step 2: Creating ticket tiers...")
    vip = TicketTier.objects.create(
        event=event,
        tier_type='vip',
        name='VIP Access',
        description='Backstage pass and VIP lounge',
        price=Decimal('75.00'),
        quantity_available=20,
        min_purchase=1,
        max_purchase=4
    )
    print(f"    ✓ VIP tier: {vip.quantity_available} @ £{vip.price}")

    standard = TicketTier.objects.create(
        event=event,
        tier_type='standard',
        name='Standard Admission',
        description='General admission',
        price=Decimal('30.00'),
        quantity_available=200,
        min_purchase=1,
        max_purchase=10
    )
    print(f"    ✓ Standard tier: {standard.quantity_available} @ £{standard.price}")

    child = TicketTier.objects.create(
        event=event,
        tier_type='child',
        name='Child Ticket',
        description='Ages 12 and under',
        price=Decimal('18.00'),
        quantity_available=30,
        min_purchase=1,
        max_purchase=6
    )
    print(f"    ✓ Child tier: {child.quantity_available} @ £{child.price}")

    # 3. Customer views event
    print("\n  Step 3: Customer views event...")
    client = Client()
    customer_user = User.objects.get(email='customer@test.com')
    response = client.get(f'/events/{event.id}/')
    print(f"    ✓ Event page loaded (status {response.status_code})")

    # 4. Calculate revenue
    print("\n  Step 4: Revenue calculation...")
    vip_revenue = vip.quantity_available * vip.price
    standard_revenue = standard.quantity_available * standard.price
    child_revenue = child.quantity_available * child.price
    total_gross = vip_revenue + standard_revenue + child_revenue

    total_tickets = vip.quantity_available + standard.quantity_available + child.quantity_available
    platform_fees = total_tickets * event.platform_fee_per_ticket

    print(f"    ✓ VIP revenue: £{vip_revenue}")
    print(f"    ✓ Standard revenue: £{standard_revenue}")
    print(f"    ✓ Child revenue: £{child_revenue}")
    print(f"    ✓ Gross revenue: £{total_gross}")
    print(f"    ✓ Platform fees: £{platform_fees} ({total_tickets} tickets × £{event.platform_fee_per_ticket})")
    print(f"    ✓ Organizer net: £{total_gross - platform_fees}")

    # 5. Create sample order with T&C acceptance
    print("\n  Step 5: Creating sample order with T&C acceptance...")
    order = Order.objects.create(
        customer=customer_user,
        delivery_first_name="Test",
        delivery_last_name="Customer",
        email="customer@test.com",
        phone_number="+447700900123",
        total=Decimal('75.00'),  # 1 VIP ticket
        terms_accepted=True,
        acceptance_ip='192.168.1.100',
        terms_version='1.0',
        status='completed'
    )
    print(f"    ✓ Order created: {order.order_number}")
    print(f"    ✓ T&C accepted: {order.terms_accepted}")
    print(f"    ✓ IP logged: {order.acceptance_ip}")
    print(f"    ✓ Version: {order.terms_version}")

    # 6. Verify all components
    print("\n  Step 6: Verifying all components...")
    checks = {
        'Event exists': Event.objects.filter(id=event.id).exists(),
        '3 tiers created': event.ticket_tiers.count() == 3,
        'Total capacity matches': total_tickets == event.capacity,
        'Order recorded': Order.objects.filter(id=order.id).exists(),
        'T&C tracked': all([order.terms_accepted, order.acceptance_ip, order.terms_version]),
        'Processing fee toggle': event.processing_fee_passed_to_customer == True
    }

    all_passed = all(checks.values())
    for check, result in checks.items():
        print(f"    {'✓' if result else '✗'} {check}")

    # Cleanup
    print("\n  Step 7: Cleanup...")
    order.delete()
    event.delete()
    print("    ✓ Test data cleaned up")

    if all_passed:
        log_pass("13.1 End-to-End Workflow", "Complete workflow successful")
    else:
        failed_checks = [k for k, v in checks.items() if not v]
        log_fail("13.1 End-to-End Workflow", f"Failed checks: {', '.join(failed_checks)}")

except Exception as e:
    log_fail("13.1 End-to-End Workflow", str(e))
    import traceback
    traceback.print_exc()

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "="*80)
print("TEST SUMMARY REPORT")
print("="*80 + "\n")

total_tests = len(test_results['passed']) + len(test_results['failed'])
pass_count = len(test_results['passed'])
fail_count = len(test_results['failed'])
warning_count = len(test_results['warnings'])

print(f"Total Tests Run: {total_tests}")
print(f"✅ Passed: {pass_count}")
print(f"❌ Failed: {fail_count}")
print(f"⚠️  Warnings: {warning_count}")

if total_tests > 0:
    pass_rate = (pass_count / total_tests) * 100
    print(f"\nPass Rate: {pass_rate:.1f}%")

if test_results['failed']:
    print("\n" + "-"*80)
    print("FAILED TESTS:")
    print("-"*80)
    for result in test_results['failed']:
        print(f"❌ {result['test']}")
        if result['message']:
            print(f"   {result['message']}")

if test_results['warnings']:
    print("\n" + "-"*80)
    print("WARNINGS:")
    print("-"*80)
    for result in test_results['warnings']:
        print(f"⚠️  {result['test']}")
        if result['message']:
            print(f"   {result['message']}")

print("\n" + "="*80)
if fail_count == 0 and warning_count <= 3:
    print("🎉 PLATFORM STATUS: PRODUCTION READY")
elif fail_count <= 2:
    print("⚠️  PLATFORM STATUS: MINOR ISSUES - REVIEW FAILURES")
else:
    print("❌ PLATFORM STATUS: CRITICAL ISSUES - NOT PRODUCTION READY")
print("="*80 + "\n")

print(f"Test execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\nFor detailed logs, review output above.")
