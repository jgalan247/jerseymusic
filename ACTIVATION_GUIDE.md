# 🚀 Payment Polling System - Activation Guide

## Quick Start (5 Minutes)

### Current Status

✅ **Django-Q is installed** (django-q2 1.8.0)
✅ **Polling schedule is configured** (runs every 5 minutes)
⚠️ **Django-Q cluster needs to be started**

---

## Step-by-Step Activation

### 1. Verify Configuration (2 minutes)

Run the activation script to verify everything is set up correctly:

```bash
cd /Users/josegalan/Documents/jersey_music
source venv/bin/activate
python activate_polling.py
```

This will:
- Check if the polling schedule exists
- Test the polling service
- Show Django-Q cluster status
- Display next steps

---

### 2. Start Django-Q Cluster (Development)

#### Option A: Simple Development Setup

Open **TWO terminal windows**:

**Terminal 1: Django Server**
```bash
cd /Users/josegalan/Documents/jersey_music
source venv/bin/activate
python manage.py runserver
```

**Terminal 2: Django-Q Cluster**
```bash
cd /Users/josegalan/Documents/jersey_music
source venv/bin/activate
python manage.py qcluster
```

**Expected output in Terminal 2:**
```
[Q] INFO Starting a worker...
[Q] INFO Process-1:1 ready for work at 12345
[Q] INFO Process-2:2 ready for work at 12346
[Q] INFO Monitoring at port 8001
```

Keep both terminals running! The polling service will now run automatically every 5 minutes.

---

### 3. Test the System (3 minutes)

#### Manual Test

In a third terminal, run the test script:

```bash
cd /Users/josegalan/Documents/jersey_music
source venv/bin/activate
python test_payment_polling.py
```

This will show:
- Current pending orders
- Recently completed orders
- Django-Q task history
- System health status

#### Manual Polling Trigger

To manually trigger a polling cycle (for testing):

```bash
python manage.py run_payment_polling --verbose
```

---

### 4. Monitor the System

#### Django Admin (Recommended)

1. Visit http://localhost:8000/admin/
2. Navigate to **Django Q** section
3. Check:
   - **Schedules**: http://localhost:8000/admin/django_q/schedule/
   - **Tasks**: http://localhost:8000/admin/django_q/task/

#### Check Logs

```bash
# Django-Q cluster output
tail -f logs/django_q.log

# Payment polling logs (if configured)
tail -f logs/payment_polling.log
```

#### Quick Status Check

```bash
# Check for pending orders
python manage.py shell -c "from orders.models import Order; print(f'Pending: {Order.objects.filter(status=\"pending_verification\").count()}')"

# Check recent tasks
python manage.py shell -c "from django_q.models import Task; from django.utils import timezone; from datetime import timedelta; print(f'Tasks (last hour): {Task.objects.filter(started__gte=timezone.now() - timedelta(hours=1)).count()}')"
```

---

## Production Deployment

### Option 1: Supervisor (Recommended)

**Step 1: Copy Configuration**
```bash
sudo cp supervisor_django_q.conf /etc/supervisor/conf.d/jerseyevents_django_q.conf
```

**Step 2: Update Paths (if needed)**
```bash
sudo nano /etc/supervisor/conf.d/jerseyevents_django_q.conf
# Update paths to match your deployment
```

**Step 3: Activate**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start jerseyevents_django_q
```

**Step 4: Verify**
```bash
sudo supervisorctl status jerseyevents_django_q
# Should show: RUNNING
```

**View Logs:**
```bash
sudo supervisorctl tail -f jerseyevents_django_q
```

**Control Commands:**
```bash
sudo supervisorctl restart jerseyevents_django_q
sudo supervisorctl stop jerseyevents_django_q
```

---

### Option 2: Systemd

**Step 1: Copy Service File**
```bash
sudo cp systemd_django_q.service /etc/systemd/system/jerseyevents-django-q.service
```

**Step 2: Update Configuration**
```bash
sudo nano /etc/systemd/system/jerseyevents-django-q.service
# Update User, Group, and paths
```

**Step 3: Enable and Start**
```bash
sudo systemctl daemon-reload
sudo systemctl enable jerseyevents-django-q
sudo systemctl start jerseyevents-django-q
```

**Step 4: Verify**
```bash
sudo systemctl status jerseyevents-django-q
# Should show: active (running)
```

**View Logs:**
```bash
sudo journalctl -u jerseyevents-django-q -f
```

**Control Commands:**
```bash
sudo systemctl restart jerseyevents-django-q
sudo systemctl stop jerseyevents-django-q
```

---

## End-to-End Testing

### Test Flow

1. **Create a test event** (or use existing event)
2. **Add tickets to cart** as a customer
3. **Complete checkout** with SumUp test card:
   - Card: `4242 4242 4242 4242`
   - CVV: Any 3 digits
   - Expiry: Any future date
4. **Complete payment** at SumUp
5. **Wait 5-10 minutes** for polling to run
6. **Check email** for ticket confirmation
7. **Verify in admin**:
   - Order status changed to 'completed'
   - Tickets were generated
   - Customer received email

### Verify in Django Admin

```bash
# Visit admin
http://localhost:8000/admin/orders/order/

# Check most recent order
# Status should be: Completed
# Is Paid: Yes
# Paid At: [timestamp]
# Tickets: [should see ticket records]
```

---

## Troubleshooting

### Problem: No tickets being sent

**Check 1: Is Django-Q running?**
```bash
ps aux | grep qcluster
# Should see python process running qcluster
```

**Check 2: Is schedule active?**
```bash
python manage.py shell
from django_q.models import Schedule
for s in Schedule.objects.all():
    print(f"{s.name}: repeats={s.repeats}, next_run={s.next_run}")
```

**Check 3: Any recent tasks?**
```bash
python manage.py shell
from django_q.models import Task
from django.utils import timezone
from datetime import timedelta
recent = Task.objects.filter(started__gte=timezone.now() - timedelta(minutes=30))
print(f"Tasks in last 30 min: {recent.count()}")
```

**Fix: Restart Django-Q**
```bash
# Development
# Stop qcluster (Ctrl+C in terminal)
python manage.py qcluster

# Production (Supervisor)
sudo supervisorctl restart jerseyevents_django_q

# Production (Systemd)
sudo systemctl restart jerseyevents-django-q
```

---

### Problem: Polling runs but orders not verified

**Check 1: Pending orders exist?**
```bash
python manage.py shell
from orders.models import Order
pending = Order.objects.filter(status='pending_verification')
print(f"Pending orders: {pending.count()}")
for o in pending[:3]:
    print(f"  {o.order_number}: £{o.total}, age={(timezone.now() - o.created_at).total_seconds()/60:.1f} min")
```

**Check 2: SumUp OAuth tokens valid?**
```bash
python manage.py shell
from accounts.models import User
from django.utils import timezone

# Check artist profiles
artists = User.objects.filter(user_type='artist')
for artist in artists:
    if hasattr(artist, 'artistprofile'):
        profile = artist.artistprofile
        if profile.sumup_access_token:
            expired = profile.sumup_token_expiry < timezone.now() if profile.sumup_token_expiry else False
            print(f"{artist.email}: token_present=True, expired={expired}")
```

**Check 3: Run manual polling with verbose output**
```bash
python manage.py run_payment_polling --verbose
# Check output for errors
```

---

### Problem: Amount mismatch errors

This is a **security feature** - orders are flagged for manual review if payment amount doesn't match order total.

**Check flagged orders:**
```bash
python manage.py shell
from orders.models import Order
flagged = Order.objects.filter(status='requires_manual_review')
for order in flagged:
    print(f"{order.order_number}: {order.payment_notes}")
```

**Manually review** in Django admin:
```bash
http://localhost:8000/admin/orders/order/
# Filter by status: requires_manual_review
```

---

### Problem: Email not being received

**Check 1: Email backend configured?**
```bash
python manage.py shell
from django.conf import settings
print(f"Backend: {settings.EMAIL_BACKEND}")
print(f"Host: {settings.EMAIL_HOST}")
print(f"Port: {settings.EMAIL_PORT}")
```

**Check 2: Send test email**
```bash
python manage.py shell
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'Testing email configuration',
    'noreply@jerseyevents.je',
    ['your-email@example.com'],
    fail_silently=False
)
```

**For MailHog (Development):**
- Visit http://localhost:8025
- Check if emails are appearing there

---

## Monitoring & Alerts

### Admin Email Alerts

The system sends alerts to: `alerts@coderra.je`

**Alert Types:**
- 🟡 **Non-Critical**: Stuck orders, expired orders, email failures
- 🔴 **Critical**: Amount mismatches, missing checkout records

**Verify alerts are working:**
```bash
python manage.py shell
from payments.polling_service import polling_service
polling_service._send_admin_alert("Test Alert", "Testing alert system")
# Check alerts@coderra.je for email
```

### Performance Metrics

**Current capacity:**
- Orders per cycle: 20
- Polling interval: 5 minutes
- Orders per hour: 240
- Orders per day: 5,760

**If you need more capacity:**
1. Increase workers in `events/settings.py`:
   ```python
   Q_CLUSTER = {
       'workers': 4,  # Increase from 2
   }
   ```
2. Increase max orders per cycle in `payments/polling_service.py`:
   ```python
   MAX_ORDERS_PER_CYCLE = 50  # Increase from 20
   ```
3. Reduce polling interval (change schedule to 3 minutes instead of 5)

---

## Quick Reference Commands

### Development

```bash
# Start servers
python manage.py runserver          # Terminal 1
python manage.py qcluster           # Terminal 2

# Test polling
python activate_polling.py          # Verify setup
python test_payment_polling.py     # Run tests
python manage.py run_payment_polling --verbose  # Manual trigger

# Check status
python manage.py shell -c "from django_q.models import Task; print(Task.objects.count())"
```

### Production

```bash
# Supervisor
sudo supervisorctl status jerseyevents_django_q
sudo supervisorctl restart jerseyevents_django_q
sudo supervisorctl tail -f jerseyevents_django_q

# Systemd
sudo systemctl status jerseyevents-django-q
sudo systemctl restart jerseyevents-django-q
sudo journalctl -u jerseyevents-django-q -f

# Logs
tail -f logs/django_q.log
tail -f logs/payment_polling.log
```

---

## Success Checklist

- [ ] Django-Q installed (v1.8.0 or higher)
- [ ] Polling schedule created (every 5 minutes)
- [ ] Django-Q cluster running
- [ ] Test payment completed successfully
- [ ] Tickets received via email within 10 minutes
- [ ] Order status changed to 'completed' in admin
- [ ] Admin alerts working (test email sent)
- [ ] Logs directory created and writable
- [ ] Production deployment configured (supervisor/systemd)
- [ ] Monitoring set up (admin panels accessible)

---

## Support & Documentation

**Files Created:**
- `activate_polling.py` - Activation script
- `test_payment_polling.py` - Testing script
- `supervisor_django_q.conf` - Supervisor configuration
- `systemd_django_q.service` - Systemd service file
- `ACTIVATION_GUIDE.md` - This guide

**Related Documentation:**
- `PAYMENT_POLLING_STRATEGY.md` - Detailed polling strategy
- `DEPLOYMENT_GUIDE_POLLING.md` - Production deployment guide
- `payments/polling_service.py` - Source code with inline docs

**Django Admin URLs:**
- Schedules: http://localhost:8000/admin/django_q/schedule/
- Tasks: http://localhost:8000/admin/django_q/task/
- Orders: http://localhost:8000/admin/orders/order/
- Checkouts: http://localhost:8000/admin/payments/sumupcheckout/

---

## Next Steps

1. **Right Now**: Run `python activate_polling.py` to verify setup
2. **In 5 Minutes**: Start Django-Q cluster with `python manage.py qcluster`
3. **In 10 Minutes**: Test with a real payment
4. **In 30 Minutes**: Deploy to production with supervisor/systemd
5. **Tomorrow**: Monitor for 24 hours and verify everything works

**Your payment polling system is ready to go! 🚀**
