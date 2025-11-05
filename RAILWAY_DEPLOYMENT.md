# 🚂 Railway.app Deployment Guide
**Jersey Music Events Platform**

---

## 📋 Overview

This guide covers deploying the Jersey Music Events ticketing platform to Railway.app. Railway is a modern Platform-as-a-Service (PaaS) that makes deployment simple with automatic builds, PostgreSQL databases, and environment management.

---

## ✅ Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] Railway.app account (sign up at https://railway.app)
- [ ] GitHub account with this repository
- [ ] Production SumUp credentials (from SumUp dashboard)
- [ ] Email service configured (SendGrid, Mailgun, or Gmail)
- [ ] Generated a new SECRET_KEY for production
- [ ] Reviewed and understood the security requirements in `DEPLOYMENT_CHECKLIST.md`

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Create Railway Project

1. Go to https://railway.app and sign in with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `jerseymusic` repository
5. Railway will automatically detect Django and start building

### Step 2: Add PostgreSQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway automatically sets the `DATABASE_URL` environment variable
4. Wait for the database to provision (~30 seconds)

### Step 3: Configure Environment Variables

1. Click on your web service (the Django app)
2. Go to the **"Variables"** tab
3. Click **"+ Add Variable"** and add these **CRITICAL** variables:

```bash
SECRET_KEY=<generate-with-command-below>
DEBUG=False
ALLOWED_HOSTS=<your-railway-domain>
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

4. Add email and SumUp variables (see `.env.railway.example` for full list)

### Step 4: Deploy!

1. Railway automatically deploys when you push to GitHub
2. Or click **"Deploy"** in the Railway dashboard
3. Watch the build logs to ensure successful deployment
4. Once deployed, Railway provides a URL: `https://your-app.up.railway.app`

---

## 📝 Detailed Deployment Steps

### 1. Repository Setup

Your repository already includes all necessary Railway configuration files:

- ✅ `Procfile` - Defines web and worker processes
- ✅ `runtime.txt` - Specifies Python 3.11.14
- ✅ `railway.json` - Railway build and deploy configuration
- ✅ `build.sh` - Build script for migrations and static files
- ✅ `requirements.txt` - All Python dependencies
- ✅ `.env.railway.example` - Template for environment variables

### 2. Railway Project Configuration

#### Create New Project
```
1. Railway Dashboard → "New Project"
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub account
4. Choose the jerseymusic repository
5. Railway detects Django automatically
```

#### Configure Build Settings (Already Configured)
Railway will automatically:
- Install dependencies from `requirements.txt`
- Run `python manage.py collectstatic --noinput`
- Run `python manage.py migrate --noinput`
- Start gunicorn on the assigned `$PORT`

### 3. Database Configuration

#### Add PostgreSQL
```
1. Project Dashboard → "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway provisions database and sets DATABASE_URL
4. No manual configuration needed!
```

#### Verify Database Connection
```bash
# Railway automatically sets:
DATABASE_URL=postgresql://user:password@host:port/database

# Your Django settings.py already handles this!
```

### 4. Environment Variables Setup

#### Required Variables (MUST SET)

```bash
# Django Core
SECRET_KEY=<50-char-random-string>
DEBUG=False
ALLOWED_HOSTS=your-app.up.railway.app,yourdomain.com

# Email Configuration
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# SumUp Payment (Production Credentials!)
SUMUP_API_URL=https://api.sumup.com/v0.1
SUMUP_CLIENT_ID=your_production_client_id
SUMUP_CLIENT_SECRET=your_production_client_secret
SUMUP_MERCHANT_CODE=your_merchant_code
SUMUP_ACCESS_TOKEN=your_access_token
SUMUP_API_KEY=your_api_key
SUMUP_MERCHANT_ID=your_merchant_id
SUMUP_REDIRECT_URI=https://your-app.up.railway.app/payments/sumup/callback/

# Site Configuration
SITE_URL=https://your-app.up.railway.app
ENVIRONMENT=production
```

#### Optional But Recommended

```bash
# Error Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Pricing Configuration (has defaults)
PLATFORM_CURRENCY=GBP
TIER_1_FEE=0.50
# ... see .env.railway.example for all tiers
```

### 5. Custom Domain Setup (Optional)

#### Add Your Domain
```
1. Project → Settings → Domains
2. Click "Add Domain"
3. Enter your domain: events.yourdomain.je
4. Add CNAME record to your DNS:
   - Name: events (or @)
   - Value: <provided-by-railway>.railway.app
5. Wait for DNS propagation (up to 48 hours)
```

#### Update Environment Variables
```bash
ALLOWED_HOSTS=events.yourdomain.je,www.events.yourdomain.je
SITE_URL=https://events.yourdomain.je
SUMUP_REDIRECT_URI=https://events.yourdomain.je/payments/sumup/callback/
```

### 6. Django-Q Worker (Optional - For Background Tasks)

If you need background task processing:

```
1. Project Dashboard → "+ New"
2. Select "Empty Service"
3. Connect same GitHub repo
4. Go to Settings → Deploy
5. Set Custom Start Command: python manage.py qcluster
6. Deploy
```

This runs the Django-Q worker separately from the web process.

---

## 🔧 Configuration Files Explained

### Procfile
```
web: gunicorn events.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
worker: python manage.py qcluster
```
- **web**: Main Django application (always runs)
- **worker**: Background task processor (optional, needs separate service)

### runtime.txt
```
python-3.11.14
```
Specifies exact Python version for Railway to use.

### railway.json
```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install && collectstatic && migrate"
  },
  "deploy": {
    "startCommand": "gunicorn events.wsgi:application",
    "healthcheckPath": "/",
    "restartPolicyType": "ON_FAILURE"
  }
}
```
Railway-specific configuration for build and deployment.

### build.sh
```bash
#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
```
Backup build script (railway.json handles this automatically).

---

## 🧪 Testing Your Deployment

### 1. Check Health
```bash
curl https://your-app.up.railway.app/
# Should return 200 OK
```

### 2. Verify Database
```bash
# Railway CLI (install: npm i -g @railway/cli)
railway run python manage.py shell

# In Django shell:
from accounts.models import User
User.objects.count()  # Should work without errors
```

### 3. Test Static Files
```bash
curl https://your-app.up.railway.app/static/css/styles.css
# Should return CSS file (WhiteNoise serving)
```

### 4. Test Payment Flow
1. Create a test event
2. Add tickets to cart
3. Proceed to checkout
4. Use SumUp test card (if in test mode)
5. Verify ticket email delivery

---

## 📊 Monitoring & Maintenance

### View Logs
```
Railway Dashboard → Your Service → Deployments → Latest → Logs
```

### Common Log Commands
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs

# Run Django commands
railway run python manage.py createsuperuser
railway run python manage.py shell
```

### Set Up Alerts
1. Railway Dashboard → Project → Settings
2. Enable "Deployment Notifications"
3. Add webhook URL for Slack/Discord (optional)

### Database Backups
```
Railway Pro plan includes:
- Automatic daily backups
- Point-in-time recovery
- Backup retention: 14 days

Free plan: Manual exports only
```

---

## 🐛 Troubleshooting

### Build Fails
```bash
# Check requirements.txt
railway run pip install -r requirements.txt

# Verify Python version
cat runtime.txt  # Should be python-3.11.14
```

### Database Connection Errors
```bash
# Verify DATABASE_URL is set
railway variables

# Check PostgreSQL service status
Railway Dashboard → Database Service → Status
```

### Static Files Not Loading
```bash
# Verify WhiteNoise middleware is enabled
# Check events/settings.py line 111:
# 'whitenoise.middleware.WhiteNoiseMiddleware',

# Collect static files manually
railway run python manage.py collectstatic --noinput
```

### ALLOWED_HOSTS Error
```bash
# Add your Railway domain
railway variables set ALLOWED_HOSTS=your-app.up.railway.app

# Or use RAILWAY_PUBLIC_DOMAIN (automatic)
# settings.py already handles this!
```

### Payment Errors
```bash
# Verify SumUp credentials
railway variables | grep SUMUP

# Check callback URL
SUMUP_REDIRECT_URI=https://your-actual-domain.com/payments/sumup/callback/

# Update SumUp dashboard with production URL
```

---

## 🔐 Security Best Practices

### 1. Environment Variables
- ✅ Never commit `.env` files to git
- ✅ Use Railway's Variables interface
- ✅ Rotate SECRET_KEY for production
- ✅ Use production SumUp credentials
- ✅ Enable Sentry for error monitoring

### 2. Database Security
- ✅ Railway encrypts DATABASE_URL
- ✅ PostgreSQL connection over TLS
- ✅ Database accessible only within Railway network
- ✅ Enable database backups (Pro plan)

### 3. HTTPS & Domains
- ✅ Railway provides free HTTPS certificates
- ✅ Automatic cert renewal
- ✅ Force HTTPS (settings.py handles this when DEBUG=False)

### 4. Django Security
- ✅ DEBUG=False in production (CRITICAL!)
- ✅ SECURE_SSL_REDIRECT=True (auto-enabled)
- ✅ SESSION_COOKIE_SECURE=True (auto-enabled)
- ✅ CSRF protection enabled
- ✅ Security headers configured

---

## 💰 Railway Pricing

### Hobby Plan (Free)
- $5 free credits/month
- ~500 hours of usage
- 1 GB RAM
- Good for testing

### Pro Plan ($20/month)
- $20 free credits/month included
- Unlimited projects
- Database backups
- Priority support
- Custom domains
- **Recommended for production**

### Usage-Based Pricing
- CPU: $0.000463/vCPU-minute
- RAM: $0.000231/GB-minute
- Typical Django app: ~$10-30/month

---

## 🚦 Go-Live Checklist

Before launching to real users:

### Critical (MUST DO)
- [ ] DEBUG=False
- [ ] Strong SECRET_KEY set
- [ ] Production SumUp credentials configured
- [ ] Custom domain configured (optional but recommended)
- [ ] Email delivery tested and working
- [ ] Database backups enabled (Railway Pro)
- [ ] SSL/HTTPS working
- [ ] ALLOWED_HOSTS configured correctly

### High Priority
- [ ] Sentry error monitoring configured
- [ ] Payment flow tested with real money (small amount)
- [ ] Email templates reviewed
- [ ] Terms of Service and Privacy Policy pages live
- [ ] Refund process tested

### Recommended
- [ ] Uptime monitoring (UptimeRobot/Pingdom)
- [ ] Load testing completed
- [ ] Django-Q worker service running
- [ ] Admin account created
- [ ] Backup restore process tested

---

## 📞 Support & Resources

### Railway Resources
- **Dashboard**: https://railway.app
- **Documentation**: https://docs.railway.app
- **Discord Community**: https://discord.gg/railway
- **Status Page**: https://status.railway.app

### Django/SumUp Resources
- **Django Deployment**: https://docs.djangoproject.com/en/5.0/howto/deployment/
- **SumUp API Docs**: https://developer.sumup.com
- **WhiteNoise**: http://whitenoise.evans.io

### Project Documentation
- `DEPLOYMENT_CHECKLIST.md` - Production readiness checklist
- `CLAUDE.md` - Project architecture and development guide
- `.env.railway.example` - Environment variables template

---

## 🎯 Quick Commands Reference

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to project
railway link

# View environment variables
railway variables

# Set environment variable
railway variables set KEY=value

# View logs
railway logs

# Run Django commands
railway run python manage.py createsuperuser
railway run python manage.py migrate
railway run python manage.py shell

# Open Railway dashboard
railway open

# Deploy manually
git push origin main  # Railway auto-deploys from GitHub
```

---

## ✅ Post-Deployment Tasks

After successful deployment:

1. **Create superuser account**
   ```bash
   railway run python manage.py createsuperuser
   ```

2. **Test admin interface**
   - Visit https://your-app.up.railway.app/admin
   - Login with superuser credentials
   - Create test event

3. **Configure SumUp OAuth** (if using per-artist payments)
   - Artists can connect their SumUp accounts
   - Update redirect URIs in SumUp dashboard

4. **Monitor first 24 hours**
   - Check Railway logs regularly
   - Watch Sentry for errors
   - Test payment flows
   - Monitor email delivery

5. **Set up monitoring**
   - Enable Railway deployment notifications
   - Configure Sentry alerts
   - Set up uptime monitoring

---

## 🎉 Congratulations!

Your Jersey Music Events platform is now live on Railway!

**Next Steps:**
1. Share the URL with test users
2. Monitor logs and errors
3. Gather feedback
4. Iterate and improve

**Need Help?**
- Check `DEPLOYMENT_CHECKLIST.md` for security requirements
- Review `CLAUDE.md` for architecture details
- Contact Railway support via Discord
- Review Django deployment best practices

---

**Last Updated:** 2025-11-05
**Railway Version:** Railway v2 (Nixpacks)
**Django Version:** 5.0.2
**Python Version:** 3.11.14
