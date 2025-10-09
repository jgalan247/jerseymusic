# 🚀 Payment Polling System - Quick Start

## Installation (5 minutes)

```bash
# 1. Install Django-Q
pip install django-q==1.3.9

# 2. Run migrations
python manage.py makemigrations orders
python manage.py migrate

# 3. Create schedule (in Django shell)
python manage.py shell
```

```python
from django_q.models import Schedule
Schedule.objects.create(
    name='Payment Polling',
    func='payments.polling_service.polling_service.process_pending_payments',
    schedule_type='I',
    minutes=5,
    repeats=-1
)
exit()
```

```bash
# 4. Start qcluster
python manage.py qcluster
```

## Test Payment (2 minutes)

1. Add event to cart
2. Checkout with test card: **5555 4444 3333 1111**
3. You'll see "Processing payment..." page
4. Wait 5-10 minutes
5. Check email for tickets

## Production Deployment

```bash
# Install on server
pip install django-q==1.3.9
python manage.py migrate

# Create schedule (run once)
python manage.py shell -c "from django_q.models import Schedule; Schedule.objects.create(name='Payment Polling', func='payments.polling_service.polling_service.process_pending_payments', schedule_type='I', minutes=5, repeats=-1)"

# Start qcluster with supervisor
sudo supervisorctl start jerseyevents_qcluster
```

## Monitoring

```bash
# Check status
sudo supervisorctl status jerseyevents_qcluster

# View logs
tail -f logs/payment_polling.log

# Django admin
https://your-domain.com/admin/django_q/
```

## Troubleshooting

**Orders stuck?**
```bash
python manage.py run_payment_polling --verbose
```

**Need help?**
See `DEPLOYMENT_GUIDE_POLLING.md` for details.

## Files Changed

- ✅ `payments/polling_service.py` - Core polling logic
- ✅ `payments/redirect_views.py` - Updated to use polling
- ✅ `payments/success_views.py` - Updated to use polling
- ✅ `orders/models.py` - New statuses
- ✅ `templates/payments/processing.html` - New template
- ✅ `requirements.txt` - Added django-q

## Security Features

- ✅ Server-side payment verification
- ✅ Amount validation before ticket issuance
- ✅ Database locking prevents race conditions
- ✅ Admin alerts for critical issues
- ✅ Comprehensive audit logging

**Ready to deploy!** 🎉
