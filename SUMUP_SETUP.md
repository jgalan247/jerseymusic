# SumUp OAuth Setup Instructions

## Overview

This guide walks you through setting up SumUp OAuth integration for the Jersey Events platform. SumUp OAuth allows event organisers to connect their SumUp accounts to receive ticket payments directly.

---

## Current Configuration

**Environment:** Development
**Redirect URI:** `http://localhost:8000/payments/sumup/oauth/callback/`
**Client ID:** `cc_classic_JtXfBv7WvQXYKX6i9nbbMeHB5g1NL`

---

## Prerequisites

1. **SumUp Merchant Account**
   - You need an active SumUp merchant account
   - Sign up at: https://sumup.com if you don't have one

2. **SumUp Developer Account**
   - Same credentials as your merchant account
   - Access developer portal at: https://developer.sumup.com/

---

## Step 1: Configure SumUp Dashboard

### 1.1 Login to SumUp Developer Portal

1. Go to: https://developer.sumup.com/
2. Click "Login" (top right)
3. Use your SumUp merchant credentials

### 1.2 Navigate to Your Application

1. Click "My Applications" in the navigation
2. You should see your app: **Jersey Events** (or similar name)
3. Click on the application to open settings

### 1.3 Configure OAuth Redirect URIs

This is the **CRITICAL** step. The redirect URI must match EXACTLY.

1. Find the "Redirect URIs" or "OAuth Settings" section
2. Click "Add Redirect URI" or "Edit"
3. Add BOTH of these URIs (both are needed for development):
   ```
   http://localhost:8000/payments/sumup/oauth/callback/
   http://127.0.0.1:8000/payments/sumup/oauth/callback/
   ```

4. **IMPORTANT CHECKS:**
   - ✅ Include the trailing slash `/`
   - ✅ Use `http://` (not `https://`) for localhost
   - ✅ Path must be `/payments/sumup/oauth/callback/` (with "oauth" in path)
   - ✅ Port must be `:8000`

5. Click "Save" or "Update"

### 1.4 Verify Your Credentials

1. In the same application settings, find:
   - **Client ID** (starts with `cc_classic_...`)
   - **Client Secret** (starts with `cc_sk_classic_...`)

2. Verify these match your `.env` file:
   ```bash
   SUMUP_CLIENT_ID=cc_classic_JtXfBv7WvQXYKX6i9nbbMeHB5g1NL
   SUMUP_CLIENT_SECRET=cc_sk_classic_jA7G1FOssixOn2kmZgnsPbaAnek257RPGzDQEEBTxRbmLZvqjJ
   ```

---

## Step 2: Verify Local Configuration

### 2.1 Check .env File

Your `.env` file should have these exact settings:

```bash
# SumUp API Configuration
SUMUP_CLIENT_ID=cc_classic_JtXfBv7WvQXYKX6i9nbbMeHB5g1NL
SUMUP_CLIENT_SECRET=cc_sk_classic_jA7G1FOssixOn2kmZgnsPbaAnek257RPGzDQEEBTxRbmLZvqjJ
SUMUP_API_BASE_URL=https://api.sumup.com/v0.1
SUMUP_MERCHANT_CODE=MV3XJWQM
SUMUP_PROCESSING_RATE=2.50

# OAuth URLs (for development)
# CRITICAL: Must match SumUp dashboard exactly (including /oauth/ and trailing slash)
SUMUP_REDIRECT_URI=http://localhost:8000/payments/sumup/oauth/callback/
SUMUP_RETURN_URL=http://localhost:8000/payments/success/
SUMUP_FAIL_URL=http://localhost:8000/payments/fail/
SUMUP_CANCEL_URL=http://localhost:8000/payments/cancel/
SUMUP_WEBHOOK_URL=http://localhost:8000/payments/sumup/webhook/
```

**Common Mistakes to Avoid:**
- ❌ Using `${SITE_URL}` variables (they don't work in Python `.env` files)
- ❌ Missing trailing slash on redirect URI
- ❌ Wrong path (missing `/oauth/` in path)
- ❌ Using `https://` for localhost

### 2.2 Run Configuration Test

```bash
python test_sumup_config.py
```

**Expected Output:**
```
======================================================================
SUMUP OAUTH CONFIGURATION TEST
======================================================================

📋 Environment Variables (.env file):
   SUMUP_CLIENT_ID: cc_classic_JtXfBv7WvQXYKX6i9n...
   SUMUP_CLIENT_SECRET: cc_sk_classic_jA7G1FOssi...
   SUMUP_REDIRECT_URI: http://localhost:8000/payments/sumup/oauth/callback/
   ...

✅ CONFIGURATION LOOKS GOOD!
```

If you see errors, fix them before proceeding.

---

## Step 3: Test OAuth Flow

### 3.1 Start Django Server

```bash
python manage.py runserver
```

Server should start on `http://localhost:8000`

### 3.2 Login as Organiser

1. Go to: http://localhost:8000/accounts/login/
2. Login with organiser credentials:
   - Email: `organiser1@home.com` (or your test organiser)
   - Password: Your organiser password

### 3.3 Navigate to Dashboard

1. You should see the organiser dashboard
2. Look for a "Connect SumUp Account" button or alert
3. The alert should say "Action Required: Connect Your SumUp Account"

### 3.4 Initiate OAuth Connection

1. Click "Connect SumUp Account Now"
2. You should be redirected to SumUp's login page
3. **URL should look like:**
   ```
   https://api.sumup.com/authorize?
   response_type=code&
   client_id=cc_classic_JtXfBv7WvQXYKX6i9nbbMeHB5g1NL&
   redirect_uri=http://localhost:8000/payments/sumup/oauth/callback/&
   state=...&
   scope=...
   ```

### 3.5 Authorize in SumUp

1. Login to SumUp (if not already logged in)
2. Review the permissions requested
3. Click "Authorize" or "Allow"

### 3.6 Callback Handling

1. You'll be redirected back to your app
2. URL will be: `http://localhost:8000/payments/sumup/oauth/callback/?code=...&state=...`
3. You should see: "SumUp connected successfully! You can close this window."

### 3.7 Verify Connection

1. Return to the organiser dashboard
2. The alert should now show:
   ```
   ✅ SumUp Connected
   Merchant Code: MV3XJWQM
   Ticket payments go directly to your account
   ```

---

## Step 4: Check Server Logs

Look for these log messages in your Django server output:

```
🔵 Starting SumUp OAuth for artist 1
🔵 OAuth URL generated: https://api.sumup.com/authorize?...
🔵 Redirect URI configured: http://localhost:8000/payments/sumup/oauth/callback/
🔵 State parameter: 1:abc123...

🟢 SumUp OAuth callback received
🟢 Query params: {'code': ['...'], 'state': ['1:abc123...']}
✅ OAuth state validated successfully
🟢 Exchanging code for tokens for artist 1
✅ Tokens received successfully
✅ Artist SumUp auth saved for artist 1
```

---

## Troubleshooting

### Error: "redirect_uri parameter does not match"

**Cause:** Your `.env` file redirect URI doesn't match SumUp dashboard

**Fix:**
1. Check `.env` file has: `http://localhost:8000/payments/sumup/oauth/callback/`
2. Check SumUp dashboard has EXACT same URI
3. Ensure trailing slash is present in both
4. Try adding both `localhost` and `127.0.0.1` versions to SumUp dashboard

### Error: "invalid_client"

**Cause:** Client ID or Client Secret is incorrect

**Fix:**
1. Go to SumUp developer dashboard
2. Copy Client ID and Client Secret again
3. Update `.env` file
4. Remove any extra spaces
5. Restart Django server

### Error: "Bad OAuth state or missing code"

**Cause:** Session state doesn't match or was lost

**Fix:**
1. Clear browser cookies
2. Try again from the beginning
3. Make sure cookies are enabled
4. Check Django session configuration

### Error: 404 on callback URL

**Cause:** URL routing issue

**Fix:**
1. Verify `payments/urls.py` has:
   ```python
   path('sumup/oauth/callback/', views.sumup_connect_callback, name='sumup_oauth_callback'),
   ```
2. Restart Django server

### No error but connection doesn't save

**Cause:** Database or model issue

**Fix:**
1. Check Django admin for `ArtistSumUpAuth` records
2. Check server logs for errors
3. Ensure migrations are up to date: `python manage.py migrate`

---

## Production Configuration

When deploying to production, update `.env` to use your domain:

```bash
# Production OAuth URLs
SUMUP_REDIRECT_URI=https://jerseyevents.je/payments/sumup/oauth/callback/
SUMUP_RETURN_URL=https://jerseyevents.je/payments/success/
SUMUP_FAIL_URL=https://jerseyevents.je/payments/fail/
SUMUP_CANCEL_URL=https://jerseyevents.je/payments/cancel/
SUMUP_WEBHOOK_URL=https://jerseyevents.je/payments/sumup/webhook/
```

**Then update SumUp dashboard:**
1. Login to developer portal
2. Add production redirect URI: `https://jerseyevents.je/payments/sumup/oauth/callback/`
3. Keep development URIs for testing
4. Save changes

---

## Security Notes

1. **Never commit `.env` file to git** - it contains secrets
2. **Client Secret** should never be exposed to frontend/JavaScript
3. **State parameter** prevents CSRF attacks - don't skip validation
4. **Access tokens** expire - implement refresh token logic
5. **HTTPS required** in production - SumUp won't accept `http://` for production

---

## Support

- **SumUp Developer Docs:** https://developer.sumup.com/docs/
- **SumUp API Reference:** https://developer.sumup.com/api/
- **SumUp Support:** https://sumup.com/support/

---

## Quick Reference

| Item | Value |
|------|-------|
| **Dev Redirect URI** | `http://localhost:8000/payments/sumup/oauth/callback/` |
| **Prod Redirect URI** | `https://jerseyevents.je/payments/sumup/oauth/callback/` |
| **OAuth Start URL** | `/payments/sumup/oauth/connect/<artist_id>/` |
| **OAuth Callback URL** | `/payments/sumup/oauth/callback/` |
| **Test Script** | `python test_sumup_config.py` |
| **Connect Button** | Organiser Dashboard → "Connect SumUp Account" |

---

**Last Updated:** 2025-10-10
**Version:** 1.0
