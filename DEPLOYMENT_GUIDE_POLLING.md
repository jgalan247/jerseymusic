# Payment Polling System - Deployment Guide

## 🎯 Overview

This guide provides step-by-step instructions to deploy the polling-based payment verification system for the Jersey Events ticketing platform. This replaces webhook-based verification with a secure, server-side polling approach.

## 📋 Prerequisites

- Django application deployed on Digital Ocean
- PostgreSQL database configured
- SumUp OAuth credentials configured for event organizers
- Email sending configured (alerts@coderra.je must receive emails)
- Python 3.8+ and virtual environment

## 🚀 Deployment Steps

### Step 1: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # or: source /path/to/venv/bin/activate

# Install django-q
pip install django-q==1.3.9

# Verify installation
pip list | grep django-q
```

### Step 2: Run Database Migrations

```bash
# Create migration for new order statuses
python manage.py makemigrations orders

# Apply migrations
python manage.py migrate

# Verify migration applied
python manage.py showmigrations orders
```

Expected output: You should see a new migration for the updated ORDER_STATUS_CHOICES.

### Step 3: Create Django-Q Schedule

Run Django shell to create the scheduled task:

```bash
python manage.py shell
```

In the shell:

```python
from django_q.models import Schedule

# Create the payment polling schedule
schedule = Schedule.objects.create(
    name='Payment Polling - Every 5 Minutes',
    func='payments.polling_service.polling_service.process_pending_payments',
    schedule_type='I',  # Interval-based
    minutes=5,
    repeats=-1  # Repeat forever
)

print(f"✓ Schedule created: {schedule.name}")
print(f"  ID: {schedule.id}")
print(f"  Next run: {schedule.next_run}")

# Verify schedule
Schedule.objects.filter(name__icontains='Payment Polling')

# Exit
exit()
```

### Step 4: Start Django-Q Cluster

#### Option A: Manual Start (Testing)

```bash
# Start cluster in foreground for testing
python manage.py qcluster

# You should see:
# [Q] INFO Starting a worker...
# [Q] INFO Process-1 ready for work
```

Leave this running and test payment flow in another terminal.

#### Option B: Production with Supervisor (Recommended)

Create supervisor configuration:

```bash
sudo nano /etc/supervisor/conf.d/jerseyevents_qcluster.conf
```

Add configuration:

```ini
[program:jerseyevents_qcluster]
command=/home/jerseyevents/venv/bin/python /home/jerseyevents/jersey_music/manage.py qcluster
directory=/home/jerseyevents/jersey_music
user=jerseyevents
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/jerseyevents/logs/qcluster.log
environment=PATH="/home/jerseyevents/venv/bin"
```

Update and start supervisor:

```bash
# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start qcluster
sudo supervisorctl start jerseyevents_qcluster

# Check status
sudo supervisorctl status jerseyevents_qcluster

# View logs
tail -f /home/jerseyevents/logs/qcluster.log
```

#### Option C: Systemd Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/jerseyevents-qcluster.service
```

Add configuration:

```ini
[Unit]
Description=Jersey Events Django-Q Cluster
After=network.target postgresql.service

[Service]
Type=simple
User=jerseyevents
Group=www-data
WorkingDirectory=/home/jerseyevents/jersey_music
Environment="PATH=/home/jerseyevents/venv/bin"
ExecStart=/home/jerseyevents/venv/bin/python manage.py qcluster
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable jerseyevents-qcluster

# Start service
sudo systemctl start jerseyevents-qcluster

# Check status
sudo systemctl status jerseyevents-qcluster

# View logs
sudo journalctl -u jerseyevents-qcluster -f
```

### Step 5: Verify Configuration

Check Django-Q admin panel:

1. Go to: `https://your-domain.com/admin/django_q/`
2. Verify:
   - **Schedules**: Should show "Payment Polling - Every 5 Minutes"
   - **Successful tasks**: Should increment every 5 minutes
   - **Failed tasks**: Should be 0 (or investigate failures)

### Step 6: Test Payment Flow

#### Test 1: Successful Payment

1. Add event to cart
2. Proceed to checkout
3. Complete payment with test card: `5555 4444 3333 1111` (CVC: any 3 digits)
4. You should see "Processing your payment..." page
5. Wait 5-10 minutes
6. Check order in Django admin - should be 'completed'
7. Check email for confirmation with tickets

#### Test 2: Failed Payment

1. Use declining test card: `4000 0000 0000 0002`
2. Payment should fail
3. Wait 5-10 minutes
4. Check order status - should be 'failed'
5. Customer should receive failure email

#### Test 3: Expired Order

1. Create a test order manually in Django admin
2. Set status to 'pending_verification'
3. Set created_at to 3 hours ago
4. Wait for next polling cycle
5. Order should be marked as 'expired'
6. Admin should receive alert email at alerts@coderra.je

### Step 7: Monitor Logs

```bash
# Polling service logs
tail -f logs/payment_polling.log

# Django-Q cluster logs
tail -f /var/log/supervisor/jerseyevents_qcluster.log
# OR
sudo journalctl -u jerseyevents-qcluster -f

# Check for errors
grep ERROR logs/payment_polling.log
grep CRITICAL logs/payment_polling.log
```

### Step 8: Verify Admin Alerts

1. Check that alerts@coderra.je email is configured
2. Test admin alerts:
   ```bash
   python manage.py shell
   ```
   ```python
   from payments.polling_service import polling_service

   # Send test alert
   polling_service._send_admin_alert(
       subject="Test Alert",
       message="This is a test alert from polling system"
   )
   ```
3. Check alerts@coderra.je inbox

## 🔍 Troubleshooting

### Issue: Django-Q not processing tasks

**Check:**
```bash
# Verify qcluster is running
ps aux | grep qcluster

# Check schedule exists
python manage.py shell
>>> from django_q.models import Schedule
>>> Schedule.objects.all()

# Check for failed tasks in admin panel
```

**Solution:**
```bash
# Restart qcluster
sudo supervisorctl restart jerseyevents_qcluster
# OR
sudo systemctl restart jerseyevents-qcluster
```

### Issue: Orders stuck in 'pending_verification'

**Check:**
1. Is qcluster running? (`ps aux | grep qcluster`)
2. Are there errors in logs? (`tail -f logs/payment_polling.log`)
3. Is SumUp API accessible? (test from server: `curl https://api.sumup.com`)
4. Are OAuth tokens valid?

**Solution:**
```bash
# Manual trigger
python manage.py run_payment_polling --verbose

# Check specific order
python manage.py shell
>>> from orders.models import Order
>>> order = Order.objects.get(order_number='JE-XXXXXXXX')
>>> order.status
>>> order.payment_notes
```

### Issue: No emails being sent

**Check:**
1. Email configuration in settings.py
2. Test email sending:
   ```python
   from django.core.mail import send_mail
   send_mail(
       'Test',
       'Test message',
       'noreply@coderra.je',
       ['alerts@coderra.je']
   )
   ```

### Issue: Amount mismatch errors

**Symptom:** Orders marked as 'requires_manual_review'

**Action:**
1. Check admin email for CRITICAL alert
2. Review order in Django admin
3. Verify SumUp dashboard for actual payment amount
4. Manually verify and complete if legitimate
5. Investigate if potential fraud attempt

## 📊 Monitoring Checklist

Daily monitoring tasks:

- [ ] Check Django-Q admin panel - tasks should be running every 5 minutes
- [ ] Review orders in 'pending_verification' status (>30 min old = investigate)
- [ ] Check alerts@coderra.je for admin alerts
- [ ] Review logs for errors: `grep ERROR logs/payment_polling.log`
- [ ] Verify qcluster is running: `supervisorctl status jerseyevents_qcluster`

Weekly tasks:

- [ ] Review 'expired' and 'requires_manual_review' orders
- [ ] Check Django-Q successful task rate (should be >95%)
- [ ] Review payment verification times (most should be <10 minutes)

## 🔐 Security Checklist

- [x] All payment amounts validated server-side before ticket issuance
- [x] Database locks prevent race conditions
- [x] Idempotency checks prevent duplicate ticket issuance
- [x] Admin alerts for suspicious activity
- [x] Comprehensive audit logging
- [x] OAuth token refresh handled automatically
- [x] Rate limiting (20 orders per cycle max)

## 📝 Post-Deployment Verification

Run through this checklist after deployment:

1. **Django-Q Running**
   ```bash
   sudo supervisorctl status jerseyevents_qcluster
   # OR
   sudo systemctl status jerseyevents-qcluster
   ```
   ✅ Status should be "RUNNING"

2. **Schedule Active**
   - Visit `/admin/django_q/schedule/`
   - ✅ Should see "Payment Polling" schedule
   - ✅ "Next run" should be within 5 minutes

3. **Test Payment Flow**
   - Make test purchase with card: `5555 4444 3333 1111`
   - ✅ Should redirect to "Processing" page
   - ✅ Within 10 minutes: order status = 'completed'
   - ✅ Email received with ticket PDFs

4. **Admin Alerts Working**
   - ✅ alerts@coderra.je receives test alert

5. **Logs Working**
   ```bash
   tail -n 50 logs/payment_polling.log
   ```
   ✅ Should see polling cycle entries every 5 minutes

## 🆘 Rollback Plan

If polling system has critical issues:

1. **Stop qcluster immediately:**
   ```bash
   sudo supervisorctl stop jerseyevents_qcluster
   # OR
   sudo systemctl stop jerseyevents-qcluster
   ```

2. **Disable schedule:**
   ```python
   from django_q.models import Schedule
   Schedule.objects.filter(name__icontains='Payment Polling').update(repeats=0)
   ```

3. **Manually process pending orders:**
   - Review all 'pending_verification' orders in admin
   - Check SumUp dashboard for actual payment status
   - Manually mark as 'completed' or 'failed' as appropriate

4. **Contact support:** support@digitalocean.com

## 📞 Support Contacts

- **Developer:** [Your contact info]
- **Digital Ocean Support:** support@digitalocean.com
- **SumUp Support:** developers@sumup.com
- **Admin Email:** alerts@coderra.je

## 📚 Additional Resources

- Django-Q Documentation: https://django-q.readthedocs.io/
- SumUp API Documentation: https://developer.sumup.com/
- Implementation Status: `POLLING_IMPLEMENTATION_STATUS.md`
- Polling Service Code: `payments/polling_service.py`

---

**Deployment Date:** _________
**Deployed By:** _________
**Verified By:** _________
**Notes:** _________
