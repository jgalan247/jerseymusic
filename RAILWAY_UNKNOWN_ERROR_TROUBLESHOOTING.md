# Railway "Unknown Error" Troubleshooting Guide

## What is the "Unknown Error"?

The "Unknown Error" page with "no-request-id" is a Railway-specific error that appears when your application fails to start or respond to health checks. This is **not** a Django application error - it indicates the deployment itself failed.

## Common Causes

### 1. Application Startup Failure (Most Common)
- Django fails to initialize due to configuration errors
- Missing or misconfigured environment variables
- Import errors or missing dependencies
- Database connection failures

### 2. Health Check Timeout
- Application takes longer than 300 seconds to start (configured in railway.json)
- Health check endpoint `/health/` is not responding
- Application crashes before health check can succeed

### 3. Port Binding Issues
- Application not binding to the PORT environment variable
- Gunicorn not starting correctly

### 4. Build Failures
- Dockerfile build errors
- Dependency installation failures
- Missing system packages

## Diagnostic Steps

### Step 1: Check Railway Deployment Logs

The **most important** step is to check your Railway logs:

1. Open your Railway project dashboard
2. Navigate to your service
3. Click on the "Deployments" tab
4. Select the failed deployment
5. Check both "Build Logs" and "Deploy Logs"

Look for error messages containing:
- `ImportError` or `ModuleNotFoundError`
- `django.core.exceptions`
- `DATABASE_URL` or connection errors
- `SECRET_KEY` errors
- Gunicorn startup errors

### Step 2: Verify Environment Variables

Check that all required environment variables are set in Railway:

**Critical Variables** (Must be set):
- ✅ `SECRET_KEY` - Django secret key
- ✅ `DATABASE_URL` - PostgreSQL connection (auto-provided by Railway)
- ✅ `PORT` - Auto-provided by Railway

**Payment Variables** (Required for app functionality):
- `SUMUP_CLIENT_ID`
- `SUMUP_CLIENT_SECRET`
- `SUMUP_MERCHANT_CODE`
- `SUMUP_ACCESS_TOKEN`
- `SUMUP_API_KEY`
- `SUMUP_MERCHANT_ID`

**DO NOT SET** (will cause deployment failure):
- ❌ `DEBUG=True` - Must be False or unset in production
- ❌ `LOCAL_TEST=True` - Will cause database errors

### Step 3: Run Local Diagnostic Script

Run the diagnostic script to check for common issues:

```bash
python3 diagnose_railway.py
```

This will check:
- Environment variables
- Python syntax errors
- Import issues
- Django configuration
- Database connectivity

### Step 4: Check Recent Changes

If the error started after a recent deployment, review your recent commits:

```bash
# Check recent commits
git log --oneline -10

# Check what changed in the last commit
git show HEAD --stat
git diff HEAD~1

# Check if there are any Python syntax errors
python3 -m py_compile $(find . -name "*.py" -not -path "./venv/*")
```

### Step 5: Test Locally

Try to reproduce the issue locally:

```bash
# Set environment variables for local testing
export DEBUG=False
export LOCAL_TEST=False
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
export SECRET_KEY="test-secret-key"

# Try running migrations
python manage.py migrate --noinput

# Try running the deployment check
python manage.py check --deploy

# Try starting gunicorn
gunicorn events.wsgi:application --bind 0.0.0.0:8000
```

## Common Fixes

### Fix 1: Missing Environment Variables

If `SECRET_KEY` or other critical variables are missing:

1. Go to Railway project settings
2. Click "Variables" tab
3. Add the missing variables
4. Railway will automatically redeploy

### Fix 2: Django Configuration Error

If there's a Django settings error:

1. Check `events/settings.py` for syntax errors
2. Verify all imports are correct
3. Check middleware and installed apps configuration
4. Push fixes and Railway will redeploy

### Fix 3: Database Connection Issues

If database connection fails:

1. Verify PostgreSQL service is running in Railway
2. Check that DATABASE_URL is properly linked
3. Try running migrations manually in Railway console:
   ```bash
   python manage.py migrate --noinput
   ```

### Fix 4: Import or Dependency Errors

If packages are missing:

1. Check `requirements.txt` for correct versions
2. Verify all required packages are listed
3. Check for typos in package names
4. Push updated requirements.txt

Recent example: We fixed `resend==2.5.0` → `resend==2.5.1` because 2.5.0 didn't exist.

### Fix 5: Health Check Issues

If health check is timing out:

1. Verify `/health/` endpoint exists (it does - in `events/app_urls.py`)
2. Check that endpoint returns quickly without database queries
3. Verify the endpoint isn't blocked by middleware or authentication
4. Consider increasing healthcheckTimeout in railway.json (currently 300s)

### Fix 6: Gunicorn Not Starting

If gunicorn fails to start:

1. Check `start.sh` script for errors
2. Verify `events.wsgi:application` is correct
3. Check that PORT environment variable is being used
4. Look for errors in gunicorn startup logs

## Checking Railway Logs via CLI

If you have Railway CLI installed:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# View logs
railway logs

# View logs for specific deployment
railway logs --deployment <deployment-id>
```

## Sentry Integration

If `SENTRY_DSN` is configured, check Sentry for error reports:

1. Log into sentry.io
2. Navigate to your Jersey Music project
3. Check for recent errors around the deployment time
4. Look for stack traces and error details

## Emergency Rollback

If you need to quickly restore service:

1. Go to Railway dashboard → Deployments
2. Find the last working deployment
3. Click "Redeploy" on that deployment

Or via CLI:
```bash
railway rollback
```

Or via git:
```bash
# Find the last working commit
git log --oneline

# Reset to that commit
git reset --hard <commit-hash>

# Force push (⚠️ use with caution)
git push -f origin <branch-name>
```

## Additional Resources

- **Railway Logs**: Your project dashboard → Deployments → Deploy Logs
- **Django Check**: Run `python manage.py check --deploy` locally
- **Health Check**: Test `/health/` endpoint after deployment
- **Start Script**: Review `start.sh` for initialization errors
- **Railway Docs**: https://docs.railway.app/
- **Django Deployment**: https://docs.djangoproject.com/en/5.0/howto/deployment/

## Getting Help

If you've tried all the above and still experiencing issues:

1. **Check Railway Status**: https://railway.statuspage.io/
2. **Railway Community**: https://discord.gg/railway
3. **Create GitHub Issue**: Include:
   - Full error message from logs
   - Recent changes (git diff)
   - Environment variable list (without sensitive values)
   - Diagnostic script output

## Specific to This Codebase

### Known Issues

1. **resend package version**: Must be 2.5.1 (not 2.5.0)
2. **DEBUG=True**: Will abort deployment with clear error message
3. **LOCAL_TEST=True**: Will cause database errors in production
4. **Missing SUMUP variables**: App will start but payments will fail

### Critical Files to Check

If deployment fails, check these files first:

1. `events/settings.py` - Django configuration
2. `events/urls.py` - Root URL configuration
3. `events/wsgi.py` - WSGI application
4. `start.sh` - Startup script
5. `requirements.txt` - Python dependencies
6. `Dockerfile` - Build configuration
7. `railway.json` - Railway configuration

### Health Check Endpoint

The health check is defined in `events/views.py:183`:

```python
def health_check(request):
    """Health check endpoint for Railway deployment monitoring."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'Jersey Music Events'
    }, status=200)
```

URL: `https://your-domain.railway.app/health/`

Should return: `{"status": "healthy", "service": "Jersey Music Events"}`

## Preventive Measures

### Before Every Deployment

1. Run tests locally: `pytest`
2. Run Django check: `python manage.py check --deploy`
3. Check for syntax errors: `python3 -m py_compile **/*.py`
4. Verify requirements.txt is up to date
5. Review recent changes: `git diff origin/main`

### Continuous Monitoring

1. Set up Sentry for error monitoring (`SENTRY_DSN`)
2. Monitor Railway deployment logs after each push
3. Set up uptime monitoring (e.g., UptimeRobot)
4. Test health check endpoint regularly

---

**Last Updated**: 2025-11-23
**Railway Configuration**: See `railway.json`, `start.sh`, `Dockerfile`
**Health Check Timeout**: 300 seconds
**Restart Policy**: ON_FAILURE with 10 max retries
