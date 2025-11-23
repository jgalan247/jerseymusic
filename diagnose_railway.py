#!/usr/bin/env python3
"""
Railway Deployment Diagnostic Script
Run this to check for common deployment issues
"""
import os
import sys

def check_environment():
    """Check critical environment variables"""
    print("=" * 60)
    print("🔍 ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)

    critical_vars = {
        'SECRET_KEY': 'Required for Django',
        'DATABASE_URL': 'Required for PostgreSQL connection',
        'PORT': 'Required for Railway binding',
    }

    optional_vars = {
        'SENTRY_DSN': 'Optional - Error monitoring',
        'SUMUP_CLIENT_ID': 'Required for payments',
        'SUMUP_CLIENT_SECRET': 'Required for payments',
        'SUMUP_MERCHANT_CODE': 'Required for payments',
    }

    print("\n✓ Critical Variables:")
    issues = []
    for var, desc in critical_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: Set ({desc})")
        else:
            print(f"  ❌ {var}: MISSING ({desc})")
            issues.append(var)

    print("\n📋 Optional Variables:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        status = "✅ Set" if value else "⚠️  Not set"
        print(f"  {status} {var}: {desc}")

    print("\n📊 Configuration:")
    print(f"  DEBUG: {os.getenv('DEBUG', 'False')}")
    print(f"  LOCAL_TEST: {os.getenv('LOCAL_TEST', 'False')}")
    print(f"  RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
    print(f"  ALLOWED_HOSTS: {os.getenv('ALLOWED_HOSTS', 'not set')}")

    return issues

def check_python_syntax():
    """Check for Python syntax errors in critical files"""
    print("\n" + "=" * 60)
    print("🐍 PYTHON SYNTAX CHECK")
    print("=" * 60)

    critical_files = [
        'events/settings.py',
        'events/wsgi.py',
        'events/urls.py',
        'events/views.py',
        'events/app_urls.py',
    ]

    errors = []
    for filepath in critical_files:
        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filepath, 'exec')
            print(f"  ✅ {filepath}")
        except SyntaxError as e:
            print(f"  ❌ {filepath}: {e}")
            errors.append((filepath, str(e)))
        except FileNotFoundError:
            print(f"  ⚠️  {filepath}: File not found")

    return errors

def check_imports():
    """Check if critical Python packages can be imported"""
    print("\n" + "=" * 60)
    print("📦 IMPORT CHECK")
    print("=" * 60)

    critical_imports = [
        ('django', 'Django framework'),
        ('gunicorn', 'WSGI server'),
        ('psycopg', 'PostgreSQL adapter'),
        ('sentry_sdk', 'Error monitoring'),
        ('whitenoise', 'Static file serving'),
        ('requests', 'HTTP library'),
        ('qrcode', 'QR code generation'),
    ]

    errors = []
    for module, desc in critical_imports:
        try:
            __import__(module)
            print(f"  ✅ {module}: {desc}")
        except ImportError as e:
            print(f"  ❌ {module}: FAILED - {e}")
            errors.append((module, str(e)))

    return errors

def check_django_config():
    """Check Django configuration"""
    print("\n" + "=" * 60)
    print("⚙️  DJANGO CONFIGURATION CHECK")
    print("=" * 60)

    # Set minimal environment for Django import
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
    os.environ.setdefault('SECRET_KEY', 'diagnostic-test-key')
    os.environ.setdefault('LOCAL_TEST', 'True')
    os.environ.setdefault('DEBUG', 'True')

    try:
        import django
        print(f"  ✅ Django version: {django.get_version()}")

        django.setup()
        print("  ✅ Django setup completed")

        from django.conf import settings
        print(f"  ✅ INSTALLED_APPS: {len(settings.INSTALLED_APPS)} apps")
        print(f"  ✅ MIDDLEWARE: {len(settings.MIDDLEWARE)} middleware")
        print(f"  ✅ ROOT_URLCONF: {settings.ROOT_URLCONF}")

        # Try importing URL config
        from django.urls import get_resolver
        resolver = get_resolver()
        print(f"  ✅ URL patterns loaded successfully")

        return []
    except Exception as e:
        print(f"  ❌ Django configuration error: {e}")
        import traceback
        traceback.print_exc()
        return [str(e)]

def check_database():
    """Check database connectivity"""
    print("\n" + "=" * 60)
    print("🗄️  DATABASE CHECK")
    print("=" * 60)

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("  ⚠️  DATABASE_URL not set (using SQLite for test)")
        return []

    print(f"  ✅ DATABASE_URL is set")

    # Parse DATABASE_URL (basic check)
    if database_url.startswith('postgres://') or database_url.startswith('postgresql://'):
        print("  ✅ PostgreSQL connection string detected")

        # Try to extract host info (basic parsing)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            print(f"  📋 Host: {parsed.hostname}")
            print(f"  📋 Port: {parsed.port or 5432}")
            print(f"  📋 Database: {parsed.path[1:] if parsed.path else 'unknown'}")
        except:
            pass
    else:
        print(f"  ⚠️  Unexpected database URL format")

    return []

def main():
    """Run all diagnostic checks"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     RAILWAY DEPLOYMENT DIAGNOSTIC TOOL                    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    all_issues = []

    # Run checks
    env_issues = check_environment()
    syntax_errors = check_python_syntax()
    import_errors = check_imports()
    django_errors = check_django_config()
    db_issues = check_database()

    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)

    total_issues = len(env_issues) + len(syntax_errors) + len(import_errors) + len(django_errors) + len(db_issues)

    if total_issues == 0:
        print("\n✅ All checks passed! Application should deploy successfully.")
        print("\nIf you're still seeing errors:")
        print("  1. Check Railway deployment logs for runtime errors")
        print("  2. Verify health check endpoint: /health/")
        print("  3. Check Sentry for error reports")
        print("  4. Verify gunicorn is binding to PORT correctly")
    else:
        print(f"\n❌ Found {total_issues} issue(s):")

        if env_issues:
            print(f"\n  Environment variables missing: {', '.join(env_issues)}")

        if syntax_errors:
            print(f"\n  Syntax errors in {len(syntax_errors)} file(s)")
            for filepath, error in syntax_errors:
                print(f"    - {filepath}: {error}")

        if import_errors:
            print(f"\n  Import errors for {len(import_errors)} package(s)")
            for module, error in import_errors:
                print(f"    - {module}: {error}")

        if django_errors:
            print(f"\n  Django configuration errors:")
            for error in django_errors:
                print(f"    - {error}")

        print("\n🔧 Recommended actions:")
        print("  1. Fix the issues listed above")
        print("  2. Commit and push changes")
        print("  3. Check Railway logs after redeployment")
        print("  4. Contact support if issues persist")

    print("\n" + "=" * 60)
    print()

    return 0 if total_issues == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
