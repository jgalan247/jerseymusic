# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jersey Events is a Django-based ticketing platform for events in Jersey. The platform charges event organizers a listing fee (£15/event) and enables them to sell tickets through an integrated payment system. Key features include event management, ticket sales with QR codes and PDF generation, session-based shopping cart, SumUp payment integration (both platform-wide and per-artist OAuth), email verification, and analytics.

## Development Commands

### Core Django Commands
```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### Testing
```bash
# Run all tests
make test
# or
python run_tests.py --type all

# Run specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-e2e          # End-to-end tests (requires MailHog)
pytest -m unit -v      # Direct pytest for unit tests

# Run tests with coverage
make test-coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run tests for specific app
make test-app  # Will prompt for app name
pytest accounts/tests -v  # Direct app testing

# Run failed tests only
make test-failed
pytest --lf
```

### Frontend/Styling
```bash
# Build Tailwind CSS (if needed)
npx tailwindcss build
```

### Development Server with HTTPS (for SumUp testing)
```bash
# Using ngrok tunnel for external payment testing
./dev-tunnel.sh

# HTTPS server for local development (creates self-signed certificate)
python events/management/commands/runserver_https.py
```

## Architecture

### Django Apps Structure
- **events/**: Main event management with Event, Ticket, ListingFee models. Includes ticket generation with QR codes/PDFs, validation views, and listing fee payment flows
- **accounts/**: Custom User model (email-based auth, no username), CustomerProfile, ArtistProfile with SumUp OAuth integration fields
- **cart/**: Session-based shopping cart (no user login required). Uses `cart` session key with context processor for global access
- **orders/**: Order model linking customers to tickets, refund processing
- **payments/**: SumUp integration hub - includes `sumup.py` (API client), multiple payment flows (widget, redirect, simple checkout), transaction/refund handling
- **subscriptions/**: Artist subscription management (legacy, may not be active)
- **analytics/**: Event analytics dashboard

### Key Configuration
- **Settings**: `events/settings.py` - Main Django settings with payment provider configuration
- **Database**: SQLite3 by default, PostgreSQL configuration available
- **Static Files**: Tailwind CSS + custom styling in `/static/`
- **Templates**: Global templates in `/templates/`, app-specific in each app's `/templates/`

### Payment System Architecture
The payment system has evolved through multiple iterations (see SUMUP_*.md files for history). Current implementation:

**SumUp Integration (Primary)**:
- **Platform-wide payments**: `payments/sumup.py::create_checkout_simple()` uses client credentials (merchant code) for listing fees and general payments
- **Per-artist OAuth**: `accounts.ArtistProfile` stores OAuth tokens, enabling artists to receive payments directly via `create_checkout_for_artist()`
- **Token management**: Platform tokens cached, artist tokens include expiry/refresh logic
- **Security**: All payment amounts validated server-side with `expected_amount` parameter (see payments/sumup.py:189)

**Payment Flows**:
1. **Widget checkout** (`payments/widget_views.py`): JavaScript SDK embedded checkout
2. **Redirect checkout** (`payments/redirect_views.py`): Full-page redirect to SumUp hosted checkout
3. **Simple checkout** (`payments/simple_checkout.py`): Programmatic API-only approach

**Alternative Providers** (configured via `PAYMENT_PROVIDER` env var):
- **Stripe**: Alternative payment processing
- **CityPay**: Monthly subscriptions (may be legacy)

**Critical Files**:
- `payments/sumup.py`: Core API client and authentication
- `payments/services.py`: High-level payment service layer
- `events/listing_fee_views.py`: Listing fee payment flow

### Email Configuration
- **Development**: MailHog (localhost:1025) or console backend
- **Production**: Google Workspace SMTP
- Uses `.env` file for configuration

### Testing Framework
- **pytest** with Django integration
- **Test markers**: `unit`, `integration`, `e2e`, `slow`, `smoke`
- **Test structure**: Each app has `/tests/` directory with organized test files
- **Coverage**: HTML reports generated in `/htmlcov/`
- **E2E tests**: Located in `/tests/e2e/` for full user journey testing

### User Authentication & Profiles
- **Custom User model**: `accounts.User` with email-only auth (no username field)
- **User types**: `customer` or `artist` via `user_type` field
- **Profile pattern**: Separate `CustomerProfile` and `ArtistProfile` models (OneToOne with User)
- **Email verification**: `EmailVerificationToken` model + `accounts.middleware.EmailVerificationMiddleware`
- **Custom manager**: `UserManager` handles user/superuser creation with email

### Ticket System
- **Ticket generation**: `events.Ticket` model with auto-generated QR codes (via qrcode library) and PDF tickets (via xhtml2pdf)
- **Validation**: Tickets have `validation_hash`, `qr_data`, `is_validated` fields for entry scanning
- **Order relationship**: Tickets link to `orders.Order` for payment tracking
- **PDF generation**: `events/ticket_generator.py` creates downloadable PDF tickets with QR codes

## Development Workflow

1. **Initial Setup**:
   - Copy `.env.example` to `.env` and configure (especially `SECRET_KEY`, `DEBUG=True`, `LOCAL_TEST=True` for SQLite)
   - Run `python manage.py migrate`
   - Create superuser: `python manage.py createsuperuser`

2. **Local Development**:
   - Standard: `python manage.py runserver`
   - For SumUp testing: Use `./dev-tunnel.sh` to create ngrok tunnel with HTTPS

3. **Testing Workflow**:
   - Run tests before committing: `make test` or `pytest`
   - For email testing: Start MailHog with `make mailhog`, view at http://localhost:8025
   - Payment testing: Use SumUp test cards documented in test files

4. **Production Deployment**:
   - Set `DEBUG=False` and `LOCAL_TEST=False`
   - Configure PostgreSQL via `DATABASE_URL` or explicit postgres env vars
   - Set `SECRET_KEY`, `SUMUP_*` credentials, email provider
   - Run `python manage.py collectstatic`
   - See `DEPLOYMENT_CHECKLIST.md` for full production readiness

## Important Architectural Patterns

### Session Management
- **Cart storage**: Session-based with `cart` key containing list of `{event_id, quantity}` dicts
- **Context processor**: `cart.context_processors.cart_context` makes cart globally available in templates
- **Session config**: `SESSION_SAVE_EVERY_REQUEST = True` ensures cart persistence

### URL Organization
- **Main URLs**: `events/urls.py` (project root URLconf)
- **App URLs**: Each app has `urls.py` with `app_name` for namespacing (e.g., `events:detail`, `accounts:login`)
- **Payment URLs**: Multiple payment URL patterns in `payments/urls.py` for different checkout flows

### Template Inheritance
- **Base template**: `templates/base.html` with Tailwind CSS styling
- **App templates**: Each app uses `app_name/template_name.html` convention
- **Context**: Cart context available everywhere via context processor

### Database Conventions
- **Soft deletes**: Not used - models use Django's standard deletion
- **Slugs**: Auto-generated in `save()` methods for Event and Category
- **Unique constraints**: Used extensively (e.g., `ticket_number`, `payment_reference`)
- **Jersey-specific**: Parish choices for addresses, postcode field

### Error Handling & Monitoring
- **Sentry integration**: Enabled when `DEBUG=False` and `SENTRY_DSN` set (see settings.py:14-52)
- **Structured logging**: Separate loggers for `payment_audit`, `payment_debug`, `security`, `tickets`, `cart`
- **Payment audit trail**: All payment operations logged to `payment_audit` logger with user context

### Security Notes
- **CSRF**: Trusted origins configured for ngrok in development (settings.py:251)
- **Amount validation**: Payment functions require `expected_amount` parameter to prevent tampering
- **Token rotation**: SumUp platform tokens cached, artist tokens have expiry/refresh
- **Production security**: HTTPS enforcement, secure cookies, HSTS headers when `DEBUG=False`