#!/usr/bin/env bash
# Railway startup script - runs migrations and starts the web server

set -e  # Exit on error

echo "🚀 Starting Jersey Music application..."

# Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Start the web server with graceful shutdown handling
echo "🌐 Starting gunicorn web server with graceful shutdown handling..."
exec gunicorn events.wsgi:application --config gunicorn.conf.py
