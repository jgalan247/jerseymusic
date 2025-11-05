#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting Railway build process..."

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗄️ Running database migrations..."
python manage.py migrate --no-input

echo "✅ Build completed successfully!"
