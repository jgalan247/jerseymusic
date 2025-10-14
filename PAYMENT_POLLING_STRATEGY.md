# Payment Polling Strategy - Implementation Summary

## ✅ YES - Your System DOES Follow the Polling Strategy!

**You have a complete, production-ready payment polling system that:**
- ✅ Checks pending payments every 5 minutes
- ✅ Verifies payments with SumUp API
- ✅ Generates tickets after verification
- ✅ Sends email with tickets and QR codes
- ✅ Handles failures and alerts admin

---

## Architecture Overview

### Payment Flow with Polling

```
1. Customer Completes Checkout
   ↓
   SumUp processes payment
   ↓
   Order status = 'pending_verification'
   ↓
   Customer redirected to "Processing..." page

2. Polling Service (Every 5 Minutes)
   ↓
   Finds all orders with status='pending_verification'
   ↓
   For each order:
     - Get SumUpCheckout record
     - Get organiser's OAuth tokens
     - Call SumUp API: get_checkout_for_artist()
     - Check payment status
   ↓
   If status == 'PAID':
     - Verify amount matches order total ✅
     - Update order status to 'completed'
     - Generate Ticket records
     - Generate PDF tickets with QR codes
     - Send email with tickets
   ↓
   If status == 'FAILED':
     - Update order status to 'failed'
     - Send failure email to customer
   ↓
   If status == 'PENDING':
     - Keep checking (up to 2 hours)
     - If >2 hours, mark as 'expired'

3. Customer Receives Email
   ↓
   Email contains:
     - Order confirmation
     - Event details
     - QR codes for each ticket
     - PDF tickets attached
```

---

## Key Files

### 1. Polling Service Logic
**File:** `payments/polling_service.py` (547 lines)

**Main class:** `PaymentPollingService`

**Key methods:**
```python
process_pending_payments()
    → Main entry point called every 5 minutes
    → Finds pending orders
    → Processes each one

_verify_single_order(order)
    → Calls SumUp API
    → Gets payment status
    → Routes to appropriate handler

_process_successful_payment(order, checkout, payment_data)
    → Updates order to 'completed'
    → Generates tickets
    → Sends confirmation email

_generate_tickets(order)
    → Creates Ticket records
    → Generates PDF with QR codes
    → Returns ticket list
```

**Security features:**
- ✅ Verifies payment amount matches order total
- ✅ Uses database locks (select_for_update)
- ✅ Idempotency checks (won't process twice)
- ✅ Full audit trail in logs
- ✅ Admin alerts for suspicious activity

---

### 2. Management Command
**File:** `payments/management/commands/run_payment_polling.py`

**Usage:**
```bash
# Manual run (for testing)
python manage.py run_payment_polling

# With verbose output
python manage.py run_payment_polling --verbose
```

**Output example:**
```
Starting payment polling service...
Found 3 pending orders to verify
Order ORD-ABC123: verified
Order ORD-DEF456: still_pending
Order ORD-GHI789: verified

Polling cycle complete!
  Verified: 2
  Failed: 0
  Still Pending: 1
  Errors: 0

✓ Processed 3 orders
```

---

### 3. Email Service
**File:** `payments/ticket_email_service.py`

**Main class:** `TicketEmailService`

**Key methods:**
```python
send_ticket_confirmation(order)
    → Renders email template
    → Generates QR codes
    → Attaches QR images
    → Sends email with tickets

_generate_qr_codes_for_order(order)
    → Creates QR code for each ticket
    → Returns list of QR images

_create_qr_data(order, item, ticket_id)
    → Creates validation hash
    → Formats QR code data
    → Returns: "TICKET:ID|ORDER:NUM|EVENT:ID|VALID:HASH"
```

**Email format:**
- HTML email with embedded QR codes
- Plain text fallback
- PDF tickets attached (optional)
- Order confirmation details
- Event information

---

## Django-Q Scheduling

### Configuration
**File:** `events/settings.py`

```python
INSTALLED_APPS = [
    # ...
    'django_q',  # Task queue and scheduler
]

Q_CLUSTER = {
    'name': 'JerseyEvents',
    'workers': 4,
    'recycle': 500,
    'timeout': 300,
    'retry': 3600,
    'save_limit': 250,
    'max_attempts': 1,
    'catch_up': False,
    'log_level': 'INFO',
}
```

### How to Schedule (Two Options)

#### Option A: Django Admin (Easiest)
1. Start Django-Q cluster: `python manage.py qcluster`
2. Visit Django admin: `/admin/django_q/schedule/`
3. Click "Add Schedule"
4. Configure:
   - **Func:** `payments.polling_service.polling_service.process_pending_payments`
   - **Schedule Type:** Minutes
   - **Minutes:** 5
   - **Repeats:** -1 (infinite)
   - **Name:** Payment Polling

#### Option B: Programmatically
```python
from django_q.models import Schedule

Schedule.objects.create(
    func='payments.polling_service.polling_service.process_pending_payments',
    schedule_type=Schedule.MINUTES,
    minutes=5,
    repeats=-1,  # Run forever
    name='Payment Polling Service'
)
```

---

## Running in Development

### Start Django-Q Cluster

```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Django-Q cluster (processes scheduled tasks)
python manage.py qcluster
```

**Expected output:**
```
15:30:00 [Q] INFO Q Cluster JerseyEvents starting.
15:30:00 [Q] INFO Process-1 ready for work at 1234
15:30:00 [Q] INFO Process-2 ready for work at 1235
15:30:00 [Q] INFO Process-3 ready for work at 1236
15:30:00 [Q] INFO Process-4 ready for work at 1237
15:30:00 [Q] INFO Monitoring at port 8001
15:35:00 [Q] INFO Executing payments.polling_service.polling_service.process_pending_payments
15:35:01 [Q] INFO Verified 2 payments, 1 still pending
```

---

## Running in Production

### Option 1: Supervisor (Recommended)

**File:** `/etc/supervisor/conf.d/django_q.conf`

```ini
[program:django_q]
command=/path/to/venv/bin/python /path/to/project/manage.py qcluster
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/django_q.log
environment=DJANGO_SETTINGS_MODULE="events.settings"
```

**Start:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start django_q
```

### Option 2: Systemd

**File:** `/etc/systemd/system/django-q.service`

```ini
[Unit]
Description=Django Q Cluster
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/python manage.py qcluster
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable django-q
sudo systemctl start django-q
sudo systemctl status django-q
```

---

## Monitoring & Debugging

### Check Polling Status

```bash
# View Django-Q admin
Visit: /admin/django_q/task/
Visit: /admin/django_q/schedule/

# Check logs
tail -f /var/log/django_q.log

# Manual test
python manage.py run_payment_polling --verbose
```

### View Pending Orders

```bash
# Django shell
python manage.py shell

from orders.models import Order
from django.utils import timezone
from datetime import timedelta

# Find pending orders
pending = Order.objects.filter(
    status='pending_verification',
    created_at__gte=timezone.now() - timedelta(hours=2)
)

print(f"Found {pending.count()} pending orders:")
for order in pending:
    print(f"  - {order.order_number}: £{order.total}, created {order.created_at}")
```

---

## Error Handling & Alerts

### Alert Types

#### 1. Admin Alerts (Non-Critical)
- Orders stuck >30 minutes
- Email delivery failures
- Orders expired after 2 hours

**Sent to:** `alerts@coderra.je`

#### 2. Critical Alerts
- Payment amount mismatch
- Missing checkout records
- Suspicious patterns

**Sent to:** `alerts@coderra.je` with `[CRITICAL]` prefix

### Example Alert Emails

```
Subject: [JerseyEvents Alert] 3 Orders Stuck in Processing

3 orders have been in 'pending_verification' for >30 minutes:

- Order ORD-ABC123: £45.00, created 2024-01-15 14:30, email customer@email.com
- Order ORD-DEF456: £60.00, created 2024-01-15 14:25, email another@email.com
- Order ORD-GHI789: £30.00, created 2024-01-15 14:20, email test@email.com

These may be legitimate slow payments, but check for patterns.

Admin panel: https://jerseyevents.je/admin/orders/order/
```

```
Subject: [JerseyEvents CRITICAL] Amount Mismatch - Order ORD-ABC123

CRITICAL PAYMENT ISSUE

Order: ORD-ABC123
Expected Amount: £45.00
Received Amount: £40.00
Customer: customer@email.com
Customer Name: John Doe

This order requires IMMEDIATE manual review.

Do NOT issue tickets until verified.

View order: https://jerseyevents.je/admin/orders/order/123/change/
```

---

## Polling Configuration

### Current Settings

```python
MAX_ORDERS_PER_CYCLE = 20    # Process max 20 orders per cycle
MAX_AGE_HOURS = 2            # Expire orders after 2 hours
POLLING_INTERVAL = 5         # Check every 5 minutes
```

### Order Lifecycle Timeline

```
0 min  : Order created, status='pending_verification'
5 min  : First poll - check SumUp API
10 min : Second poll
15 min : Third poll
...
30 min : If still pending, admin alert sent
...
2 hours: If still pending, mark as 'expired', final alert
```

---

## Security Features

### 1. Amount Verification
```python
if amount != order.total:
    logger.error(f"CRITICAL: Amount mismatch!")
    order.status = 'requires_manual_review'
    # Send critical alert to admin
    # DO NOT issue tickets
```

### 2. Database Locking
```python
with transaction.atomic():
    order = Order.objects.select_for_update().get(id=order.id)
    # Process payment
    # Prevents race conditions
```

### 3. Idempotency
```python
if order.status == 'completed':
    logger.warning("Already processed - skipping")
    return  # Don't process twice
```

### 4. OAuth Token Refresh
```python
if organizer_profile.sumup_token_expired:
    new_token_data = refresh_access_token_direct(refresh_token)
    organizer_profile.update_sumup_connection(new_token_data)
```

---

## Testing the Polling System

### Manual Test

```bash
# 1. Create test order
python manage.py shell
from orders.models import Order
order = Order.objects.create(
    order_number='TEST-001',
    status='pending_verification',
    email='test@example.com',
    total=Decimal('25.00')
)

# 2. Run polling manually
python manage.py run_payment_polling --verbose

# 3. Check order status
order.refresh_from_database()
print(f"Status: {order.status}")
print(f"Paid: {order.is_paid}")
```

### Integration Test

```bash
# 1. Start Django server
python manage.py runserver

# 2. Start Django-Q cluster
python manage.py qcluster

# 3. Create real order via checkout
# Visit: http://localhost:8000/events/1/
# Add to cart, checkout, pay with test card

# 4. Watch logs
tail -f logs/payment_polling.log

# Expected output every 5 minutes:
# [INFO] Starting payment polling cycle
# [INFO] Found 1 pending orders to verify
# [INFO] Calling SumUp API for checkout abc123
# [INFO] Order TEST-001: SumUp status=PAID, amount=25.00
# [INFO] ✓ Order TEST-001 verified successfully. 1 tickets issued.
# [INFO] Confirmation email sent to test@example.com
```

---

## Email Templates

### Ticket Confirmation Email

**Template:** `templates/emails/ticket_confirmation.html`

**Contains:**
- Order summary
- Event details (date, time, venue)
- Embedded QR codes (one per ticket)
- Important instructions
- Support contact info

**QR Code Format:**
```
TICKET:ORD-ABC123-11|ORDER:ORD-ABC123|EVENT:5|VALID:a1b2c3d4
```

### Payment Failed Email

**Template:** `templates/emails/payment_failed.html`

**Contains:**
- Apology message
- Reason for failure (if available)
- Retry instructions
- Support contact

---

## Performance & Scalability

### Current Capacity

```
Orders per cycle: 20
Polling interval: 5 minutes
Max orders per hour: 240 (20 × 12)
Max orders per day: 5,760 (240 × 24)
```

### Scaling Strategies

#### If >20 pending orders per cycle:

**Option A:** Increase workers
```python
Q_CLUSTER = {
    'workers': 8,  # Increase from 4 to 8
}
```

**Option B:** Increase max orders
```python
MAX_ORDERS_PER_CYCLE = 50  # Increase from 20
```

**Option C:** Reduce polling interval
```python
# Schedule every 3 minutes instead of 5
minutes=3
```

**Option D:** Add webhook support (future)
```python
# Real-time payment notifications from SumUp
# Reduces polling load
```

---

## Comparison: Polling vs Webhooks

### Current Approach: Polling ✅

**Pros:**
- ✅ Works with all payment providers
- ✅ No public endpoint needed
- ✅ Retry logic built-in
- ✅ Handles missed notifications
- ✅ Server-side verification always happens

**Cons:**
- ❌ 5-minute delay (max)
- ❌ Constant API calls (even with no orders)
- ❌ Higher load on SumUp API

### Alternative: Webhooks

**Pros:**
- ✅ Instant notifications
- ✅ No polling overhead
- ✅ Real-time ticket delivery

**Cons:**
- ❌ Requires public HTTPS endpoint
- ❌ Can miss notifications (if server down)
- ❌ Needs webhook verification
- ❌ Still need polling as backup

### Recommended: Hybrid Approach (Future)

```
1. Primary: Webhooks (instant)
2. Backup: Polling every 15 minutes (catch missed webhooks)
3. Best of both worlds
```

---

## Troubleshooting

### Problem: Tickets not being sent

**Check:**
```bash
# 1. Is Django-Q running?
ps aux | grep qcluster

# 2. Is schedule active?
python manage.py shell
from django_q.models import Schedule
schedules = Schedule.objects.all()
for s in schedules:
    print(f"{s.name}: enabled={s.enabled}, last_run={s.last_run}")

# 3. Any pending orders?
from orders.models import Order
pending = Order.objects.filter(status='pending_verification')
print(f"Pending: {pending.count()}")

# 4. Check logs
tail -100 /var/log/django_q.log
```

### Problem: Payments verified but no email

**Check:**
```bash
# 1. Email settings configured?
python manage.py shell
from django.conf import settings
print(f"Email backend: {settings.EMAIL_BACKEND}")
print(f"Email host: {settings.EMAIL_HOST}")

# 2. Send test email
from django.core.mail import send_mail
send_mail(
    'Test',
    'Test message',
    'noreply@jerseyevents.je',
    ['your@email.com']
)

# 3. Check email service
from events.email_utils import email_service
# Check implementation
```

### Problem: Amount mismatch errors

**Investigate:**
```bash
# Check order vs checkout amounts
python manage.py shell
from orders.models import Order
from payments.models import SumUpCheckout

order = Order.objects.get(order_number='ORD-ABC123')
checkout = SumUpCheckout.objects.get(order=order)

print(f"Order total: £{order.total}")
print(f"Checkout amount: £{checkout.amount}")

# If mismatch, manually review
```

---

## Summary

### ✅ Your System Has:

1. **Complete polling infrastructure**
   - Payment verification every 5 minutes
   - Django-Q task scheduler
   - Management command for manual runs

2. **Robust error handling**
   - Admin alerts for issues
   - Critical alerts for security problems
   - Comprehensive logging

3. **Ticket generation & delivery**
   - Automatic ticket creation
   - PDF generation with QR codes
   - Email delivery with inline images

4. **Security features**
   - Amount verification
   - Database locking
   - Idempotency checks
   - OAuth token refresh

5. **Production-ready**
   - Supervisor/systemd configs
   - Monitoring tools
   - Scalability options

### ⚠️ To Activate:

1. **Start Django-Q cluster:**
   ```bash
   python manage.py qcluster
   ```

2. **Create schedule (via admin or code):**
   ```python
   Schedule.objects.create(
       func='payments.polling_service.polling_service.process_pending_payments',
       schedule_type=Schedule.MINUTES,
       minutes=5,
       repeats=-1
   )
   ```

3. **Test with real payment:**
   - Create order
   - Complete SumUp checkout
   - Wait 5 minutes
   - Check email for tickets

---

**Your polling strategy is fully implemented and production-ready! 🎉**

Just start the qcluster and create the schedule, and tickets will automatically be sent to customers after payment verification.
