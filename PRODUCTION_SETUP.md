# 🚀 Production Setup Guide - Jersey Music

This guide walks you through preparing your Jersey Music application for production deployment on Railway.

## ✅ Pre-Deployment Checklist

### 1. Add boto3 to requirements.txt ✅
Already done! `boto3==1.35.76` has been added for AWS S3 integration.

### 2. Set up Sentry Error Monitoring

Sentry provides real-time error tracking and monitoring for production.

#### Step 1: Create a Sentry Account
1. Go to [https://sentry.io](https://sentry.io)
2. Sign up for a free account (or use your existing account)
3. Click **"Create Project"**

#### Step 2: Configure Your Sentry Project
1. **Platform**: Select **Django**
2. **Project Name**: `jerseymusic-production` (or your preferred name)
3. **Team**: Select your default team
4. Click **"Create Project"**

#### Step 3: Get Your DSN
After creating the project, Sentry will show you setup instructions. You need the **DSN** (Data Source Name).

1. Look for a line like:
   ```python
   dsn="https://abc123def456@o123456.ingest.sentry.io/7890123"
   ```
2. **Copy the full DSN URL** (starts with `https://`)

Or navigate to:
- **Settings** > **Projects** > **[Your Project]** > **Client Keys (DSN)**
- Copy the **DSN** value

#### Step 4: Configure Sentry in Railway
1. Open your Railway project: [https://railway.app](https://railway.app)
2. Select your **jerseymusic** service
3. Go to **Variables** tab
4. Click **"+ New Variable"**
5. Add:
   - **Variable**: `SENTRY_DSN`
   - **Value**: `https://abc123def456@o123456.ingest.sentry.io/7890123` (your actual DSN)
6. Click **"Add"**

### 3. Verify DEBUG=False in Railway

**IMPORTANT**: Your application will automatically fail to deploy if `DEBUG=True` in production.

#### Check Railway Variables
1. Go to Railway project > **Variables** tab
2. **VERIFY** that `DEBUG` is **NOT SET** (it should not appear in the list)
3. If you see `DEBUG` in your variables:
   - Click the **⨯ (delete)** button next to it
   - The app defaults to `DEBUG=False` when the variable doesn't exist

**Why this matters:**
- `DEBUG=True` in production exposes sensitive information
- The `start.sh` script will **abort deployment** if it detects `DEBUG=True`
- Default behavior (no DEBUG variable) = `DEBUG=False` ✅

### 4. Verify LOCAL_TEST=False in Railway

**IMPORTANT**: Your application will fail to deploy if `LOCAL_TEST=True` in production.

#### Check Railway Variables
1. Go to Railway project > **Variables** tab
2. **VERIFY** that `LOCAL_TEST` is **NOT SET**
3. If you see `LOCAL_TEST` in your variables:
   - Click the **⨯ (delete)** button next to it
   - The app defaults to `LOCAL_TEST=False` when the variable doesn't exist

**Why this matters:**
- `LOCAL_TEST=True` forces SQLite usage (unsuitable for production)
- Production requires PostgreSQL via `DATABASE_URL`
- The `start.sh` script will **abort deployment** if it detects `LOCAL_TEST=True`

---

## 🔧 Required Railway Environment Variables

Here's the complete list of variables you need in Railway:

### Critical Variables (REQUIRED)

```bash
# Django Secret Key (generate with Python command below)
SECRET_KEY=<your-50-character-secret-key>

# Sentry Error Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/your-project-id

# SumUp Payment Credentials
SUMUP_CLIENT_ID=<from-sumup-dashboard>
SUMUP_CLIENT_SECRET=<from-sumup-dashboard>
SUMUP_MERCHANT_CODE=<from-sumup-dashboard>
SUMUP_ACCESS_TOKEN=<from-sumup-dashboard>
SUMUP_API_KEY=<from-sumup-dashboard>
SUMUP_MERCHANT_ID=<from-sumup-dashboard>

# Email Configuration (Amazon SES)
EMAIL_HOST_USER=<your-ses-smtp-username>
EMAIL_HOST_PASSWORD=<your-ses-smtp-password>

# Site Configuration
ALLOWED_HOSTS=<your-railway-domain.up.railway.app>
SITE_URL=https://<your-railway-domain.up.railway.app>
```

### Optional Variables

```bash
# Environment name for Sentry
ENVIRONMENT=production

# AWS S3 (if using S3 for media storage)
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
AWS_STORAGE_BUCKET_NAME=jerseymusic-media
AWS_S3_REGION_NAME=eu-west-2

# Enable Django-Q background tasks (only if running qcluster worker)
ENABLE_DJANGO_Q=false  # Keep false for web deployment
```

### Variables That Should NOT Exist

```bash
# ❌ DO NOT SET THESE IN RAILWAY
# DEBUG=False          # Defaults to False, setting it can cause issues
# LOCAL_TEST=False     # Defaults to False, setting it can cause issues
```

---

## 🔑 Generate SECRET_KEY

Run this command locally to generate a secure secret key:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and add it to Railway as `SECRET_KEY`.

---

## 📧 Email Configuration (Amazon SES)

Your application is already configured to use Amazon SES (eu-north-1 region).

### Get SES Credentials
1. Log into AWS Console: [https://console.aws.amazon.com](https://console.aws.amazon.com)
2. Go to **SES (Simple Email Service)**
3. Navigate to **SMTP Settings**
4. Click **"Create My SMTP Credentials"**
5. Copy the **SMTP Username** and **SMTP Password**
6. Add to Railway:
   - `EMAIL_HOST_USER=<smtp-username>`
   - `EMAIL_HOST_PASSWORD=<smtp-password>`

### Verify Email Addresses
1. In SES, go to **Verified Identities**
2. Click **"Create Identity"**
3. Verify your sending email address (e.g., `noreply@jerseymusic.je`)
4. Check your email for verification link
5. Click the link to verify

---

## 🗄️ Database (PostgreSQL)

Railway automatically provides `DATABASE_URL` when you add a PostgreSQL database.

### Add PostgreSQL to Railway
1. In your Railway project, click **"+ New"**
2. Select **"Database"** > **"PostgreSQL"**
3. Railway automatically links it to your service
4. `DATABASE_URL` is automatically set

**You don't need to manually set DATABASE_URL** - Railway handles this.

---

## 🚀 Deployment Steps

### 1. Commit and Push Your Changes

```bash
# Add boto3 and production fixes
git add requirements.txt events/settings.py CLAUDE.md
git commit -m "Add boto3 and prepare for production deployment"
git push origin main
```

### 2. Configure Railway Variables

Add all required variables from the list above in Railway's Variables tab.

### 3. Deploy

Railway will automatically deploy when you push to main. Monitor the deployment:

1. Go to Railway project > **Deployments** tab
2. Watch the build logs
3. Wait for health check to pass (should take 1-2 minutes)

### 4. Verify Production Settings

After successful deployment, check:

```bash
# Check Sentry is receiving data
# Visit: https://sentry.io/organizations/[your-org]/projects/
# You should see your project with 0 errors (if everything is working)

# Test your application
# Visit: https://your-railway-domain.up.railway.app
# Check: Health endpoint returns {"status": "healthy"}
# Visit: https://your-railway-domain.up.railway.app/health/
```

---

## 🔍 Post-Deployment Verification

### 1. Check Application Logs
```
Railway Dashboard > Deployments > Latest > View Logs
```

Look for:
- ✅ `Production security settings enabled`
- ✅ `Sentry error monitoring enabled`
- ✅ `Migrations completed successfully`
- ✅ `Django application verified successfully`
- ✅ `Starting gunicorn web server...`

### 2. Test Sentry Integration

Trigger a test error to verify Sentry is working:

1. In Railway logs, you should see: `✅ Sentry error monitoring enabled`
2. Visit your Sentry dashboard: [https://sentry.io](https://sentry.io)
3. Check that the project shows as active
4. When real errors occur, they'll appear in Sentry automatically

### 3. Verify Email Configuration

Test email sending:
1. Register a new user account on your site
2. Check that verification email is sent
3. Check AWS SES Console for sent email metrics

---

## 🛡️ Security Checklist

- ✅ `DEBUG=False` (default, not set in Railway)
- ✅ `LOCAL_TEST=False` (default, not set in Railway)
- ✅ `SECRET_KEY` set to a strong, unique value
- ✅ `SENTRY_DSN` configured for error monitoring
- ✅ `ALLOWED_HOSTS` set to your Railway domain
- ✅ PostgreSQL database (not SQLite)
- ✅ HTTPS enforced (Railway provides this automatically)
- ✅ SumUp credentials configured
- ✅ Email verification enabled

---

## 🆘 Troubleshooting

### Deployment fails with "CRITICAL SECURITY ERROR"
- **Cause**: `DEBUG=True` is set in Railway
- **Fix**: Delete the `DEBUG` variable from Railway Variables tab

### Deployment fails with "CRITICAL DATABASE ERROR"
- **Cause**: `LOCAL_TEST=True` is set in Railway
- **Fix**: Delete the `LOCAL_TEST` variable from Railway Variables tab

### Health check fails after 5 minutes
- **Cause**: Application failed to start
- **Fix**: Check Railway logs for errors, verify all required variables are set

### Sentry not receiving errors
- **Verify**: `SENTRY_DSN` is correctly set in Railway
- **Check**: Application logs show "✅ Sentry error monitoring enabled"
- **Test**: Trigger a test error and check Sentry dashboard

### Email not sending
- **Verify**: `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set
- **Check**: Email address is verified in AWS SES
- **Note**: SES starts in sandbox mode - verify recipient emails or request production access

---

## 📚 Additional Resources

- **Sentry Documentation**: [https://docs.sentry.io/platforms/python/guides/django/](https://docs.sentry.io/platforms/python/guides/django/)
- **Railway Documentation**: [https://docs.railway.app/](https://docs.railway.app/)
- **AWS SES Documentation**: [https://docs.aws.amazon.com/ses/](https://docs.aws.amazon.com/ses/)
- **Django Production Checklist**: [https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)

---

## ✅ Production Ready!

Once you've completed all steps above, your Jersey Music application will be:
- ✅ Running with `DEBUG=False`
- ✅ Monitoring errors with Sentry
- ✅ Using PostgreSQL for database
- ✅ Sending emails via Amazon SES
- ✅ Processing payments via SumUp
- ✅ Secured with HTTPS
- ✅ Protected by Django security middleware

**Your application is now production-ready! 🎉**
