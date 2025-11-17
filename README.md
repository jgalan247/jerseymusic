# Jersey Events - Ticketing Platform

**Version:** 2.0
**Status:** Production Ready
**Last Updated:** 9 October 2025

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Pricing Model](#pricing-model)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Admin Guide](#admin-guide)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [Support](#support)

---

## 🎯 Overview

Jersey Events is a modern, transparent ticketing platform designed specifically for event organizers in Jersey, Channel Islands. Built with Django 4.2+, the platform offers:

- **Pay-Per-Event Model** - No monthly subscriptions, pay only when you sell tickets
- **Tier-Based Pricing** - £0.30-£0.50 per ticket (based on capacity)
- **Multi-Tier Ticketing** - VIP, Standard, Child, Concession, and more
- **Processing Fee Flexibility** - Organizers choose who pays the 1.69% SumUp fee
- **Comprehensive Admin** - Powerful management interface
- **Legal Compliance** - Full T&C acceptance tracking with IP logging

### Why Jersey Events?

| Feature | Jersey Events | Eventbrite |
|---------|---------------|------------|
| **Platform Fee** | £0.30-£0.50 per ticket | 6.95% + £0.59 |
| **Processing Fee** | 1.69% (optional) | 2.9% + £0.30 |
| **Monthly Subscription** | ✗ None | ✗ None |
| **Local Support** | ✓ Jersey-based | ✗ International |
| **Direct Payouts** | ✓ Yes | ✓ Yes |
| **Typical Savings** | - | **70-75% cheaper** |

**Example:** For a 100-ticket event at £25/ticket:
- **Jersey Events:** £87.25 in fees (3.5% of revenue)
- **Eventbrite:** £335.25 in fees (13.4% of revenue)
- **Your Savings:** £248.00 (74% reduction)

---

## ✨ Key Features

### For Event Organizers

- **🎫 Multi-Tier Ticketing** - Create VIP, Standard, Child, Concession, Student, Group, and Early Bird tiers
- **💰 Transparent Pricing** - Flat per-ticket fee (£0.30-£0.50) based on event capacity
- **📊 Real-Time Analytics** - Track sales, revenue, and capacity in real-time
- **💳 Flexible Payment Processing** - Choose whether customers or organizers pay the 1.69% SumUp fee
- **📧 Automated Emails** - Order confirmations, ticket delivery, and organizer notifications
- **🔍 QR Code Validation** - Secure ticket validation at venue entrance
- **📱 Mobile-Friendly** - Works perfectly on all devices

### For Customers

- **🎟️ Digital Tickets** - PDF tickets with QR codes delivered instantly
- **💳 Secure Payments** - PCI-compliant payment processing via SumUp
- **📧 Email Confirmations** - Detailed order confirmations with tier information
- **🔒 Legal Protection** - T&C acceptance with IP logging for dispute resolution
- **📱 Mobile Tickets** - Show QR codes on your phone at the venue

### For Administrators

- **🎨 Visual Admin Interface** - Beautiful, feature-rich Django admin
- **📈 Fee Breakdown Display** - Automatic calculations and revenue projections
- **🎫 Tier Management** - Inline editing and standalone tier admin
- **📊 Progress Bars** - Visual ticket availability indicators
- **✅ T&C Tracking** - Complete legal compliance records
- **🔍 Advanced Filtering** - Filter by tier, status, validation, and more

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+ (or SQLite for development)
- pip and virtualenv
- Git

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/jersey_events.git
cd jersey_events

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
cp .env.example .env

# 5. Edit .env with your settings
nano .env  # or your preferred editor

# 6. Run migrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver

# 9. Visit http://localhost:8000/admin
```

**Done!** Your Jersey Events instance is running.

---

## 💵 Pricing Model

### Tier-Based Platform Fees

Jersey Events uses capacity-based pricing tiers:

| Tier | Capacity | Platform Fee | Example Event |
|------|----------|--------------|---------------|
| **Tier 1** | Up to 50 | £0.50/ticket | Small Gig |
| **Tier 2** | Up to 100 | £0.45/ticket | Local Concert |
| **Tier 3** | Up to 250 | £0.40/ticket | Club Night |
| **Tier 4** | Up to 400 | £0.35/ticket | Large Event |
| **Tier 5** | Up to 500 | £0.30/ticket | Major Festival |
| **Custom** | 500+ | Contact admin@coderra.je | Arena Events |

### Processing Fee Options

Organizers can choose who pays the 1.69% SumUp processing fee:

**Option A - Customer Pays (Recommended):**
- Base ticket: £25.00
- Processing fee: £0.42 (added to price)
- **Customer pays:** £25.42
- **Organizer receives:** £24.55 (after £0.45 platform fee)

**Option B - Organizer Absorbs:**
- Base ticket: £25.00
- Processing fee: £0.42 (deducted from revenue)
- **Customer pays:** £25.00
- **Organizer receives:** £24.13 (after both fees)

**Difference:** £0.42 more per ticket when customers pay the processing fee.

### Example Calculations

**100-ticket event at £25/ticket:**

```
Tier 2 (up to 100 capacity)
Platform Fee: £0.45/ticket

If Customer Pays Processing Fee:
├─ Customer Price:       £25.42/ticket (£25 + £0.42)
├─ Platform Fee:         £0.45/ticket
├─ Processing Fee:       £0.42/ticket (customer pays)
└─ Organizer Receives:   £24.55/ticket

Total Revenue (100 tickets):
├─ Gross Revenue:        £2,542.00
├─ Platform Fees:        £45.00
└─ Organizer Net:        £2,455.00

If Organizer Absorbs Processing Fee:
├─ Customer Price:       £25.00/ticket
├─ Platform Fee:         £0.45/ticket
├─ Processing Fee:       £0.42/ticket (organizer pays)
└─ Organizer Receives:   £24.13/ticket

Total Revenue (100 tickets):
├─ Gross Revenue:        £2,500.00
├─ Platform Fees:        £45.00
├─ Processing Fees:      £42.00
└─ Organizer Net:        £2,413.00
```

---

## 🎫 Multi-Tier Ticketing

### Available Ticket Tiers

Create multiple ticket types for a single event:

| Tier Type | Typical Use | Example Price |
|-----------|-------------|---------------|
| **VIP** | Premium access, perks | £75.00 |
| **Standard** | General admission | £25.00 |
| **Child** | Ages 12 and under | £15.00 |
| **Concession** | Seniors, disabled | £20.00 |
| **Elderly** | Senior citizens | £20.00 |
| **Student** | Valid student ID | £20.00 |
| **Group** | 10+ tickets | £22.00 |
| **Early Bird** | Limited quantity | £20.00 |

### Tier Configuration

Each tier can have:
- ✅ Custom name and description
- ✅ Individual pricing
- ✅ Separate inventory tracking
- ✅ Min/max purchase limits (1-100 tickets)
- ✅ Sort order for display
- ✅ Active/inactive toggle

**Example Event Setup:**
```
Event: Summer Music Festival 2025
Capacity: 250 tickets (Tier 3 - £0.40 platform fee)

Tier Configuration:
├─ VIP (20 tickets) - £60.00
│  └─ Includes backstage pass and meet & greet
├─ Standard (180 tickets) - £30.00
│  └─ General admission
├─ Child (30 tickets) - £18.00
│  └─ Ages 12 and under
└─ Early Bird (20 tickets) - £25.00
   └─ First 20 tickets sold
```

---

## ⚙️ Configuration

### Environment Variables

Key configuration in `.env`:

```bash
# ============================================
# PAY-PER-EVENT PRICING CONFIGURATION
# ============================================

# Platform Fees Per Tier (in GBP)
TIER_1_CAPACITY=50
TIER_1_FEE=0.50

TIER_2_CAPACITY=100
TIER_2_FEE=0.45

TIER_3_CAPACITY=250
TIER_3_FEE=0.40

TIER_4_CAPACITY=400
TIER_4_FEE=0.35

TIER_5_CAPACITY=500
TIER_5_FEE=0.30

# Maximum capacity for automatic pricing
MAX_AUTO_CAPACITY=500

# Contact for custom pricing (>500 capacity)
CUSTOM_PRICING_EMAIL=admin@coderra.je

# SumUp processing rate (1.69%)
SUMUP_PROCESSING_RATE=0.0169

# ============================================
# PAYMENT CONFIGURATION
# ============================================

PAYMENT_PROVIDER=sumup
SUMUP_MERCHANT_CODE=your_merchant_code
SUMUP_ACCESS_TOKEN=your_access_token

# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-app-specific-password
```

### Changing Pricing

To change platform fees:

1. Edit `.env` file (e.g., change `TIER_1_FEE=0.50` to `TIER_1_FEE=0.60`)
2. Restart Django server
3. New events use new pricing
4. Existing events keep original pricing

**No code changes required!**

---

## 📖 Usage Guide

### For Event Organizers

#### Creating an Event

1. **Register as Organizer:**
   - Visit `/accounts/register/organiser/`
   - Fill in your details
   - Verify your email

2. **Create Event:**
   - Go to "Create Event" in your dashboard
   - Fill in event details:
     - Title, description, category
     - Venue name and address
     - Date and time
     - Capacity (1-500)
     - Base ticket price
   - Choose processing fee option:
     - ☐ Pass processing fee to customer (+£0.42 per £25 ticket)
     - ☑ Absorb processing fee (deducted from revenue)

3. **Add Ticket Tiers (Optional):**
   - Click "Add Tier" in the event form
   - Configure each tier:
     - Type (VIP, Standard, Child, etc.)
     - Name and description
     - Price and quantity
     - Min/max purchase limits

4. **Publish Event:**
   - Save as "Draft" to preview
   - Set to "Published" when ready
   - Event appears on public listings

#### Managing Sales

- **View Dashboard:** Track tickets sold, revenue, and capacity
- **Check Orders:** See all customer orders for your events
- **Monitor Tiers:** Track which tiers are selling fastest
- **Download Reports:** Export sales data for accounting

### For Customers

#### Buying Tickets

1. **Browse Events:** Visit homepage or events listing
2. **Select Event:** Click event for details
3. **Choose Tier:** Select ticket type (if multiple tiers)
4. **Add to Cart:** Choose quantity and add to cart
5. **Checkout:**
   - Enter your details
   - Accept Terms & Conditions
   - Choose payment method
6. **Payment:** Complete secure payment via SumUp
7. **Receive Tickets:** Check email for PDF tickets with QR codes

#### Using Tickets

1. **Save Tickets:** Save email or take screenshot of QR codes
2. **Arrive Early:** Get to venue 15 minutes before event
3. **Present QR Code:** Show QR code at entrance
4. **Entry Validated:** Staff scans code for entry

---

## 🔧 Admin Guide

### Admin Interface Overview

Access admin at `/admin/` with superuser credentials.

### Event Management

**List View Features:**
- Pricing tier badge (Tier 1-5)
- Processing fee indicator (Customer Pays / Organizer Absorbs)
- Tickets sold / capacity
- Status (Draft, Published, Sold Out)
- Date hierarchy navigation

**Detail View Features:**
- Complete fee breakdown per ticket
- Revenue projections (if sold out)
- Inline ticket tier management
- Capacity validation
- Processing fee toggle

**Fee Breakdown Display:**
```
╔════════════════════════════════════════╗
║ 💰 Fee Breakdown (Per Ticket):        ║
╠════════════════════════════════════════╣
║ Pricing Tier:     Medium Event (Tier 2)║
║ Base Ticket:      £25.00              ║
║ Platform Fee:     £0.45               ║
║ Processing Fee:   £0.42               ║
║ Customer Pays:    £25.42              ║
║ Organizer Gets:   £24.55              ║
╠════════════════════════════════════════╣
║ 📊 Full Event Projection:             ║
║ Total Capacity:   100 tickets         ║
║ Tickets Sold:     45 (45%)            ║
║ Est. Revenue:     £2,455.00           ║
╚════════════════════════════════════════╝
```

### Ticket Tier Management

**Standalone Admin:**
- View all tiers across all events
- Visual progress bars (green/orange/red)
- Filter by tier type, status, event
- Bulk management

**Inline Editing:**
- Add/edit tiers directly in event admin
- Real-time capacity tracking
- Validation on save

**Progress Bar Colors:**
- 🟢 Green: >10 tickets remaining
- 🟠 Orange: <10 tickets remaining
- 🔴 Red: Sold out

### Order Management

**T&C Tracking:**
- Checkmark in list view (✓ Accepted / ✗ Not Accepted)
- Full legal record in detail view:
  - Acceptance date/time
  - T&C version
  - IP address
  - Legal compliance notice

**Filters:**
- Status (Pending, Confirmed, Cancelled)
- Payment status (Paid / Unpaid)
- T&C acceptance (Yes / No)
- Date range

### Ticket Validation

**Validation Tracking:**
- Validation status with timestamp
- Validated by (staff member)
- Filter by validated/not validated
- Tier display on each ticket

---

## 🧪 Testing

### Run All Tests

```bash
# Run complete test suite
python manage.py test

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific app tests
python manage.py test events
python manage.py test orders
python manage.py test payments
```

### Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e
```

### Critical Test Scenarios

1. **Event Creation:**
   - ✅ Capacity validation (1-500)
   - ✅ Pricing tier assignment
   - ✅ Tier total capacity validation

2. **Checkout:**
   - ✅ T&C acceptance required
   - ✅ Email validation with typo detection
   - ✅ Ticket availability checks
   - ✅ Tier capacity validation

3. **Payment:**
   - ✅ SumUp integration
   - ✅ Order confirmation emails
   - ✅ Ticket generation with QR codes

4. **Admin:**
   - ✅ Fee breakdown calculations
   - ✅ Tier progress bars
   - ✅ T&C acceptance display

---

## 🚀 Deployment

### 📖 Deployment Guides

**🚂 For Railway Deployment:** See **[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)** - Complete step-by-step guide with environment variables and troubleshooting.

**📋 General Checklist:** See **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production readiness across all platforms.

### Production Checklist

- [ ] Set `DEBUG=False` (or don't set it - defaults to False)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY` (generate with Django's `get_random_secret_key()`)
- [ ] Configure PostgreSQL database
- [ ] Set up email (Google Workspace or SendGrid)
- [ ] Configure SumUp credentials
- [ ] Set up Sentry for error monitoring
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Set up SSL/TLS certificate
- [ ] Configure domain and DNS
- [ ] Configure backups

### Deployment Options

**Option 1: Railway (Recommended for Easy Deployment)**
- Quick setup with PostgreSQL auto-provisioning
- Automatic HTTPS and deployments
- See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- Environment validation in startup script

**Option 2: Traditional VPS (Recommended for Jersey)**
- DigitalOcean / Linode / Vultr
- Nginx + Gunicorn
- PostgreSQL database
- SSL via Let's Encrypt

**Option 3: Other PaaS**
- Heroku
- Render
- Similar to Railway setup

**Option 4: Docker**
- Docker Compose included
- Easy container deployment

---

## 📚 Additional Documentation

- **[PLATFORM_UPGRADE_COMPLETE.md](PLATFORM_UPGRADE_COMPLETE.md)** - Complete upgrade overview
- **[VALIDATION_IMPLEMENTATION_COMPLETE.md](VALIDATION_IMPLEMENTATION_COMPLETE.md)** - Validation system details
- **[ADMIN_INTERFACE_UPDATE_COMPLETE.md](ADMIN_INTERFACE_UPDATE_COMPLETE.md)** - Admin interface guide
- **[EMAIL_TEMPLATES_UPDATE_COMPLETE.md](EMAIL_TEMPLATES_UPDATE_COMPLETE.md)** - Email system documentation
- **[ORGANIZER_GUIDE.md](ORGANIZER_GUIDE.md)** - Guide for event organizers
- **[.env.example](.env.example)** - Complete configuration reference

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards

- Follow PEP 8 for Python code
- Write tests for new features
- Update documentation
- Use meaningful commit messages

---

## 📞 Support

### Contact

- **Email:** support@jerseyevents.co.uk
- **Technical Support:** admin@coderra.je
- **Custom Pricing (>500):** admin@coderra.je

### Documentation

- **GitHub:** https://github.com/yourusername/jersey_events
- **Issues:** https://github.com/yourusername/jersey_events/issues

### Office Hours

Monday - Friday: 9:00 AM - 5:00 PM (GMT)
Response time: Within 24 hours

---

## 📄 License

Copyright © 2025 Jersey Events / Coderra
All rights reserved.

---

## 🙏 Acknowledgments

- Django framework team
- SumUp payment integration
- Jersey community
- All our event organizers

---

**Built with ❤️ in Jersey, Channel Islands**

Version 2.0 - Pay-Per-Event Platform
Last Updated: 9 October 2025
