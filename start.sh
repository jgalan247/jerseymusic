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
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                    🚨 CRITICAL SECURITY ERROR 🚨                      ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "❌ DEBUG=True detected in production Railway environment!"
        echo ""
        echo "This exposes sensitive information and MUST be fixed before deployment."
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                         🔧 HOW TO FIX THIS                            ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Option 1: DELETE the DEBUG variable (RECOMMENDED)"
        echo "  1. Open: https://railway.app/project/$RAILWAY_PROJECT_ID/settings"
        echo "  2. Click: Variables tab"
        echo "  3. Find: DEBUG variable"
        echo "  4. Click: Delete (⨯) button"
        echo "  5. Redeploy automatically starts"
        echo ""
        echo "Option 2: Set DEBUG to False (or 'false')"
        echo "  1. Open: https://railway.app/project/$RAILWAY_PROJECT_ID/settings"
        echo "  2. Click: Variables tab"
        echo "  3. Find: DEBUG variable"
        echo "  4. Change value to: False"
        echo "  5. Save and redeploy"
        echo ""
        echo "💡 TIP: DEBUG defaults to False when not set - no need to add it!"
        echo ""
        echo "📖 Full troubleshooting guide: RAILWAY_TROUBLESHOOTING.md"
        echo "📖 Deployment guide: RAILWAY_DEPLOYMENT.md"
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                    🛑 DEPLOYMENT ABORTED                              ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
        exit 1
    fi

    # CRITICAL: Check LOCAL_TEST is False in production
    if [ "$LOCAL_TEST" = "True" ] || [ "$LOCAL_TEST" = "true" ] || [ "$LOCAL_TEST" = "TRUE" ]; then
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                    🚨 CRITICAL DATABASE ERROR 🚨                      ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "❌ LOCAL_TEST=True detected in production Railway environment!"
        echo ""
        echo "This forces SQLite usage and WILL cause database errors in production."
        echo "Production MUST use PostgreSQL via DATABASE_URL."
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                         🔧 HOW TO FIX THIS                            ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "DELETE the LOCAL_TEST variable (it should NEVER exist in production):"
        echo "  1. Open: https://railway.app/project/$RAILWAY_PROJECT_ID/settings"
        echo "  2. Click: Variables tab"
        echo "  3. Find: LOCAL_TEST variable"
        echo "  4. Click: Delete (⨯) button"
        echo "  5. Redeploy automatically starts"
        echo ""
        echo "💡 TIP: LOCAL_TEST is only for local dev with SQLite - never use in production!"
        echo ""
        echo "📖 Full troubleshooting guide: RAILWAY_TROUBLESHOOTING.md"
        echo "📖 Deployment guide: RAILWAY_DEPLOYMENT.md"
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════════════╗"
        echo "║                    🛑 DEPLOYMENT ABORTED                              ║"
        echo "╚═══════════════════════════════════════════════════════════════════════╝"
        echo ""
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

    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║              ✅ PRODUCTION ENVIRONMENT VALIDATED                      ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✓ DEBUG is not True (production mode active)"
    echo "✓ LOCAL_TEST is not True (will use PostgreSQL)"
    echo "✓ DATABASE_URL is configured"
    echo "✓ SECRET_KEY is set"
    if [ -n "$SENTRY_DSN" ]; then
        echo "✓ Sentry error monitoring enabled"
    fi
    echo ""
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
