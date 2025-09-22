import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal  # Add this import for subscription pricing

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if h.strip()]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local apps
    'accounts',
    'artworks',
    'cart',
    'orders',
    'payments',
    'subscriptions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'artworks.urls'

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

WSGI_APPLICATION = 'artworks.wsgi.application'

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "jersey_artwork"),
        "USER": os.getenv("POSTGRES_USER", "jersey"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "secret"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

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
# SUBSCRIPTION CONFIGURATION
# ============================================
SUBSCRIPTION_CONFIG = {
    'MONTHLY_PRICE': Decimal(os.environ.get('ARTIST_SUBSCRIPTION_PRICE', '15.00')),
    'CURRENCY': os.environ.get('SUBSCRIPTION_CURRENCY', 'GBP'),
    'TRIAL_DAYS': int(os.environ.get('SUBSCRIPTION_TRIAL_DAYS', '14')),
    'GRACE_PERIOD_DAYS': int(os.environ.get('SUBSCRIPTION_GRACE_PERIOD', '3')),
    'FEATURES': {
        'MAX_ARTWORKS': int(os.environ.get('MAX_ARTWORKS_PER_ARTIST', '100')),
        'FEATURED_LISTINGS': int(os.environ.get('FEATURED_LISTINGS', '3')),
        'COMMISSION_RATE': Decimal('0.00'),  # No commission in subscription model
    }
}

# ============================================
# PAYMENT CONFIGURATION
# ============================================

# Payment Provider Selection
PAYMENT_PROVIDER = os.environ.get('PAYMENT_PROVIDER', 'sumup')  # 'sumup', 'stripe', or 'citypay'

# SumUp Configuration (for one-time artwork purchases)
SUMUP_BASE_URL = os.getenv("SUMUP_BASE_URL", "https://api.sumup.com")
SUMUP_API_URL = os.getenv("SUMUP_API_URL", "https://api.sumup.com/v0.1")
SUMUP_CLIENT_ID = os.getenv("SUMUP_CLIENT_ID")
SUMUP_CLIENT_SECRET = os.getenv("SUMUP_CLIENT_SECRET")
SUMUP_MERCHANT_CODE = os.getenv("SUMUP_MERCHANT_CODE")
SUMUP_ACCESS_TOKEN = os.getenv("SUMUP_ACCESS_TOKEN")
SUMUP_API_KEY = os.getenv("SUMUP_API_KEY", "")
SUMUP_MERCHANT_ID = os.getenv("SUMUP_MERCHANT_ID", "")
SUMUP_REDIRECT_URI = os.getenv("SUMUP_REDIRECT_URI")  # e.g. https://your.site/payments/sumup/callback/
SUMUP_SUCCESS_URL = os.getenv("SUMUP_SUCCESS_URL", "/payments/success/")
SUMUP_FAIL_URL = os.getenv("SUMUP_FAIL_URL", "/payments/fail/")

# CityPay Configuration (alternative for monthly subscriptions)
CITYPAY_BASE_URL = os.getenv("CITYPAY_BASE_URL", "https://api.citypay.com")
CITYPAY_MERCHANT_ID = os.getenv("CITYPAY_MERCHANT_ID")
CITYPAY_LICENCE = os.getenv("CITYPAY_LICENCE")  # API key / licence code

# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_USE_MAILHOG = os.environ.get('USE_MAILHOG', 'True') == 'True'  # Default to MailHog in development

if DEBUG and EMAIL_USE_MAILHOG:
    # MailHog Configuration for Development
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025  # MailHog SMTP port
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    print("📧 Using MailHog for emails (localhost:1025)")
    print("   View emails at: http://localhost:8025")
    
elif DEBUG:
    # Console backend for development (if MailHog is not available)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("📧 Using Console backend for emails (check terminal output)")
    
else:
    # Google Workspace Configuration for Production
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')     
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    
    # For Google Workspace, you need an app-specific password:
    # 1. Go to https://myaccount.google.com/security
    # 2. Enable 2-factor authentication
    # 3. Generate an app-specific password
    # 4. Use that password here (not your regular password)

# Default email settings
DEFAULT_FROM_EMAIL = 'Jersey Artwork <noreply@coderra.je>'
EMAIL_SUBJECT_PREFIX = '[Jersey Artwork] '
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email verification settings
EMAIL_VERIFICATION_TIMEOUT = 48  # Hours before verification link expires