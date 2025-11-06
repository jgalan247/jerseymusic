# 🚀 PRODUCTION DEPLOYMENT CHECKLIST
**Jersey Events - Django Ticket Sales Platform**
**Last Updated:** November 6, 2025

---

## 📖 DEPLOYMENT GUIDES

**For Railway deployment**, see the detailed guide: **[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)**

This checklist covers general production readiness across all platforms.

---

## ⚠️ CRITICAL WARNING
**DO NOT DEPLOY TO PRODUCTION** until ALL items in the "MUST DO BEFORE LAUNCH" section are completed!

---

## 🔴 MUST DO BEFORE LAUNCH (Critical Security)

### 1. ⚠️ ROTATE ALL CREDENTIALS IN .env FILE
- [ ] **Generate new SECRET_KEY:**
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- [ ] **Rotate SumUp credentials** (get new ones from SumUp dashboard)
- [ ] **Remove all test/demo credentials**
- [ ] **Never commit .env to git** (already in .gitignore)

### 2. ⚠️ IMPLEMENT SUMUP WEBHOOK SIGNATURE VERIFICATION
**CRITICAL: The payment webhook has NO signature verification!**
- [ ] Contact SumUp support for webhook signature documentation
- [ ] Implement signature verification in `redirect_success_fixed.py`
- [ ] Test with real SumUp webhooks
- [ ] **WITHOUT THIS, ANYONE CAN FAKE PAYMENTS!**

### 3. ✅ SET ENVIRONMENT VARIABLES ON DIGITAL OCEAN
```bash
# Required environment variables for production:
SECRET_KEY=<generate-strong-50-char-key>
DEBUG=False
DATABASE_URL=<digital-ocean-provides-this>
SENTRY_DSN=<your-sentry-project-dsn>

# SumUp Production Credentials (from SumUp dashboard)
SUMUP_CLIENT_ID=<production-client-id>
SUMUP_CLIENT_SECRET=<production-client-secret>
SUMUP_MERCHANT_CODE=<your-merchant-code>
SUMUP_API_KEY=<production-api-key>

# Email Configuration
EMAIL_PROVIDER=sendgrid  # or mailgun
SENDGRID_API_KEY=<your-sendgrid-key>

# Site Configuration
SITE_URL=https://yourdomain.je
ALLOWED_HOSTS=yourdomain.je,www.yourdomain.je
```

### 4. ✅ DATABASE SETUP
- [ ] Create PostgreSQL database on Digital Ocean
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Configure automated backups (Digital Ocean dashboard)

### 5. ✅ INSTALL DEPENDENCIES
```bash
pip install -r requirements.txt
# New dependencies added:
# - dj-database-url==2.2.0
# - django-ratelimit==4.1.0
# - sentry-sdk==2.10.0
```

---

## 🟡 HIGH PRIORITY (Complete within 1 week)

### 6. PAYMENT SECURITY
- [ ] Test payment amount validation is working
- [ ] Implement idempotency for webhook processing
- [ ] Add payment reconciliation process
- [ ] Set up payment failure alerts

### 7. MONITORING & ALERTS
- [ ] Configure Sentry error tracking (SENTRY_DSN)
- [ ] Set up uptime monitoring (UptimeRobot/Pingdom)
- [ ] Configure payment failure alerts
- [ ] Set up database performance monitoring

### 8. LEGAL COMPLIANCE
- [ ] Create Terms of Service page
- [ ] Create Privacy Policy page (GDPR compliant)
- [ ] Add cookie consent banner
- [ ] Implement data deletion mechanism (GDPR)

### 9. TESTING
- [ ] Test complete payment flow with REAL money (small amount)
- [ ] Test refund process
- [ ] Load test ticket purchasing (prevent overselling)
- [ ] Test email delivery (tickets with QR codes)

---

## 🟠 SHOULD DO (Complete within 2-3 weeks)

### 10. FRAUD PREVENTION
- [ ] Add CAPTCHA to checkout (reCAPTCHA/hCaptcha)
- [ ] Implement velocity checking (max tickets per IP)
- [ ] Add suspicious transaction monitoring
- [ ] Block known bot user agents

### 11. PERFORMANCE
- [ ] Configure CDN for static files (CloudFront/Cloudflare)
- [ ] Set up Redis for caching
- [ ] Optimize database queries (use select_related/prefetch_related)
- [ ] Enable gzip compression

### 12. BACKUP & RECOVERY
- [ ] Test database restore process
- [ ] Create disaster recovery plan
- [ ] Document rollback procedure
- [ ] Set up staging environment

---

## 📋 DIGITAL OCEAN APP PLATFORM CONFIGURATION

### Build Command:
```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

### Run Command:
```bash
gunicorn events.wsgi:application --bind 0.0.0.0:8000
```

### Environment Variables (see section 3 above)

### Health Check Path: `/health/` (needs implementation)

---

## 🔍 WHAT'S STILL NOT PRODUCTION-READY

### ⚠️ CRITICAL GAPS:
1. **NO webhook signature verification** - anyone can fake payments
2. **NO PCI compliance audit** - required for payment processing
3. **NO GDPR compliance** - no privacy policy or data deletion
4. **NO fraud detection** - vulnerable to bots and scalping
5. **NO payment reconciliation** - can't detect payment discrepancies

### 🚨 SECURITY VULNERABILITIES REMAINING:
- Webhook endpoints can be exploited without signature verification
- No rate limiting on ticket purchase endpoint
- QR codes use weak MD5 hashing (should use HMAC-SHA256)
- No anti-bot protection on high-demand events

---

## ✅ WHAT HAS BEEN FIXED

### Security Improvements Implemented:
- ✅ SECRET_KEY now requires environment variable (no default)
- ✅ DEBUG defaults to False for production
- ✅ PostgreSQL configuration ready (DATABASE_URL support)
- ✅ Session and cookie security hardened
- ✅ Payment amount validation added
- ✅ Rate limiting on checkout (10 requests/minute)
- ✅ Ticket inventory locking to prevent overselling
- ✅ Sentry error monitoring configured
- ✅ Structured logging for audit trail
- ✅ Security headers (HSTS, XSS protection, etc.)

---

## 📅 RECOMMENDED TIMELINE

### Week 1: Critical Security
- Days 1-2: Rotate credentials, configure Digital Ocean
- Days 3-4: Deploy with PostgreSQL, test payments
- Days 5-7: Monitor for issues, fix bugs

### Week 2: Compliance & Testing
- Implement webhook verification (or disable payments temporarily)
- Add legal pages
- Extensive testing with real payments

### Week 3-4: Optimization & Hardening
- Add fraud detection
- Performance optimization
- Full security audit

---

## 🚦 GO/NO-GO DECISION

### ✅ CAN LAUNCH (LIMITED BETA) IF:
- All "MUST DO" items completed
- Webhook verification implemented OR payments in test mode
- Legal pages published
- Tested with real money

### 🛑 DO NOT LAUNCH IF:
- Using default SECRET_KEY
- DEBUG=True in production
- No database backups configured
- Webhook verification not implemented (for real payments)

---

## 📞 SUPPORT CONTACTS

- **Digital Ocean Support:** https://www.digitalocean.com/support/
- **SumUp Developer Support:** developer@sumup.com
- **Sentry Support:** https://sentry.io/support/

---

## ⚡ QUICK COMMANDS

```bash
# Check production readiness
python manage.py check --deploy

# Test database connection
python manage.py dbshell

# Collect static files
python manage.py collectstatic

# Run migrations
python manage.py migrate

# Create cache table (if using database cache)
python manage.py createcachetable
```

---

**⚠️ FINAL WARNING:** This platform handles real money. Security cannot be compromised. When in doubt, hire a security consultant for a final audit before processing real payments.