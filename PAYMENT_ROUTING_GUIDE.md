# Payment Routing Guide - Artist OAuth vs Platform Payments

**Date:** October 14, 2025
**Status:** ✅ Infrastructure Complete - Configuration Needed

---

## Overview

The Jersey Events platform supports **TWO payment flows**:

1. **Artist OAuth Payments** (PRODUCTION) - Money goes directly to artist
2. **Platform Payments** (TESTING/FALLBACK) - Money goes to platform account

---

## How It Works

### 🔑 Key Concept: OAuth Token vs Merchant Code

**Authentication (API Access):**
- OAuth tokens are used to AUTHENTICATE with SumUp API
- They allow reading/checking payment status
- They DON'T determine where money goes

**Money Destination:**
- Determined by the **merchant code** used when **creating checkout**
- OR by the **OAuth token** used to create checkout (includes merchant identity)

---

## Payment Flow Comparison

### ✅ Artist OAuth Payment (PRODUCTION - Money to Artist)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Artist Connects SumUp (One-time)                         │
└─────────────────────────────────────────────────────────────┘
   ↓
   Artist clicks "Connect SumUp" in dashboard
   ↓
   Redirected to SumUp OAuth authorization
   ↓
   Artist logs into THEIR SumUp account
   ↓
   Grants permission to Jersey Events
   ↓
   Tokens stored in ArtistProfile:
     - sumup_access_token (expires in ~1 hour)
     - sumup_refresh_token (long-lived)
     - sumup_merchant_code (e.g., M-ABC123)
     - sumup_token_expiry

┌─────────────────────────────────────────────────────────────┐
│ 2. Customer Buys Ticket                                     │
└─────────────────────────────────────────────────────────────┘
   ↓
   System calls: create_checkout_for_connected_artist()
     - Uses artist's OAuth token
     - Money goes to artist's merchant code (M-ABC123)
   ↓
   Customer pays on SumUp
   ↓
   Money → ARTIST'S SumUp Account ✅
   ↓
   Polling service verifies payment:
     - Uses artist's OAuth token to check status
     - Marks order as completed
     - Sends email with tickets
```

**Code Location:** `payments/connected_payment_service.py:67`
```python
checkout_data = sumup_api.create_checkout_for_connected_artist(
    artist_profile=artist_profile,
    amount=order.total,
    currency='GBP',
    reference=f"JE-{order.order_number}",
    description=f"Jersey Events - Order {order.order_number}",
    return_url=f"{settings.SITE_URL}/payments/callback/"
)
```

---

### ⚠️ Platform Payment (TESTING - Money to Platform)

```
┌─────────────────────────────────────────────────────────────┐
│ Artist NOT Connected to SumUp                               │
└─────────────────────────────────────────────────────────────┘
   ↓
   Customer buys ticket
   ↓
   System calls: create_checkout_simple()
     - Uses platform OAuth token (for API auth)
     - Uses platform merchant code: M28WNZCB
   ↓
   Customer pays on SumUp
   ↓
   Money → PLATFORM's SumUp Account ⚠️
   ↓
   Platform must manually transfer to artist
   ↓
   Polling service verifies payment:
     - Uses platform token to check status (FIXED)
     - Marks order as completed
     - Sends email with tickets
```

**Code Location:** `payments/sumup.py:337`
```python
payload = {
    "checkout_reference": reference,
    "amount": validated_amount,
    "currency": currency,
    "description": description,
    "merchant_code": settings.SUMUP_MERCHANT_CODE,  # ← Platform code (M28WNZCB)
    "return_url": return_url
}
```

---

## Current Configuration

### Platform Credentials (Testing Only)
```bash
# In .env
SUMUP_CLIENT_ID=cc_classic_u9OD2Fvg8R2FBv2U4ZQdWZHJGGuBV
SUMUP_CLIENT_SECRET=cc_sk_classic_o3ozGI6z3...
SUMUP_MERCHANT_CODE=M28WNZCB  # ← Platform account
```

**Money Flow:**
- All payments from artists WITHOUT OAuth → Platform account (M28WNZCB)
- Platform must manually transfer to artists

---

## Production Configuration Required

### Option 1: Require All Artists to Connect SumUp (RECOMMENDED ✅)

**Implementation:**

1. **Add decorator to event creation:**
```python
# In events/views.py
from accounts.sumup_views import sumup_connection_required

@sumup_connection_required
def create_event(request):
    # Event creation logic
    pass
```

2. **Update event creation template:**
```html
{% if not user.artistprofile.is_sumup_connected %}
  <div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle"></i>
    You must connect your SumUp account before creating events.
    <a href="{% url 'accounts:sumup_connect' %}" class="btn btn-primary btn-sm">
      Connect SumUp Now
    </a>
  </div>
{% endif %}
```

3. **Update payment routing in checkout:**
```python
# In payments/widget_service.py or wherever checkout is created

def create_checkout_for_order(order):
    # Get event organizer
    artist_profile = order.items.first().event.organiser.artistprofile

    # Check if artist has OAuth
    if artist_profile.is_sumup_connected:
        # Use artist's SumUp account - money goes to them
        service = ConnectedPaymentService()
        return service.create_connected_checkout(order)
    else:
        # This should never happen in production if we enforce OAuth
        raise ValueError("Artist must connect SumUp account to receive payments")
```

**Benefits:**
- ✅ Money goes directly to artists
- ✅ No manual transfers needed
- ✅ Clean accounting
- ✅ Artists see payments immediately in their SumUp dashboard
- ✅ Platform doesn't hold artist money

**Implementation Time:** ~2 hours

---

### Option 2: Platform as Payment Processor (NOT RECOMMENDED)

Keep current system but add:
- Artist payout management system
- Bank account collection from artists
- Scheduled payout runs (weekly/monthly)
- Accounting for platform fees
- Payout tracking and reconciliation

**Code exists:** `payments/connected_payment_service.py:178-226` (ArtistPayout model)

**Issues:**
- Platform holds artist money
- Complex accounting required
- Manual transfers needed
- Potential legal/compliance issues
- More support burden

---

## How Artists Connect SumUp (User Flow)

### Step 1: Artist Dashboard
```
Artist logs in → Dashboard → See "SumUp Connection" card
Status: "Not Connected"
Button: "Connect SumUp"
```

### Step 2: OAuth Flow
```
Click "Connect SumUp"
  ↓
Redirected to SumUp login page
  ↓
Artist enters THEIR SumUp email/password
  ↓
SumUp asks: "Allow Jersey Events to access your account?"
  ↓
Artist clicks "Allow"
  ↓
Redirected back to Jersey Events
  ↓
Success message: "Successfully connected to SumUp!"
```

### Step 3: Tokens Stored
```python
ArtistProfile fields updated:
- sumup_access_token: "at_classic_Abc123..."
- sumup_refresh_token: "rt_classic_Xyz789..."
- sumup_merchant_code: "M-ABC123"  # Artist's merchant code
- sumup_token_expiry: 2025-10-14 15:30:00
- sumup_connection_status: "active"
```

### Step 4: Artist Creates Event
```
Event created with organiser = artist
  ↓
Customer buys ticket
  ↓
Checkout created using artist's OAuth token
  ↓
Money → Artist's SumUp account (M-ABC123) ✅
```

---

## NO Manual Entry Required! 🎉

**Artists DO NOT need to:**
- ❌ Enter Client ID
- ❌ Enter Client Secret
- ❌ Enter Merchant Code
- ❌ Copy/paste any credentials

**They ONLY need to:**
1. Click "Connect SumUp"
2. Log into their SumUp account
3. Click "Allow"

**That's it!** OAuth does the rest automatically.

---

## Polling Service Payment Verification

### Fixed OAuth Fallback (October 14, 2025)

**Code:** `payments/polling_service.py:143-156`

```python
# Check if artist has OAuth connection
if organizer_profile and organizer_profile.is_sumup_connected:
    # Use artist's OAuth tokens
    logger.info(f"Using artist OAuth tokens for checkout {checkout_id}")
    payment_data = sumup_api.get_checkout_for_artist(
        artist_profile=organizer_profile,
        checkout_id=checkout_id
    )
else:
    # Use platform token as fallback
    logger.info(f"Artist not connected to SumUp - using platform token")
    payment_data = sumup_api.get_checkout_status(checkout_id)
```

**This works for BOTH scenarios:**
- ✅ Artist with OAuth → Uses artist token
- ✅ Artist without OAuth → Uses platform token

---

## Money Flow Summary

### Current State (Testing):
```
ALL PAYMENTS → Platform Account (M28WNZCB)
  ↓
Platform manually transfers to artists
```

### Production Goal:
```
Artist WITH OAuth:
  Payment → Artist's SumUp Account (M-ABC123) ✅

Artist WITHOUT OAuth:
  Cannot create events (enforced by decorator)
```

---

## Implementation Checklist

### For Production Launch:

- [ ] **1. Add SumUp requirement to event creation** (30 min)
  - Add `@sumup_connection_required` decorator
  - Update event creation templates
  - Show connection prompt to artists

- [ ] **2. Update payment routing** (1 hour)
  - Use `ConnectedPaymentService` for all event payments
  - Fallback to platform only for listing fees
  - Add error handling for disconnected artists

- [ ] **3. Update artist onboarding** (30 min)
  - Show SumUp connection step in signup flow
  - Add "Next: Connect SumUp" button after registration
  - Send reminder email if not connected

- [ ] **4. Add monitoring** (30 min)
  - Alert when artist tries to create event without OAuth
  - Track OAuth connection success rate
  - Monitor payment routing (artist vs platform)

- [ ] **5. Update documentation** (30 min)
  - Artist help docs: "How to Connect SumUp"
  - FAQ: "Where does my money go?"
  - Support team guide

**Total estimated time: ~3 hours**

---

## Testing Checklist

### Local Testing (Current):
- ✅ Use platform credentials (M28WNZCB)
- ✅ Money goes to platform account
- ✅ Polling service works with platform token
- ✅ Email notifications sent

### Pre-Production Testing:
- [ ] Create test artist account
- [ ] Connect test SumUp account (get from SumUp support)
- [ ] Create test event
- [ ] Buy test ticket
- [ ] Verify money goes to test artist account
- [ ] Verify polling uses artist OAuth token
- [ ] Verify email sent with tickets

### Production Launch:
- [ ] Require all artists to connect SumUp
- [ ] Monitor first 10 payments closely
- [ ] Verify money routing to correct artists
- [ ] Check payout reconciliation

---

## Troubleshooting

### Issue: Artist's OAuth token expired
**Symptom:** Polling shows "Token expired" error
**Solution:** Automatic token refresh (already implemented)
**Fallback:** Artist reconnects via dashboard

### Issue: Artist disconnects SumUp
**Symptom:** Existing events can't process payments
**Solution:**
1. Detect disconnection in polling
2. Alert artist via email
3. Pause event ticket sales until reconnected

### Issue: Money went to wrong account
**Symptom:** Customer payment went to platform instead of artist
**Solution:**
1. Check event organizer's `is_sumup_connected` status
2. Verify which checkout function was called
3. Manual refund/transfer if needed

---

## Security Notes

### OAuth Token Storage
- ✅ Tokens stored encrypted in database
- ✅ Access tokens expire after 1 hour
- ✅ Refresh tokens used automatically
- ✅ No sensitive credentials in logs

### Payment Security
- ✅ Server-side amount validation
- ✅ All payments verified with SumUp API
- ✅ Polling service double-checks amounts
- ✅ Audit trail for all transactions

### Artist Verification
- ✅ Only event organizer can connect SumUp
- ✅ OAuth state parameter prevents CSRF
- ✅ User ID validated in callback
- ✅ Connection status tracked

---

## Support & Resources

### For Artists:
- Dashboard: View SumUp connection status
- Connect: `/accounts/sumup/connect/`
- Disconnect: `/accounts/sumup/disconnect/`
- Status Check: `/accounts/sumup/status/`

### For Developers:
- OAuth Flow: `accounts/sumup_views.py`
- Payment Service: `payments/connected_payment_service.py`
- Polling Service: `payments/polling_service.py`
- API Client: `payments/sumup.py`

### SumUp Resources:
- Developer Portal: https://developer.sumup.com
- OAuth Docs: https://developer.sumup.com/docs/oauth
- Test Cards: https://developer.sumup.com/docs/testing

---

## Conclusion

**Current Status:** ✅ Infrastructure Complete

**Polling Fix:** ✅ OAuth fallback working (October 14, 2025)

**Money Flow:**
- Testing: Platform account (M28WNZCB)
- Production: Artist accounts (after enforcing OAuth)

**Next Steps:**
1. Enforce SumUp connection for event creation
2. Update payment routing to use artist OAuth
3. Test with real artist SumUp account
4. Deploy to production

**Estimated Implementation:** 3 hours

**Result:** Money flows directly to artists with no manual intervention needed! 🎉
