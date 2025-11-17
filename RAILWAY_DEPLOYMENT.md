# 🚂 Railway Deployment Guide - Jersey Music

## ⚠️ CRITICAL: Production Environment Variables

**IMPORTANT:** The application will REFUSE to start if misconfigured. All checks happen in `start.sh` before deployment.

### Required Environment Variables for Railway

Copy these variables into your Railway project's **Variables** tab:

```bash
# ============================================
# CRITICAL SECURITY SETTINGS (REQUIRED)
# ============================================

# Generate a new SECRET_KEY with:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=<generate-a-strong-50-character-secret-key>

# ⚠️  DO NOT SET DEBUG OR LOCAL_TEST IN PRODUCTION
# These variables should NOT exist in your Railway environment!
# They default to False automatically - adding them will cause errors!
#
# ❌ DO NOT ADD: DEBUG=False  (it's False by default)
# ❌ DO NOT ADD: LOCAL_TEST=False  (it's False by default)

# ============================================
# DATABASE (Auto-configured by Railway)
# ============================================
# Railway provides DATABASE_URL automatically when you add a PostgreSQL database
# You don't need to set this manually - Railway does it for you!
# DATABASE_URL=<railway-provides-this-automatically>

# ============================================
# ERROR MONITORING (HIGHLY RECOMMENDED)
# ============================================
# Get your Sentry DSN from: https://sentry.io
# 1. Create a new project in Sentry
# 2. Copy the DSN from Settings > Client Keys
SENTRY_DSN=https://your-sentry-dsn@sentry.io/your-project-id

# Optional: Environment name for Sentry (defaults to "production")
ENVIRONMENT=production

# ============================================
# SUMUP PAYMENT CREDENTIALS (REQUIRED)
# ============================================
# Get these from your SumUp developer dashboard
SUMUP_CLIENT_ID=<your-sumup-client-id>
SUMUP_CLIENT_SECRET=<your-sumup-client-secret>
SUMUP_MERCHANT_CODE=<your-merchant-code>
SUMUP_ACCESS_TOKEN=<your-access-token>
SUMUP_API_KEY=<your-api-key>
SUMUP_MERCHANT_ID=<your-merchant-id>

# SumUp API URL (usually doesn't need to change)
SUMUP_API_URL=https://api.sumup.com/v0.1

# ============================================
# EMAIL CONFIGURATION (RECOMMENDED)
# ============================================
# Choose one email provider: gmail, sendgrid, or mailgun

# Option 1: Gmail (Google Workspace)
EMAIL_PROVIDER=gmail
EMAIL_HOST_USER=noreply@yourdomain.je
EMAIL_HOST_PASSWORD=<your-app-specific-password>

# Option 2: SendGrid
# EMAIL_PROVIDER=sendgrid
# SENDGRID_API_KEY=<your-sendgrid-api-key>

# Option 3: Mailgun
# EMAIL_PROVIDER=mailgun
# MAILGUN_SMTP_USER=<your-mailgun-smtp-user>
# MAILGUN_SMTP_PASSWORD=<your-mailgun-smtp-password>

# ============================================
# SITE CONFIGURATION
# ============================================
# Your Railway domain (e.g., jerseymusic-production.up.railway.app)
SITE_URL=https://jerseymusic-production.up.railway.app

# Allowed hosts (comma-separated, no spaces)
# Include your custom domain if you have one
ALLOWED_HOSTS=jerseymusic-production.up.railway.app

# ============================================
# OPTIONAL: PRICING CONFIGURATION
# ============================================
# Only set these if you want to override defaults
# PLATFORM_CURRENCY=GBP
# TIER_1_CAPACITY=50
# TIER_1_FEE=0.50
# (see .env.example for full list of pricing variables)
```

---

## 🚀 Step-by-Step Railway Deployment

### 1. Prerequisites
- [ ] Railway account created (https://railway.app)
- [ ] GitHub repository connected to Railway
- [ ] PostgreSQL database added to Railway project

### 2. Add PostgreSQL Database
1. In your Railway project, click **"+ New"**
2. Select **"Database" > "PostgreSQL"**
3. Railway will automatically:
   - Create the database
   - Set the `DATABASE_URL` environment variable
   - Link it to your web service

### 3. Configure Environment Variables
1. Go to your web service in Railway
2. Click the **"Variables"** tab
3. Add **ONLY** the variables listed above
4. **CRITICAL:** Do NOT add `DEBUG` or `LOCAL_TEST` variables!

### 4. Generate SECRET_KEY
Run this command locally to generate a secure key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and paste it as the `SECRET_KEY` variable in Railway.

### 5. Set Up Sentry (Recommended)
1. Create a free account at https://sentry.io
2. Create a new Django project
3. Copy the DSN from Settings > Client Keys (SDK Setup)
4. Add it as `SENTRY_DSN` in Railway
5. Without this, you won't see production errors!

### 6. Deploy
1. Push your code to GitHub
2. Railway will automatically deploy
3. Watch the deployment logs for validation checks
4. If misconfigured, the deployment will fail with clear error messages

---

## 🔍 Troubleshooting Deployment Failures

### Error: "DEBUG=True detected in production Railway environment!"
**Cause:** You have `DEBUG=True` set in Railway's environment variables.

**Fix:**
1. Go to Railway dashboard > Your project > Variables tab
2. Find the `DEBUG` variable
3. Either **DELETE it** (recommended) or set it to `DEBUG=False`
4. Redeploy

### Error: "LOCAL_TEST=True detected in production!"
**Cause:** You have `LOCAL_TEST=True` set in Railway's environment variables.

**Fix:**
1. Go to Railway dashboard > Your project > Variables tab
2. Find the `LOCAL_TEST` variable
3. **DELETE it** (it should never exist in production)
4. Redeploy

### Error: "DATABASE_URL not set!"
**Cause:** PostgreSQL database not connected.

**Fix:**
1. In Railway project, click **"+ New" > "Database" > "PostgreSQL"**
2. Wait for database to provision
3. Railway automatically sets `DATABASE_URL`
4. Redeploy

### Error: "SECRET_KEY not set!"
**Cause:** No SECRET_KEY environment variable.

**Fix:**
1. Generate a key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
2. Add it to Railway Variables as `SECRET_KEY`
3. Redeploy

### Warning: "SENTRY_DSN not configured"
**Not a fatal error**, but you should set this up for production error monitoring.

---

## ✅ Deployment Checklist

Before going live with real payments:

- [ ] `SECRET_KEY` is set to a strong random key (not the dev default)
- [ ] `DEBUG` variable does NOT exist in Railway (or is set to False)
- [ ] `LOCAL_TEST` variable does NOT exist in Railway
- [ ] `DATABASE_URL` is automatically set by Railway PostgreSQL
- [ ] `SENTRY_DSN` is configured for error monitoring
- [ ] SumUp credentials are set (all 6 variables)
- [ ] Email provider is configured
- [ ] `SITE_URL` matches your Railway domain
- [ ] Test payment flow with small amount
- [ ] Check Sentry is receiving test errors
- [ ] Verify emails are being sent

---

## 🔒 Security Best Practices

1. **Never commit `.env` to git** (already in `.gitignore`)
2. **Rotate SECRET_KEY** if ever exposed
3. **Use Railway's secret variables** (they're encrypted at rest)
4. **Keep SumUp credentials secure** (use environment variables only)
5. **Enable Sentry** to catch errors before users report them
6. **Review Django's security checklist**: `python manage.py check --deploy`

---

## 📊 Monitoring Your Deployment

### Check Application Health
```bash
# View Railway logs
railway logs

# Check if app is running
curl https://your-app.up.railway.app/
```

### Monitor Errors with Sentry
1. Log in to https://sentry.io
2. View your Jersey Music project
3. Set up alerts for critical errors

### Database Status
- Check database health in Railway dashboard
- Monitor database size and connection pool

---

## 🆘 Getting Help

- **Railway Docs:** https://docs.railway.app
- **Railway Support:** https://railway.app/help
- **Sentry Docs:** https://docs.sentry.io
- **Django Security Checklist:** https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

---

## 📝 Quick Reference: What NOT To Do

❌ **DO NOT** set `DEBUG=True` in Railway
❌ **DO NOT** set `LOCAL_TEST=True` in Railway
❌ **DO NOT** use the example SECRET_KEY from .env.example
❌ **DO NOT** commit credentials to git
❌ **DO NOT** skip setting up Sentry

✅ **DO** let DEBUG default to False (don't set it)
✅ **DO** let LOCAL_TEST default to False (don't set it)
✅ **DO** generate a new SECRET_KEY for production
✅ **DO** use Railway's environment variables for secrets
✅ **DO** configure Sentry for error monitoring

---

**Last Updated:** 2025-11-06
**For Issues:** https://github.com/jgalan247/jerseymusic/issues
