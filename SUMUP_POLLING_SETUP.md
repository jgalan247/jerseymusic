# SumUp Payment Polling System Setup

## Overview

Since SumUp webhooks are not yet available (as confirmed by SumUp support), we've implemented a robust polling system that periodically checks payment status via the SumUp API.

**Polling interval:** Every 5 minutes (configurable)
**Max polling duration:** 2 hours per payment (configurable)
**Supports:** Ticket orders and listing fee payments

## Architecture

### Database Model (SumUpCheckout)

The `SumUpCheckout` model tracks all payment checkouts with polling-specific fields:

- `should_poll`: Boolean flag to enable/disable polling for this checkout
- `polling_started_at`: Timestamp when polling began
- `last_polled_at`: Timestamp of last status check
- `poll_count`: Number of times we've checked this checkout
- `max_poll_duration_minutes`: Maximum time to keep polling (default: 120 minutes)

### Polling Service (`payments/polling_service.py`)

The `PaymentPollingService` class handles:
- Finding checkouts that need polling
- Calling SumUp API to check status
- Processing successful payments (issuing tickets, publishing events)
- Handling failed/expired payments
- Amount verification (security critical)
- Email notifications
- Admin alerts for issues

### Management Command (`run_payment_polling`)

Django management command that can be:
- Run manually: `python manage.py run_payment_polling --verbose`
- Scheduled via cron
- Scheduled via Django-Q or Celery
- Run as a background service

## Setup Instructions

### 1. Run Database Migrations

```bash
python manage.py migrate payments
```

This adds the polling fields to the `SumUpCheckout` model.

### 2. Choose Scheduling Method

#### Option A: Cron (Recommended for Production)

Add to your crontab (`crontab -e`):

```cron
# Run payment polling every 5 minutes
*/5 * * * * cd /path/to/jerseymusic && /path/to/venv/bin/python manage.py run_payment_polling >> /var/log/payment_polling.log 2>&1
```

**With verbose output:**
```cron
*/5 * * * * cd /path/to/jerseymusic && /path/to/venv/bin/python manage.py run_payment_polling --verbose >> /var/log/payment_polling.log 2>&1
```

**Production example (systemd timer alternative):**
```bash
# Create service file: /etc/systemd/system/payment-polling.service
[Unit]
Description=SumUp Payment Polling Service
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/var/www/jerseymusic
Environment="DJANGO_SETTINGS_MODULE=events.settings"
ExecStart=/var/www/jerseymusic/venv/bin/python manage.py run_payment_polling

[Install]
WantedBy=multi-user.target

# Create timer file: /etc/systemd/system/payment-polling.timer
[Unit]
Description=Run Payment Polling every 5 minutes
Requires=payment-polling.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target

# Enable and start
sudo systemctl enable payment-polling.timer
sudo systemctl start payment-polling.timer
```

#### Option B: Django-Q (if already using it)

In your Django settings, add scheduled task:

```python
Q_CLUSTER = {
    'name': 'Jersey Music',
    'workers': 4,
    'timeout': 300,
    'retry': 360,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
    'schedule': [
        {
            'func': 'payments.polling_service.polling_service.process_pending_payments',
            'schedule_type': 'I',  # Interval
            'minutes': 5,
            'repeats': -1  # Repeat forever
        },
    ]
}
```

Start Django-Q cluster:
```bash
python manage.py qcluster
```

#### Option C: Celery Beat (if using Celery)

In `celery.py`:

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('jerseymusic')

app.conf.beat_schedule = {
    'poll-payments-every-5-minutes': {
        'task': 'payments.tasks.poll_payments',
        'schedule': crontab(minute='*/5'),
    },
}
```

Create `payments/tasks.py`:

```python
from celery import shared_task
from payments.polling_service import polling_service
import logging

logger = logging.getLogger(__name__)

@shared_task
def poll_payments():
    """Celery task to poll payment status."""
    try:
        stats = polling_service.process_pending_payments()
        logger.info(f"Payment polling complete: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Payment polling failed: {e}", exc_info=True)
        raise
```

### 3. Configure Logging

Add to your Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'polling_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/jerseymusic/payment_polling.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'payments.polling_service': {
            'handlers': ['polling_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 4. Configure Email Alerts

Ensure admin email is set in `payments/polling_service.py`:

```python
class PaymentPollingService:
    ADMIN_EMAIL = 'alerts@coderra.je'  # Update this!
```

Or override via environment variable in your settings:

```python
# In settings.py
PAYMENT_ALERT_EMAIL = os.getenv('PAYMENT_ALERT_EMAIL', 'alerts@coderra.je')

# In polling_service.py
from django.conf import settings
ADMIN_EMAIL = getattr(settings, 'PAYMENT_ALERT_EMAIL', 'alerts@coderra.je')
```

### 5. Test the System

#### Manual test:
```bash
python manage.py run_payment_polling --verbose
```

#### Create a test payment:
1. Go through checkout flow
2. Complete payment on SumUp hosted page
3. Wait 5 minutes (or run polling manually)
4. Check that order status updates to 'completed'
5. Verify tickets were generated
6. Confirm email was sent

#### Check logs:
```bash
tail -f /var/log/jerseymusic/payment_polling.log
```

## Configuration Options

### Polling Duration

To change how long payments are polled before expiring:

**Per-checkout** (when creating checkout):
```python
checkout = SumUpCheckout.objects.create(
    # ... other fields ...
    max_poll_duration_minutes=180,  # 3 hours instead of default 2
)
```

**Globally** (in `polling_service.py`):
```python
class PaymentPollingService:
    MAX_AGE_HOURS = 3  # Change from 2 to 3 hours
```

### Polling Interval

Change cron schedule:
- Every 3 minutes: `*/3 * * * *`
- Every 10 minutes: `*/10 * * * *`
- Every minute (not recommended): `* * * * *`

### Disable Polling for Specific Checkout

```python
checkout.should_poll = False
checkout.save()
```

Or programmatically:
```python
checkout.stop_polling("Reason for stopping")
```

## Monitoring

### Check Polling Status

Django admin interface shows:
- `should_poll`: Whether polling is active
- `poll_count`: How many times checked
- `last_polled_at`: Last check timestamp
- `polling_started_at`: When polling began

### Manual Status Check

Check a specific checkout:
```python
from payments.models import SumUpCheckout
checkout = SumUpCheckout.objects.get(payment_id='CHK-XXXXXXXXXX')
print(f"Needs polling: {checkout.needs_polling}")
print(f"Poll count: {checkout.poll_count}")
print(f"Elapsed: {checkout.polling_elapsed_minutes} minutes")
```

### View Pending Checkouts

```python
from payments.models import SumUpCheckout
pending = SumUpCheckout.objects.filter(
    status__in=['created', 'pending'],
    should_poll=True
)
for checkout in pending:
    print(f"{checkout.payment_id}: {checkout.poll_count} polls, {checkout.polling_elapsed_minutes:.1f} mins")
```

## Troubleshooting

### Polling Not Running

1. **Check cron is active:**
   ```bash
   sudo systemctl status cron
   ```

2. **Check cron logs:**
   ```bash
   grep CRON /var/log/syslog
   ```

3. **Run manually to check for errors:**
   ```bash
   python manage.py run_payment_polling --verbose
   ```

### Payments Stuck in Pending

1. **Check SumUp API is accessible:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" https://api.sumup.com/v0.1/me
   ```

2. **Check polling logs:**
   ```bash
   grep "ERROR" /var/log/jerseymusic/payment_polling.log
   ```

3. **Manually check payment status:**
   ```python
   from payments import sumup
   status = sumup.get_checkout_status('CHECKOUT_ID')
   print(status)
   ```

### Email Alerts Not Sending

1. **Check email settings in Django settings**
2. **Test email configuration:**
   ```bash
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```

3. **Check email logs:**
   ```bash
   grep "email" /var/log/jerseymusic/payment_polling.log
   ```

## Security Considerations

### Amount Verification

The polling system ALWAYS verifies payment amounts match expected amounts:

```python
if amount != checkout.amount:
    # CRITICAL ALERT - Potential fraud attempt
    self._handle_checkout_amount_mismatch(checkout, amount)
```

This prevents:
- Payment amount manipulation
- Frontend tampering
- Man-in-the-middle attacks

### Race Condition Prevention

Uses database locks to prevent duplicate ticket issuance:

```python
with transaction.atomic():
    order = Order.objects.select_for_update().get(id=order.id)
    # ... process payment
```

### Idempotency

Double-checks order status before processing:

```python
if order.status == 'completed':
    logger.warning(f"Order already completed - skipping")
    return
```

## Performance Considerations

### Database Indexes

Migration adds index for efficient polling queries:

```python
models.Index(fields=['status', 'should_poll', 'last_polled_at'])
```

### Query Optimization

Uses `select_related()` to minimize database queries:

```python
pending_checkouts = SumUpCheckout.objects.filter(
    ...
).select_related('order', 'customer')
```

### Rate Limiting

Default limit: 20 checkouts per cycle (prevents API rate limits)

To change:
```python
class PaymentPollingService:
    MAX_ORDERS_PER_CYCLE = 50  # Increase if needed
```

## Migration to Webhooks

When SumUp webhooks become available:

1. **Keep polling as fallback:**
   - Webhooks may fail (network issues, downtime)
   - Polling provides redundancy

2. **Reduce polling frequency:**
   - Change to every 15-30 minutes instead of 5
   - Primary verification via webhook
   - Polling catches missed webhooks

3. **Implement webhook handler:**
   ```python
   @csrf_exempt
   def sumup_webhook(request):
       # Verify signature (when x-payload-signature is available)
       # Process payment status update
       # Update checkout status
       # Disable polling for this checkout
   ```

4. **Gradual transition:**
   - Enable webhooks
   - Monitor both systems
   - Reduce polling frequency gradually
   - Keep polling for legacy payments

## Support

For issues or questions:
- Check logs: `/var/log/jerseymusic/payment_polling.log`
- Review SumUp API docs: https://developer.sumup.com/
- Contact platform admin: alerts@coderra.je

---

**Implementation Date:** 2025-11-05
**Last Updated:** 2025-11-05
**Version:** 1.0
**Status:** Production Ready
