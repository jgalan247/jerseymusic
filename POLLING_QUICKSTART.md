# Payment Polling - Quick Start

## TL;DR

SumUp webhooks aren't available yet, so we poll the API every 5 minutes to verify payments.

## Setup (Production)

1. **Run migrations:**
   ```bash
   python manage.py migrate payments
   ```

2. **Add to crontab:**
   ```bash
   crontab -e
   ```

   Add this line:
   ```cron
   */5 * * * * cd /var/www/jerseymusic && /var/www/jerseymusic/venv/bin/python manage.py run_payment_polling >> /var/log/payment_polling.log 2>&1
   ```

3. **Update admin email in `payments/polling_service.py`:**
   ```python
   ADMIN_EMAIL = 'your-email@domain.com'
   ```

4. **Test:**
   ```bash
   python manage.py run_payment_polling --verbose
   ```

That's it! Payments will now be verified automatically every 5 minutes.

## How It Works

1. Customer completes payment on SumUp hosted page
2. They're redirected back to your site with status "pending"
3. Every 5 minutes, cron job runs `run_payment_polling` command
4. Command checks all pending payments via SumUp API
5. When payment confirmed:
   - Order marked as completed
   - Tickets generated and emailed
   - Event published (for listing fees)

## Manual Testing

```bash
# Run polling manually
python manage.py run_payment_polling --verbose

# Check logs
tail -f /var/log/payment_polling.log

# Check pending checkouts in Django shell
python manage.py shell
>>> from payments.models import SumUpCheckout
>>> SumUpCheckout.objects.filter(status__in=['pending', 'created'], should_poll=True)
```

## Configuration

### Change polling duration (default: 2 hours)
In `payments/polling_service.py`:
```python
MAX_AGE_HOURS = 3  # Change to 3 hours
```

### Change how often to poll (default: every 5 minutes)
In crontab:
```cron
*/10 * * * *  # Every 10 minutes instead
```

## Troubleshooting

**Polling not running?**
```bash
# Check cron is active
sudo systemctl status cron

# Check for errors
grep CRON /var/log/syslog
```

**Payments stuck?**
```bash
# Run manually to see errors
python manage.py run_payment_polling --verbose

# Check polling logs
grep "ERROR" /var/log/payment_polling.log
```

**Need to force check a specific payment?**
```python
from payments.polling_service import polling_service
from payments.models import SumUpCheckout

checkout = SumUpCheckout.objects.get(payment_id='CHK-XXXXXXXXXX')
result = polling_service._verify_single_checkout(checkout)
print(result)
```

## Important Security Note

The polling system ALWAYS verifies payment amounts server-side before issuing tickets. This prevents fraud even if the frontend is compromised.

---

For complete documentation, see `SUMUP_POLLING_SETUP.md`.
