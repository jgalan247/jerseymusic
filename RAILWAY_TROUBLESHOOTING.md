# 🔧 Railway Deployment Troubleshooting Guide

## 🚨 Common Deployment Errors and Fixes

### Error: "DEBUG=True detected in production"

**Symptom:**
```
🚨 CRITICAL SECURITY ERROR 🚨
❌ DEBUG=True detected in production Railway environment!
🛑 DEPLOYMENT ABORTED
```

**Why this happens:**
- You have a `DEBUG` environment variable set to "True" in Railway
- This exposes sensitive debug information and is a critical security risk

**How to fix:**

**Option 1: Delete the DEBUG variable (RECOMMENDED)**
1. Go to your Railway project: https://railway.app/project/YOUR_PROJECT_ID/settings
2. Click the **Variables** tab
3. Find the `DEBUG` variable
4. Click the **Delete (⨯)** button next to it
5. Railway will automatically redeploy

**Option 2: Set DEBUG to False**
1. Go to your Railway project: https://railway.app/project/YOUR_PROJECT_ID/settings
2. Click the **Variables** tab
3. Find the `DEBUG` variable
4. Change the value to: `False` (or `false`)
5. Click **Save** and Railway will redeploy

**💡 Pro Tip:**
DEBUG defaults to `False` automatically in production - you don't need to set it at all! The safest approach is to simply delete the variable.

---

### Error: "LOCAL_TEST=True detected in production"

**Symptom:**
```
🚨 CRITICAL DATABASE ERROR 🚨
❌ LOCAL_TEST=True detected in production Railway environment!
This forces SQLite usage and WILL cause database errors in production.
🛑 DEPLOYMENT ABORTED
```

**Why this happens:**
- You have a `LOCAL_TEST` environment variable set to "True" in Railway
- This forces Django to use SQLite instead of PostgreSQL
- SQLite doesn't work properly in Railway's ephemeral filesystem

**How to fix:**
1. Go to your Railway project: https://railway.app/project/YOUR_PROJECT_ID/settings
2. Click the **Variables** tab
3. Find the `LOCAL_TEST` variable
4. Click the **Delete (⨯)** button next to it
5. Railway will automatically redeploy

**💡 Pro Tip:**
`LOCAL_TEST` is ONLY for local development with SQLite. It should NEVER exist in production. Just delete it!

---

### Error: "SECRET_KEY not set"

**Symptom:**
```
🚨 FATAL ERROR: SECRET_KEY not set!
```

**Why this happens:**
- Django requires a secret key for cryptographic signing
- This is a required environment variable

**How to fix:**
1. Generate a strong secret key by running locally:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
2. Copy the generated key
3. Go to your Railway project: https://railway.app/project/YOUR_PROJECT_ID/settings
4. Click the **Variables** tab
5. Add a new variable:
   - Name: `SECRET_KEY`
   - Value: (paste the generated key)
6. Click **Save**

---

### Error: "DATABASE_URL not set"

**Symptom:**
```
🚨 FATAL ERROR: DATABASE_URL not set!
```

**Why this happens:**
- Your Railway project doesn't have a PostgreSQL database attached

**How to fix:**
1. Go to your Railway project dashboard
2. Click **+ New** button
3. Select **Database** → **Add PostgreSQL**
4. Railway will automatically:
   - Create the database
   - Set the `DATABASE_URL` environment variable
   - Redeploy your application

---

## ✅ Successful Deployment Checklist

When your deployment succeeds, you should see:

```
╔═══════════════════════════════════════════════════════════════════════╗
║              ✅ PRODUCTION ENVIRONMENT VALIDATED                      ║
╚═══════════════════════════════════════════════════════════════════════╝

✓ DEBUG is not True (production mode active)
✓ LOCAL_TEST is not True (will use PostgreSQL)
✓ DATABASE_URL is configured
✓ SECRET_KEY is set
✓ Sentry error monitoring enabled

📦 Running database migrations...
📦 Collecting static files...
🌐 Starting gunicorn web server...
```

---

## 🔍 Environment Variable Quick Reference

### ✅ Variables that MUST be set in Railway:

| Variable | Description | How to get |
|----------|-------------|------------|
| `SECRET_KEY` | Django cryptographic key | Generate with Python command above |
| `DATABASE_URL` | PostgreSQL connection | Auto-set when you add PostgreSQL |
| `SUMUP_CLIENT_ID` | SumUp OAuth client ID | From SumUp developer dashboard |
| `SUMUP_CLIENT_SECRET` | SumUp OAuth secret | From SumUp developer dashboard |
| `SUMUP_MERCHANT_CODE` | SumUp merchant code | From SumUp account |
| `SUMUP_ACCESS_TOKEN` | SumUp platform token | From SumUp dashboard |
| `SUMUP_API_KEY` | SumUp API key | From SumUp dashboard |
| `SUMUP_MERCHANT_ID` | SumUp merchant ID | From SumUp account |

### ⚠️ Variables that should NEVER be set in Railway:

| Variable | Why NOT to set | Default behavior |
|----------|---------------|------------------|
| `DEBUG` | Security risk - exposes sensitive info | Defaults to `False` ✅ |
| `LOCAL_TEST` | Forces SQLite (breaks in production) | Defaults to `False` ✅ |

### 📋 Optional but recommended variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTRY_DSN` | Error monitoring | None (warnings shown) |
| `EMAIL_HOST_USER` | Email sending address | Console backend |
| `EMAIL_HOST_PASSWORD` | Email password | Console backend |
| `ENVIRONMENT` | Environment name | "production" |
| `ALLOWED_HOSTS` | Allowed domains | Railway domain auto-added |

---

## 🆘 Still Having Issues?

1. **Check the deployment logs:**
   - Go to your Railway project
   - Click on your service
   - View the **Deploy Logs** tab
   - Look for the first error message

2. **Review the environment variables:**
   - Go to the **Variables** tab
   - Make sure DEBUG and LOCAL_TEST are NOT listed
   - Verify all required variables are set

3. **Redeploy from scratch:**
   - Delete DEBUG and LOCAL_TEST variables
   - Click **Redeploy** button in Railway

4. **Check the documentation:**
   - `RAILWAY_DEPLOYMENT.md` - Full deployment guide
   - `.env.example` - Example of development variables
   - `CLAUDE.md` - Project architecture overview

---

## 📚 Related Documentation

- **Full deployment guide:** [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md)
- **Environment template:** [.env.example](./.env.example) (for local dev only!)
- **Deployment checklist:** [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

**Last Updated:** 2025-01-06
