# SumUp URL Fixes - Summary

**Date:** October 14, 2025
**Status:** ✅ **COMPLETED**

---

## Overview

Updated all references to SumUp URLs to use the correct URL structure. The OAuth flow is in the **accounts** app, not the payments app.

---

## Changes Made

### 1. ✅ Test File Fixed

**File:** `tests/test_critical_workflows.py`

**Lines Updated:** 359, 372, 381

**Change:**
```python
# ❌ BEFORE (Wrong namespace)
reverse('payments:sumup_connect')
reverse('payments:sumup_callback')

# ✅ AFTER (Correct namespace)
reverse('accounts:sumup_connect')
reverse('accounts:sumup_callback')
```

**Reason:** OAuth URLs are in the accounts app, not payments app.

---

### 2. ✅ Ngrok Script Fixed

**File:** `start_with_ngrok.py`

**Line Updated:** 109

**Change:**
```python
# ❌ BEFORE (Wrong URL path)
redirect_uri = f"{ngrok_url}/payments/sumup/oauth/callback/"

# ✅ AFTER (Correct URL path)
redirect_uri = f"{ngrok_url}/accounts/sumup/callback/"
```

**Reason:** OAuth callback is at `/accounts/sumup/callback/`, not `/payments/sumup/oauth/callback/`.

---

### 3. ✅ Environment File Fixed

**File:** `.env`

**Lines Updated:** 59-61

**Change:**
```bash
# ❌ BEFORE (Wrong URL path)
SUMUP_REDIRECT_URI=https://00539b37b8d9.ngrok-free.app/payments/sumup/oauth/callback/
# SUMUP_REDIRECT_URI=http://localhost:8000/payments/sumup/oauth/callback/

# ✅ AFTER (Correct URL path)
SUMUP_REDIRECT_URI=https://00539b37b8d9.ngrok-free.app/accounts/sumup/callback/
# SUMUP_REDIRECT_URI=http://localhost:8000/accounts/sumup/callback/
```

**Reason:** OAuth redirect URI must match the actual callback URL in the Django app.

---

## Files Already Correct (No Changes Needed)

### ✅ Templates
All templates were already using correct URLs:

- `accounts/templates/accounts/organiser_dashboard.html` ✅
  - Uses `{% url 'accounts:sumup_connect' %}`
  - Uses `{% url 'accounts:sumup_disconnect' %}`

- `accounts/templates/accounts/sumup_connect.html` ✅
  - Uses `{% url 'accounts:sumup_connect' %}`

- `accounts/templates/accounts/artist_dashboard.html` ✅
  - Uses `{% url 'accounts:sumup_connect' %}`
  - Uses `{% url 'accounts:sumup_status' %}`
  - Uses `{% url 'accounts:sumup_disconnect' %}`

### ✅ Views
All view files were already using correct URL patterns:

- `accounts/sumup_views.py` ✅ - OAuth implementation
- `payments/views.py` ✅ - Payment processing
- `events/views.py` ✅ - Uses `redirect('accounts:sumup_connect')`

---

## URL Structure Reference

### Correct OAuth URLs (Accounts App)

| Purpose | URL Path | Django URL Name |
|---------|----------|-----------------|
| Start OAuth | `/accounts/sumup/connect/` | `accounts:sumup_connect` |
| OAuth Callback | `/accounts/sumup/callback/` | `accounts:sumup_callback` |
| Disconnect | `/accounts/sumup/disconnect/` | `accounts:sumup_disconnect` |
| Check Status | `/accounts/sumup/status/` | `accounts:sumup_status` |

### Payment Processing URLs (Payments App)

| Purpose | URL Path | Django URL Name |
|---------|----------|-----------------|
| Checkout | `/payments/sumup/checkout/<order_id>/` | `payments:sumup_checkout` |
| Connected Checkout | `/payments/sumup/connected-checkout/<order_id>/` | `payments:connected_sumup_checkout` |
| Success | `/payments/sumup/success/` | `payments:sumup_success` |
| Callback | `/payments/sumup/callback/` | `payments:sumup_callback` |
| Webhook | `/payments/sumup/webhook/` | `payments:sumup_webhook` |

---

## Important Notes

### ⚠️ Two Different "Callback" URLs

There are **two different callback URLs** with different purposes:

1. **OAuth Callback** (Accounts App)
   - URL: `/accounts/sumup/callback/`
   - Purpose: Receives OAuth authorization code from SumUp
   - Called during artist account connection

2. **Payment Callback** (Payments App)
   - URL: `/payments/sumup/callback/`
   - Purpose: Receives payment status updates
   - Called after customer completes payment

**Do not confuse these two!**

---

## Legacy URLs (Deprecated)

These URLs exist in `payments/urls.py` but are legacy/redundant:

- `/payments/sumup/oauth/connect/<artist_id>/` - Use `/accounts/sumup/connect/` instead
- `/payments/sumup/oauth/callback/` - Use `/accounts/sumup/callback/` instead

**Recommendation:** These legacy URLs could be removed in a future cleanup to avoid confusion.

---

## Environment Configuration

### Development (Local)

```bash
SUMUP_REDIRECT_URI=http://localhost:8000/accounts/sumup/callback/
```

### Development (Ngrok)

```bash
SUMUP_REDIRECT_URI=https://YOUR-NGROK-ID.ngrok-free.app/accounts/sumup/callback/
```

### Production

```bash
SUMUP_REDIRECT_URI=https://yourdomain.com/accounts/sumup/callback/
```

**Important:** The redirect URI must be **exactly** configured in the SumUp developer portal.

---

## SumUp Developer Portal Configuration

You must update your SumUp application settings:

1. Go to: https://developer.sumup.com/
2. Select your application
3. Update **Redirect URIs** to:
   ```
   http://localhost:8000/accounts/sumup/callback/
   https://YOUR-NGROK-ID.ngrok-free.app/accounts/sumup/callback/
   https://yourdomain.com/accounts/sumup/callback/
   ```

**Remove old redirect URIs:**
- ❌ `/payments/sumup/oauth/callback/`
- ❌ Any other incorrect paths

---

## Testing Instructions

### 1. Verify URL Resolution

```bash
python manage.py shell
```

```python
from django.urls import reverse

# Test OAuth URLs
print(reverse('accounts:sumup_connect'))
# Should output: /accounts/sumup/connect/

print(reverse('accounts:sumup_callback'))
# Should output: /accounts/sumup/callback/
```

### 2. Run Verification Script

```bash
python verify_sumup_urls.py
```

**Expected output:**
```
✅ PASSED: All URLs are configured correctly!
✅ Success: 15 URLs
```

### 3. Test OAuth Flow

```bash
# Start server
python manage.py runserver

# Login as artist
# Visit: http://localhost:8000/accounts/login/

# Connect SumUp
# Visit: http://localhost:8000/accounts/sumup/connect/

# Should redirect to SumUp OAuth page
# After authorization, should redirect back to:
# http://localhost:8000/accounts/sumup/callback/?code=...&state=...
```

### 4. Test with Ngrok (for external callback)

```bash
# Start ngrok script (auto-updates .env)
python start_with_ngrok.py

# Follow OAuth flow as above
# Ngrok URL will be used for callback
```

---

## Common Issues & Solutions

### Issue 1: "redirect_uri_mismatch" Error

**Cause:** The redirect URI in `.env` doesn't match SumUp developer portal.

**Solution:**
1. Check `.env` file has correct URL: `/accounts/sumup/callback/`
2. Update SumUp developer portal with exact same URL
3. Ensure no typos (especially trailing slash!)

### Issue 2: Tests Failing with NoReverseMatch

**Cause:** Tests using wrong URL namespace (payments instead of accounts).

**Solution:** Use `reverse('accounts:sumup_connect')` not `reverse('payments:sumup_connect')`

### Issue 3: 404 Error on OAuth Callback

**Cause:** URL pattern not matching or wrong path in `.env`.

**Solution:**
1. Verify `accounts/urls.py` has the route (it does)
2. Check `.env` has `/accounts/sumup/callback/` (not `/payments/...`)
3. Restart Django server after changing `.env`

---

## Files Modified

| File | Lines | Change Type |
|------|-------|-------------|
| `tests/test_critical_workflows.py` | 359, 372, 381 | Fixed URL namespace |
| `start_with_ngrok.py` | 109 | Fixed callback URL path |
| `.env` | 59-61 | Fixed redirect URI |

---

## Documentation Created

1. ✅ `SUMUP_URLS_REFERENCE.md` - Complete URL reference
2. ✅ `URL_404_RESOLUTION.md` - Resolution of 404 error
3. ✅ `verify_sumup_urls.py` - Automated verification script
4. ✅ `SUMUP_URL_FIXES_SUMMARY.md` - This document

---

## Verification Results

```bash
$ python verify_sumup_urls.py

✅ accounts:sumup_connect        → /accounts/sumup/connect/
✅ accounts:sumup_callback       → /accounts/sumup/callback/
✅ accounts:sumup_disconnect     → /accounts/sumup/disconnect/
✅ accounts:sumup_status         → /accounts/sumup/status/
✅ payments:sumup_checkout       → /payments/sumup/checkout/1/
✅ payments:sumup_success        → /payments/sumup/success/
✅ payments:sumup_callback       → /payments/sumup/callback/
✅ payments:sumup_webhook        → /payments/sumup/webhook/

✅ PASSED: All URLs are configured correctly!
```

---

## Next Steps

### For Development

1. ✅ All files updated
2. ✅ URLs verified
3. ⚠️ **Action Required:** Update SumUp developer portal redirect URIs
4. Test OAuth flow with real SumUp account

### For Production

1. Update `.env` with production domain
2. Update SumUp developer portal with production redirect URI
3. Test OAuth flow in production environment
4. Monitor logs for any OAuth errors

---

## Summary

**What was wrong:**
- Test file used `payments:sumup_connect` instead of `accounts:sumup_connect`
- Ngrok script generated wrong callback URL path
- `.env` file had incorrect OAuth redirect URI path

**What was fixed:**
- ✅ Test file now uses correct namespace
- ✅ Ngrok script generates correct URL path
- ✅ `.env` file has correct redirect URI

**What was already correct:**
- ✅ All templates were using correct URLs
- ✅ All views were using correct URL patterns
- ✅ URL routing configuration was correct

**Result:**
🎉 **All SumUp URLs are now consistent and correct!**

---

**Status:** ✅ **READY FOR TESTING**

Test the OAuth flow and verify everything works as expected. The URLs are now properly configured across the entire codebase.
