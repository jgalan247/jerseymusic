# SumUp OAuth Integration Setup Guide

This guide explains how to configure the SumUp OAuth integration for artist payment connections.

## Overview

The Jersey Events platform uses SumUp OAuth to allow artists to connect their own SumUp accounts. This enables customers' ticket payments to be sent directly to the artist's SumUp merchant account.

## Problem: "Unknown Error" When Connecting to SumUp

If you see an "Unknown Error" page when trying to connect your SumUp account, this is usually caused by a missing or incorrect `SUMUP_REDIRECT_URI` configuration.

## Required Environment Variables

You need to configure the following environment variables in your Railway deployment:

### 1. SUMUP_CLIENT_ID (Required)
Your SumUp OAuth application's Client ID.

**Where to find it:**
1. Go to [SumUp Developer Dashboard](https://developer.sumup.com/)
2. Navigate to your OAuth application
3. Copy the "Client ID"

**Example:**
```bash
SUMUP_CLIENT_ID=your_client_id_here
```

### 2. SUMUP_CLIENT_SECRET (Required)
Your SumUp OAuth application's Client Secret.

**Where to find it:**
1. Go to [SumUp Developer Dashboard](https://developer.sumup.com/)
2. Navigate to your OAuth application
3. Copy the "Client Secret" (keep this secure!)

**Example:**
```bash
SUMUP_CLIENT_SECRET=your_client_secret_here
```

### 3. SUMUP_REDIRECT_URI (Critical - Most Common Issue)
The callback URL where SumUp redirects users after authorization.

**IMPORTANT:** This must exactly match the redirect URI registered in your SumUp OAuth application.

**For Railway deployment:**
```bash
SUMUP_REDIRECT_URI=https://tickets.coderra.je/accounts/sumup/callback/
```

**For local development:**
```bash
SUMUP_REDIRECT_URI=http://localhost:8000/accounts/sumup/callback/
```

**For ngrok testing:**
```bash
SUMUP_REDIRECT_URI=https://your-ngrok-url.ngrok.io/accounts/sumup/callback/
```

### 4. SUMUP_MERCHANT_CODE (Optional for OAuth)
Your platform's merchant code for platform-wide payments (listing fees, etc.)

**Example:**
```bash
SUMUP_MERCHANT_CODE=MCXXXXXX
```

## SumUp Developer Dashboard Configuration

### Step 1: Create or Update OAuth Application

1. Go to [SumUp Developer Dashboard](https://developer.sumup.com/)
2. Sign in with your SumUp account
3. Navigate to "My Applications" or "OAuth Apps"
4. Create a new OAuth application or select your existing one

### Step 2: Configure Redirect URI

In your SumUp OAuth application settings:

1. Find the "Redirect URIs" section
2. Add your callback URL exactly as configured in `SUMUP_REDIRECT_URI`
3. **Production:** `https://tickets.coderra.je/accounts/sumup/callback/`
4. **Development:** `http://localhost:8000/accounts/sumup/callback/` (if testing locally)

**CRITICAL:** The URL must match exactly, including:
- Protocol (https:// or http://)
- Domain
- Path (/accounts/sumup/callback/)
- Trailing slash

### Step 3: Configure OAuth Scopes

Make sure your OAuth application requests the following scopes:
- `payments` - Required for creating checkouts
- `checkouts` - Required for checkout status

### Step 4: Save and Deploy

1. Save your SumUp OAuth application settings
2. Copy the Client ID and Client Secret
3. Configure the environment variables in Railway
4. Redeploy your application

## Setting Environment Variables in Railway

### Via Railway Dashboard:

1. Go to your Railway project: https://railway.app/project/[your-project-id]
2. Select your service
3. Go to "Variables" tab
4. Add each environment variable:
   - Click "+ New Variable"
   - Enter variable name (e.g., `SUMUP_REDIRECT_URI`)
   - Enter variable value
   - Click "Add"
5. Railway will automatically redeploy with new variables

### Via Railway CLI:

```bash
railway variables set SUMUP_CLIENT_ID=your_client_id_here
railway variables set SUMUP_CLIENT_SECRET=your_client_secret_here
railway variables set SUMUP_REDIRECT_URI=https://tickets.coderra.je/accounts/sumup/callback/
```

## Verifying Configuration

### Method 1: Management Command

Run the configuration check command:

```bash
python manage.py check_sumup_config --verbose
```

This will:
- Check all required environment variables are set
- Validate the redirect URI format
- Show you the expected OAuth flow
- Identify any configuration issues

### Method 2: Check Application Logs

After deploying with the correct configuration:

1. Try connecting to SumUp as an artist user
2. Check the application logs in Railway
3. Look for log messages like:
   - "User X initiating SumUp OAuth flow"
   - "Configured redirect URI: https://..."
   - "Redirecting to SumUp authorization URL"

If you see these logs, the configuration is working correctly.

## OAuth Flow Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Artist    │         │ Jersey Events│         │    SumUp    │
│             │         │              │         │             │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. Click "Connect"    │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │                       │ 2. Redirect to OAuth   │
       │                       ├───────────────────────>│
       │                       │                        │
       │           3. User authorizes app               │
       │<──────────────────────────────────────────────>│
       │                       │                        │
       │                       │ 4. Redirect to callback│
       │                       │<───────────────────────┤
       │                       │   with code            │
       │                       │                        │
       │                       │ 5. Exchange code       │
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │ 6. Return tokens       │
       │                       │<───────────────────────┤
       │                       │                        │
       │ 7. Show success msg   │                        │
       │<──────────────────────┤                        │
       │                       │                        │
```

## Troubleshooting

### Issue: "Unknown Error" page

**Cause:** The redirect URI is not configured or doesn't match SumUp's whitelist.

**Solution:**
1. Set `SUMUP_REDIRECT_URI` environment variable in Railway
2. Make sure it matches exactly what's in SumUp Developer Dashboard
3. Redeploy the application

### Issue: "Session expired" error

**Cause:** The OAuth state token expired (user took too long to authorize).

**Solution:**
- This is normal if the authorization takes more than a few minutes
- Simply try connecting again

### Issue: "Invalid OAuth state" error

**Cause:** The state parameter doesn't match (possible CSRF attack or session issue).

**Solution:**
- Clear browser cookies and try again
- Make sure sessions are properly configured in Django

### Issue: "SumUp authorization failed: access_denied"

**Cause:** User clicked "Cancel" or denied authorization on SumUp's page.

**Solution:**
- Try connecting again and click "Authorize" on SumUp's page

### Issue: Network error during token exchange

**Cause:** Cannot reach SumUp's API servers.

**Solution:**
- Check your internet connection
- Verify `SUMUP_API_URL` is correct (should be https://api.sumup.com/v0.1)
- Check Railway's network settings

## Testing the Integration

### 1. Create a Test Artist Account

```bash
# Create a test artist user
python manage.py createsuperuser
# Set user_type to 'artist' in admin panel
```

### 2. Test the OAuth Flow

1. Log in as the artist user
2. Go to the dashboard
3. You should see a message: "Please connect your SumUp account"
4. Click the "Connect to SumUp" button
5. You should be redirected to SumUp's authorization page
6. Authorize the application
7. You should be redirected back to your dashboard with a success message

### 3. Verify the Connection

After successful connection:
- Artist profile should show "Connected" status
- Merchant code should be populated
- Access token should be stored (visible in admin panel)

## Security Considerations

1. **Never commit credentials to git**
   - All SumUp credentials must be in environment variables
   - Never hardcode CLIENT_ID, CLIENT_SECRET, or tokens

2. **Use HTTPS in production**
   - The redirect URI must use HTTPS in production
   - HTTP is only acceptable for local development

3. **Rotate credentials regularly**
   - Generate new CLIENT_SECRET periodically
   - Update environment variables when rotating

4. **Validate callback parameters**
   - The code already validates the OAuth state parameter
   - Never trust client-provided data without validation

## Support

If you continue experiencing issues:

1. Run the configuration check: `python manage.py check_sumup_config --verbose`
2. Check application logs in Railway dashboard
3. Verify all environment variables are set correctly
4. Ensure redirect URI matches exactly in both places
5. Contact SumUp support if issues persist with their OAuth implementation

## References

- [SumUp API Documentation](https://developer.sumup.com/docs/)
- [SumUp OAuth Guide](https://developer.sumup.com/docs/authorization/)
- [Railway Documentation](https://docs.railway.app/)
