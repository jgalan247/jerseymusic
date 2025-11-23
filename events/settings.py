import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal  # Add this import for subscription pricing

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# ERROR MONITORING WITH SENTRY
# ============================================
# Only enable Sentry in production (when DEBUG=False)
SENTRY_DSN = os.getenv('SENTRY_DSN')

if not os.getenv('DEBUG', 'False').lower() == 'true' and SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    # Configure Sentry for production
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='function_name',
                middleware_spans=True,
            ),
            sentry_logging,
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        send_default_pii=False,  # Don't send PII for GDPR compliance
        environment=os.getenv('ENVIRONMENT', 'production'),
        release=os.getenv('RELEASE_VERSION'),

        # Security: Don't send sensitive data
        before_send=lambda event, hint: event if not any(
            key in str(event).lower() for key in ['password', 'secret', 'token', 'api_key']
        ) else None,
    )

    print("✅ Sentry error monitoring enabled")
else:
    if not SENTRY_DSN:
        print("⚠️  WARNING: Sentry DSN not configured - no error monitoring in production!")

# ============================================
# CRITICAL SECURITY SETTINGS
# ============================================
# SECURITY WARNING: SECRET_KEY must be set in environment variables for production!
# Generate a strong key: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
if 'SECRET_KEY' not in os.environ and not os.getenv('LOCAL_TEST', False):
    raise ValueError(
        "SECRET_KEY environment variable is required! "
        "For production: generate a strong 50+ character key. "
        "For local dev only: set LOCAL_TEST=True"
    )
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key' if os.getenv('LOCAL_TEST') else None)

# SECURITY WARNING: DEBUG must be False in production!
# Only set DEBUG=True explicitly for development
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Log critical warning if DEBUG is True
if DEBUG:
    import sys
    print("⚠️  WARNING: DEBUG mode is enabled! Never use in production!", file=sys.stderr)

# ALLOWED_HOSTS configuration
# Supports Railway's automatic domain via RAILWAY_PUBLIC_DOMAIN or explicit ALLOWED_HOSTS env var
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]

# Add Railway-specific domains
# Railway health checks come from 'healthcheck.railway.app' - must be allowed
if os.getenv('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.append('healthcheck.railway.app')
    # Also allow wildcard for any Railway internal domains
    ALLOWED_HOSTS.append('.railway.app')
    ALLOWED_HOSTS.append('.railway.internal')
    print("✅ Added Railway health check domains to ALLOWED_HOSTS", file=sys.stderr)

# Add Railway's public domain if available
railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
if railway_domain and railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(railway_domain)
    print(f"✅ Added Railway public domain to ALLOWED_HOSTS: {railway_domain}", file=sys.stderr)

# Add Railway's static domain if available
railway_static_url = os.getenv('RAILWAY_STATIC_URL')
if railway_static_url:
    # Extract domain from URL (remove protocol)
    railway_static_domain = railway_static_url.replace('https://', '').replace('http://', '').split('/')[0]
    if railway_static_domain and railway_static_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(railway_static_domain)
        print(f"✅ Added Railway static domain to ALLOWED_HOSTS: {railway_static_domain}", file=sys.stderr)

# Log final ALLOWED_HOSTS configuration for debugging
if os.getenv('RAILWAY_ENVIRONMENT'):
    print(f"📋 Final ALLOWED_HOSTS: {ALLOWED_HOSTS}", file=sys.stderr)
# Site ID for django.contrib.sites
SITE_ID = 1

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Local apps
    'accounts',
    'events',
    'cart',
    'orders',
    'payments',
    'subscriptions',
    'analytics',
    # 'help',
]

# Conditionally add django_q for background task processing
# Only include when ENABLE_DJANGO_Q=True (for environments running qcluster worker)
# Railway web deployments don't need this since they don't run background workers
if os.getenv('ENABLE_DJANGO_Q', 'false').lower() == 'true':
    INSTALLED_APPS.append('django_q')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.EmailVerificationMiddleware',
]

ROOT_URLCONF = 'events.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_context',  
            ],
        },
    },
]

WSGI_APPLICATION = 'events.wsgi.application'

# Database Configuration
# ⚠️  CRITICAL: SQLite is for LOCAL TESTING ONLY!
# Production MUST use PostgreSQL or another production-grade database

import dj_database_url

# Check if we're in local test mode
LOCAL_TEST = os.getenv('LOCAL_TEST', 'False').lower() == 'true'

if LOCAL_TEST and DEBUG:
    # SQLite ONLY for local development/testing
    print("⚠️  Using SQLite for LOCAL TESTING ONLY - Never use in production!")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Production: Use PostgreSQL via DATABASE_URL or explicit config
    DATABASE_URL = os.getenv('DATABASE_URL')

    if DATABASE_URL:
        # Digital Ocean and most cloud providers set DATABASE_URL
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    else:
        # Fallback to explicit PostgreSQL configuration
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("POSTGRES_DB", "jersey_events"),
                "USER": os.getenv("POSTGRES_USER", "jersey"),
                "PASSWORD": os.getenv("POSTGRES_PASSWORD"),  # Required for production
                "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
                "PORT": os.getenv("POSTGRES_PORT", "5432"),
                "CONN_MAX_AGE": 600,
                "OPTIONS": {
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000"  # 30 second statement timeout
                }
            }
        }

    # Verify database is configured for production
    if not DEBUG and not DATABASE_URL and not os.getenv("POSTGRES_PASSWORD"):
        raise ValueError("Production requires DATABASE_URL or POSTGRES_PASSWORD to be set!")

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise configuration for serving static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Session configuration
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 86400  # 1 day

# ============================================
# SUBSCRIPTION CONFIGURATION (DEPRECATED - Using pay-per-event model)
# ============================================
# SUBSCRIPTION_CONFIG = {
#     'MONTHLY_PRICE': Decimal(os.environ.get('ARTIST_SUBSCRIPTION_PRICE', '15.00')),
#     'CURRENCY': os.environ.get('SUBSCRIPTION_CURRENCY', 'GBP'),
#     'TRIAL_DAYS': int(os.environ.get('SUBSCRIPTION_TRIAL_DAYS', '14')),
#     'GRACE_PERIOD_DAYS': int(os.environ.get('SUBSCRIPTION_GRACE_PERIOD', '3')),
#     'FEATURES': {
#         'MAX_ARTWORKS': int(os.environ.get('MAX_ARTWORKS_PER_ARTIST', '100')),
#         'FEATURED_LISTINGS': int(os.environ.get('FEATURED_LISTINGS', '3')),
#         'COMMISSION_RATE': Decimal('0.00'),  # No commission in subscription model
#     }
# }

# ============================================
# PAY-PER-EVENT PRICING CONFIGURATION
# ============================================
PLATFORM_CURRENCY = os.environ.get('PLATFORM_CURRENCY', 'GBP')

# Tier-based pricing structure
# Each tier has a capacity limit and a platform fee per ticket
PRICING_TIERS = [
    {
        'tier': 1,
        'capacity': int(os.environ.get('TIER_1_CAPACITY', '50')),
        'fee': Decimal(os.environ.get('TIER_1_FEE', '0.50')),
        'name': 'Small Event'
    },
    {
        'tier': 2,
        'capacity': int(os.environ.get('TIER_2_CAPACITY', '100')),
        'fee': Decimal(os.environ.get('TIER_2_FEE', '0.45')),
        'name': 'Medium Event'
    },
    {
        'tier': 3,
        'capacity': int(os.environ.get('TIER_3_CAPACITY', '250')),
        'fee': Decimal(os.environ.get('TIER_3_FEE', '0.40')),
        'name': 'Large Event'
    },
    {
        'tier': 4,
        'capacity': int(os.environ.get('TIER_4_CAPACITY', '400')),
        'fee': Decimal(os.environ.get('TIER_4_FEE', '0.35')),
        'name': 'Very Large Event'
    },
    {
        'tier': 5,
        'capacity': int(os.environ.get('TIER_5_CAPACITY', '500')),
        'fee': Decimal(os.environ.get('TIER_5_FEE', '0.30')),
        'name': 'Major Event'
    },
]

# Maximum capacity supported by automatic pricing
MAX_AUTO_CAPACITY = int(os.environ.get('MAX_AUTO_CAPACITY', '500'))

# Contact email for custom pricing (events >500)
CUSTOM_PRICING_EMAIL = os.environ.get('CUSTOM_PRICING_EMAIL', 'admin@coderra.je')

# SumUp processing rate (1.69%)
SUMUP_PROCESSING_RATE = Decimal(os.environ.get('SUMUP_PROCESSING_RATE', '0.0169'))


def get_pricing_tier(capacity):
    """
    Get the pricing tier for a given capacity.

    Args:
        capacity (int): Event capacity

    Returns:
        dict: Tier information with capacity, fee, and name
        None: If capacity exceeds MAX_AUTO_CAPACITY
    """
    if capacity > MAX_AUTO_CAPACITY:
        return None

    for tier in PRICING_TIERS:
        if capacity <= tier['capacity']:
            return tier

    # If we get here, capacity is within range but not matched
    # Return the highest tier
    return PRICING_TIERS[-1] if PRICING_TIERS else None

# ============================================
# PAYMENT CONFIGURATION
# ============================================

# CSRF Trusted Origins - for cross-origin POST requests (payments, etc.)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',  # Local development
    'http://127.0.0.1:8000',  # Local development (IP)
    'https://localhost:8000',  # Local HTTPS testing
]

# Add Railway's public domain if available
if railway_domain:
    CSRF_TRUSTED_ORIGINS.extend([
        f'https://{railway_domain}',
        f'http://{railway_domain}',  # Fallback, though Railway uses HTTPS
    ])

# Add Railway's static URL if available
if railway_static_url:
    # Ensure it has a scheme for Django 4.0+
    if not railway_static_url.startswith(('http://', 'https://')):
        railway_static_url = f'https://{railway_static_url}'
    if railway_static_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_static_url)

# Add custom CSRF origins from environment (comma-separated)
custom_csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if custom_csrf_origins:
    for origin in custom_csrf_origins.split(','):
        origin = origin.strip()
        if origin:
            # Django 4.0+ requires scheme (https:// or http://)
            # Auto-prepend https:// if missing
            if not origin.startswith(('http://', 'https://')):
                origin = f'https://{origin}'
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)

# Log CSRF trusted origins for debugging in Railway
if os.getenv('RAILWAY_ENVIRONMENT'):
    print(f"📋 CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)

# Payment Provider Selection
PAYMENT_PROVIDER = os.environ.get('PAYMENT_PROVIDER', 'sumup')  # 'sumup', 'stripe', or 'citypay'

# SumUp Configuration (for one-time event ticket purchases)
# ⚠️  CRITICAL SECURITY WARNING: Never hardcode credentials in code!
# All credentials MUST come from environment variables or secure vault
# Rotate all credentials before production deployment
SUMUP_API_URL = os.getenv("SUMUP_API_URL", "https://api.sumup.com/v0.1")
SUMUP_CLIENT_ID = os.getenv("SUMUP_CLIENT_ID")  # NEVER hardcode!
SUMUP_CLIENT_SECRET = os.getenv("SUMUP_CLIENT_SECRET")  # NEVER hardcode!
SUMUP_MERCHANT_CODE = os.getenv("SUMUP_MERCHANT_CODE")  # NEVER hardcode!
SUMUP_ACCESS_TOKEN = os.getenv("SUMUP_ACCESS_TOKEN")  # Rotate regularly
SUMUP_API_KEY = os.getenv("SUMUP_API_KEY", "")
SUMUP_MERCHANT_ID = os.getenv("SUMUP_MERCHANT_ID", "")


# Verify critical payment credentials are set for production
if not DEBUG and not all([SUMUP_CLIENT_ID, SUMUP_CLIENT_SECRET, SUMUP_MERCHANT_CODE]):
    import sys
    print("⚠️  CRITICAL: Missing SumUp credentials for production!", file=sys.stderr)

# SumUp OAuth redirect URI - must match the callback URL registered in SumUp dashboard
# For artist OAuth: https://your.site/accounts/sumup/callback/
# If not set, will be constructed from SITE_URL (requires SITE_URL to be set correctly)
SUMUP_REDIRECT_URI = os.getenv("SUMUP_REDIRECT_URI")
SUMUP_SUCCESS_URL = os.getenv("SUMUP_SUCCESS_URL", "/payments/success/")
SUMUP_FAIL_URL = os.getenv("SUMUP_FAIL_URL", "/payments/fail/")

# Derived URLs from single API URL
SUMUP_BASE_URL = SUMUP_API_URL.rsplit('/v0.1', 1)[0] if SUMUP_API_URL else "https://api.sumup.com"

# CityPay Configuration (alternative for monthly subscriptions)
CITYPAY_BASE_URL = os.getenv("CITYPAY_BASE_URL", "https://api.citypay.com")
CITYPAY_MERCHANT_ID = os.getenv("CITYPAY_MERCHANT_ID")
CITYPAY_LICENCE = os.getenv("CITYPAY_LICENCE")  # API key / licence code

# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_USE_MAILHOG = os.environ.get('USE_MAILHOG', 'False') == 'True'  # Changed default to False

# Email timeout and retry settings
EMAIL_TIMEOUT = 30  # seconds
DEFAULT_RETRY_DELAY = 1  # seconds between retries

if DEBUG and EMAIL_USE_MAILHOG:
    try:
        import socket
        # Test if MailHog is actually running
        sock = socket.create_connection(('localhost', 1025), timeout=1)
        sock.close()
        # MailHog is running
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'localhost'
        EMAIL_PORT = 1025
        EMAIL_USE_TLS = False
        EMAIL_USE_SSL = False
        EMAIL_HOST_USER = ''
        EMAIL_HOST_PASSWORD = ''
        print("📧 Using MailHog for emails (localhost:1025)")
        print("   View emails at: http://localhost:8025")
    except (socket.error, OSError):
        # MailHog is not running, fall back to console
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        print("📧 MailHog not available, using Console backend for emails")

elif DEBUG:
    # Console backend for development - more reliable
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("📧 Using Console backend for emails (check terminal output)")

else:
    # Production email configuration with multiple providers
    email_provider = os.getenv('EMAIL_PROVIDER', 'ses').lower()  # Default to Amazon SES

    if email_provider == 'resend':
        # Resend (Modern Email API)
        # Get API key from RESEND_API_KEY environment variable
        # Sign up at https://resend.com
        EMAIL_BACKEND = 'events.email_backend.ResendEmailBackend'
        RESEND_API_KEY = os.getenv('RESEND_API_KEY')
        if not RESEND_API_KEY:
            print("⚠️ WARNING: RESEND_API_KEY not configured!", file=sys.stderr)
        print("📧 Using Resend for production emails")

    elif email_provider == 'ses' or email_provider == 'amazon-ses':
        # Amazon SES (Simple Email Service)
        # Default to EU North (Stockholm) region - change EMAIL_SES_REGION to use different region
        ses_region = os.getenv('EMAIL_SES_REGION', 'eu-north-1')
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = f'email-smtp.{ses_region}.amazonaws.com'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_USE_SSL = False
        EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
        EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
        print(f"📧 Using Amazon SES for production emails (region: {ses_region})")

    elif email_provider == 'gmail':
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.gmail.com'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
        EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # App-specific password
        print("📧 Using Gmail for production emails")

    elif email_provider == 'sendgrid':
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.sendgrid.net'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = 'apikey'  # Always 'apikey' for SendGrid
        EMAIL_HOST_PASSWORD = os.getenv('SENDGRID_API_KEY')
        print("📧 Using SendGrid for production emails")

    elif email_provider == 'mailgun':
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.mailgun.org'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = os.getenv('MAILGUN_SMTP_USER')
        EMAIL_HOST_PASSWORD = os.getenv('MAILGUN_SMTP_PASSWORD')
        print("📧 Using Mailgun for production emails")

    else:
        # Fallback to console for production if no provider configured
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        print("⚠️ No email provider configured for production, using console backend")

# Default email settings
DEFAULT_FROM_EMAIL = 'Jersey Events <noreply@coderra.je>'
EMAIL_SUBJECT_PREFIX = '[Jersey Events] '
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email verification settings
EMAIL_VERIFICATION_TIMEOUT = 48  # Hours before verification link expires

# Site URL for payment callbacks and emails
SITE_URL = os.getenv('SITE_URL', 'https://1de8a13b06da.ngrok-free.app' if not DEBUG else 'http://127.0.0.1:8000')

# Auto-construct SUMUP_REDIRECT_URI from SITE_URL if not explicitly set
# This ensures the OAuth callback URL is always correct
if not SUMUP_REDIRECT_URI and SITE_URL:
    SUMUP_REDIRECT_URI = f"{SITE_URL.rstrip('/')}/accounts/sumup/callback/"
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print(f"✅ Auto-configured SUMUP_REDIRECT_URI: {SUMUP_REDIRECT_URI}", file=sys.stderr)

# ============================================
# TERMS & CONDITIONS CONFIGURATION
# ============================================
TERMS_VERSION = '1.0'  # Update this when T&C are modified
TERMS_UPDATED_DATE = '2025-10-09'  # Format: YYYY-MM-DD

# ============================================
# STRUCTURED LOGGING CONFIGURATION
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'payment_audit': {
            'format': '[PAYMENT AUDIT] {asctime} | Level: {levelname} | User: {user} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'security': {
            'format': '🔒 [SECURITY] {asctime} | {levelname} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        # Background task formatter (no user context)
        'background': {
            'format': '[POLLING] {asctime} | {levelname} | {name} | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'payment_audit': {
            'class': 'logging.StreamHandler',
            'formatter': 'payment_audit',
            'level': 'INFO',
        },
        'security': {
            'class': 'logging.StreamHandler',
            'formatter': 'security',
            'level': 'WARNING',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
        # Payment polling file handler
        'payment_polling_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/payment_polling.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'background',
        },
        # Payment polling console handler
        'payment_polling_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'background',
            'level': 'INFO',
        },
    },
    'loggers': {
        # Payment audit trail (for web requests with user context)
        'payment_audit': {
            'handlers': ['payment_audit', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Payment debugging
        'payment_debug': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Security logging
        'security': {
            'handlers': ['security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Payments app (web requests)
        'payments': {
            'handlers': ['console', 'payment_audit'],
            'level': 'INFO',
            'propagate': False,
        },
        # Payment polling service (background task - NO user context)
        'payments.polling_service': {
            'handlers': ['payment_polling_file', 'payment_polling_console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Ticket operations
        'tickets': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Cart operations
        'cart': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django core
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        # Django security
        'django.security': {
            'handlers': ['security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Database queries (only in DEBUG)
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG and os.getenv('SQL_DEBUG') else 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
# ============================================
# SECURITY CONFIGURATION FOR PAYMENT WIDGETS
# ============================================

# X-Frame-Options configuration for SumUp widget support
# Allow SumUp domains to iframe our payment pages
X_FRAME_OPTIONS = 'DENY'  # Default deny, override in specific views

# Exempt specific views from X-Frame-Options restrictions
# We'll use @xframe_options_exempt decorator on widget views
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Content Security Policy for SumUp integration
# Allow SumUp scripts and iframes
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for SumUp widget initialization
    "https://gateway.sumup.com",
    "https://api.sumup.com",
    "https://checkout.sumup.com",
)
CSP_FRAME_SRC = (
    "'self'",
    "https://gateway.sumup.com",
    "https://checkout.sumup.com",
)
CSP_CONNECT_SRC = (
    "'self'",
    "https://api.sumup.com",
    "https://gateway.sumup.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for widget styling
    "https://gateway.sumup.com",
)

# ============================================
# PRODUCTION SECURITY SETTINGS
# ============================================
if not DEBUG:
    # HTTPS enforcement
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Exempt health check from HTTPS redirect for Railway health checks
    # Railway's internal health checks use HTTP, not HTTPS
    # Match both /health/ and /health (with or without trailing slash)
    SECURE_REDIRECT_EXEMPT = [r'^health/', r'^/health/']

    # Session cookie security
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookies
    SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
    SESSION_COOKIE_NAME = 'je_sessionid'  # Custom name to avoid defaults
    SESSION_COOKIE_AGE = 3600  # 1 hour for payment processing security

    # CSRF cookie security
    CSRF_COOKIE_SECURE = True  # Only send CSRF cookie over HTTPS
    CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access
    CSRF_COOKIE_SAMESITE = 'Strict'  # Additional CSRF protection
    CSRF_COOKIE_NAME = 'je_csrftoken'  # Custom name

    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Additional security headers
    SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing
    SECURE_BROWSER_XSS_FILTER = True  # Enable browser XSS protection
    X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking (except for payment widgets)

    # Require HTTPS for all media/static in production
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    print("✅ Production security settings enabled")

# ============================================
# DJANGO-Q CONFIGURATION (Task Scheduling)
# ============================================
# Only configure Q_CLUSTER when django_q is enabled
# This prevents configuration errors when django_q is not in INSTALLED_APPS
if os.getenv('ENABLE_DJANGO_Q', 'false').lower() == 'true':
    Q_CLUSTER = {
        'name': 'JerseyEvents',
        'workers': 2 if not DEBUG else 1,
        'timeout': 300,  # 5 minutes per task
        'retry': 360,  # Retry failed tasks after 6 minutes
        'queue_limit': 50,
        'bulk': 10,  # Process up to 10 tasks at once
        'orm': 'default',  # Use default database for queue storage

        # Scheduling
        'save_limit': 250,  # Keep last 250 successful tasks
        'max_attempts': 1,  # Don't retry tasks automatically (we handle retries in polling)
        'catch_up': False,  # Don't catch up missed schedules on startup

        # Logging
        'log_level': 'INFO',

        # Security
        'cpu_affinity': 1 if not DEBUG else 0,  # Bind to CPU in production
        'label': 'Django Q Tasks',

        # Admin
        'django_redis': None,  # Not using Redis initially (ORM-based queue)
    }
    print("✅ Django-Q task scheduling enabled")

# Note: Email configuration is handled earlier in this file (lines 381-470)
# based on DEBUG mode and EMAIL_PROVIDER environment variable
# Amazon SES is the default provider for production (EMAIL_PROVIDER=ses)

# ============================================
# CSRF SETTINGS FOR DEVELOPMENT
# ============================================
if DEBUG:
    CSRF_COOKIE_SECURE = False  # Allow non-HTTPS in development
    SESSION_COOKIE_SECURE = False  # Allow non-HTTPS in development
    CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access in development
    CSRF_USE_SESSIONS = False  # Use cookie-based CSRF (default)
    CSRF_COOKIE_SAMESITE = 'Lax'  # More permissive for development