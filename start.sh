#!/usr/bin/env bash
# Railway startup script - runs migrations and starts the web server

set -e  # Exit on error

echo "🚀 Starting Jersey Music application..."

# ============================================
# PRODUCTION ENVIRONMENT VALIDATION
# ============================================
echo "🔍 Validating production environment configuration..."

# Detect if we're in Railway
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "✅ Detected Railway environment: $RAILWAY_ENVIRONMENT"

    # CRITICAL: Check DEBUG is False in production
    if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ] || [ "$DEBUG" = "TRUE" ]; then
        echo "🚨 FATAL ERROR: DEBUG=True detected in production Railway environment!"
        echo ""
        echo "This is a critical security misconfiguration that MUST be fixed."
        echo ""
        echo "⚡ FIX THIS NOW:"
        echo "1. Go to your Railway project dashboard"
        echo "2. Navigate to: Variables tab"
        echo "3. Either DELETE the DEBUG variable (it defaults to False)"
        echo "   OR set it to: DEBUG=False"
        echo ""
        echo "🛑 Deployment aborted. Fix the configuration and redeploy."
        exit 1
    fi

    # CRITICAL: Check LOCAL_TEST is False in production
    if [ "$LOCAL_TEST" = "True" ] || [ "$LOCAL_TEST" = "true" ] || [ "$LOCAL_TEST" = "TRUE" ]; then
        echo "🚨 FATAL ERROR: LOCAL_TEST=True detected in production!"
        echo "This will use SQLite which WILL cause database errors in production."
        echo ""
        echo "⚡ FIX THIS NOW:"
        echo "1. Go to your Railway project dashboard"
        echo "2. Navigate to: Variables tab"
        echo "3. DELETE the LOCAL_TEST variable (it should not exist in production)"
        echo ""
        echo "🛑 Deployment aborted. Fix the configuration and redeploy."
        exit 1
    fi

    # Check DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        echo "🚨 FATAL ERROR: DATABASE_URL not set!"
        echo "Railway should automatically provide this. Check your database service."
        exit 1
    fi

    # Check SECRET_KEY is set
    if [ -z "$SECRET_KEY" ]; then
        echo "🚨 FATAL ERROR: SECRET_KEY not set!"
        echo "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
        exit 1
    fi

    # Warn about Sentry DSN
    if [ -z "$SENTRY_DSN" ]; then
        echo "⚠️  WARNING: SENTRY_DSN not configured - no error monitoring!"
        echo "   Recommended: Set up Sentry for production error tracking"
    fi

    echo "✅ Production environment validation passed"
else
    echo "ℹ️  Not running in Railway environment (local development)"
fi

# Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Start the web server
echo "🌐 Starting gunicorn web server..."
exec gunicorn events.wsgi:application --bind 0.0.0.0:$PORT
