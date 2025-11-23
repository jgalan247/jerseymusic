# SumUp OAuth Integration Setup Guide

This guide explains how to configure SumUp OAuth for artist payment integration in Jersey Events.

## Overview

Jersey Events uses SumUp OAuth to allow artists/organizers to connect their SumUp accounts. This enables:
- Artists receive ticket payments directly to their SumUp account
- Platform handles payment processing without storing sensitive payment credentials
- Artists can disconnect/reconnect at any time

## Architecture

### OAuth Flow

1. **Artist clicks "Connect SumUp"** → `/accounts/sumup/connect/`
2. **Redirects to SumUp** → `https://api.sumup.com/authorize?...`
3. **Artist logs into SumUp** → Approves access
4. **SumUp redirects back** → `/accounts/sumup/callback/?code=...&state=...`
5. **Platform exchanges code for tokens** → Stores in `ArtistProfile`
6. **Artist is connected** → Can now receive payments

### URL Endpoints

- **Connect**: `/accounts/sumup/connect/` - Initiates OAuth flow
- **Callback**: `/accounts/sumup/callback/` - Receives authorization code from SumUp
- **Disconnect**: `/accounts/sumup/disconnect/` - Removes OAuth connection
- **Status**: `/accounts/sumup/status/` - Checks connection status

## Required Configuration

### 1. SumUp Developer Account

1. Register at https://developer.sumup.com/
2. Create a new OAuth application
3. Configure OAuth settings:
   - **Application Name**: Jersey Events (or your platform name)
   - **Redirect URI**: `https://your-domain.com/accounts/sumup/callback/`
   - **Scopes**:
     - `payments` - Create and process payments
     - `user.profile_readonly` - Read merchant profile
     - `transactions.history` - View transaction history
4. Note your credentials:
   - **Client ID**: Public identifier for your app
   - **Client Secret**: Secret key for authentication

### 2. Environment Variables

Configure these in Railway (or your deployment platform):

```bash
# Required for OAuth
SUMUP_CLIENT_ID=your_client_id_here
SUMUP_CLIENT_SECRET=your_client_secret_here

# Optional - will auto-configure from SITE_URL if not set
SUMUP_REDIRECT_URI=https://your-domain.com/accounts/sumup/callback/

# Required - base URL for your platform
SITE_URL=https://your-domain.com

# Required for platform payments (listing fees)
SUMUP_MERCHANT_CODE=your_platform_merchant_code
SUMUP_ACCESS_TOKEN=your_platform_access_token
```

### 3. Redirect URI Configuration

The **redirect URI** must match exactly what's configured in SumUp dashboard.

#### Automatic Configuration (Recommended)

If `SUMUP_REDIRECT_URI` is not set, it will be auto-constructed from `SITE_URL`:

```python
SUMUP_REDIRECT_URI = f"{SITE_URL}/accounts/sumup/callback/"
```

For example:
- `SITE_URL=https://tickets.coderra.je` → `https://tickets.coderra.je/accounts/sumup/callback/`
- `SITE_URL=https://myapp.railway.app` → `https://myapp.railway.app/accounts/sumup/callback/`

#### Manual Configuration

Set explicitly if you need a different URL:

```bash
SUMUP_REDIRECT_URI=https://tickets.coderra.je/accounts/sumup/callback/
```

⚠️ **Important**: The redirect URI must:
- Use HTTPS in production (HTTP only for local development)
- Match exactly what's in SumUp dashboard (including trailing slash)
- Be publicly accessible (SumUp needs to redirect to it)

## SumUp Dashboard Setup

### Step 1: Register Redirect URI

1. Log into https://developer.sumup.com/
2. Go to your application settings
3. Add redirect URI: `https://your-domain.com/accounts/sumup/callback/`
4. Save changes

### Step 2: Configure Scopes

Ensure these scopes are enabled:
- ✅ `payments` - Required for creating checkouts
- ✅ `user.profile_readonly` - Required for merchant info
- ✅ `transactions.history` - Required for transaction tracking

### Step 3: Test Environment

For testing, you can use SumUp's sandbox environment:
- **API URL**: https://api.sumup.com (use production URL)
- **Test Cards**: Available in SumUp documentation
- **Test Mode**: Set `DEBUG=True` locally

## Testing the OAuth Flow

### Local Development

1. Set environment variables in `.env`:
   ```bash
   SUMUP_CLIENT_ID=your_test_client_id
   SUMUP_CLIENT_SECRET=your_test_client_secret
   SITE_URL=http://127.0.0.1:8000
   DEBUG=True
   ```

2. Start development server:
   ```bash
   python manage.py runserver
   ```

3. Create an artist account:
   - Register as "Organiser" at `/accounts/register/organiser/`
   - Complete artist profile

4. Test OAuth connection:
   - Navigate to `/accounts/sumup/connect/`
   - Should redirect to SumUp login
   - After login, should redirect back to `/accounts/sumup/callback/`
   - Should see success message and be connected

### Production Testing

1. Deploy to Railway with environment variables configured
2. Verify `SITE_URL` matches your Railway public domain
3. Check Railway logs for OAuth URL generation:
   ```
   ✅ Auto-configured SUMUP_REDIRECT_URI: https://your-domain.railway.app/accounts/sumup/callback/
   ```
4. Test connection as an artist user

## Troubleshooting

### Issue: Redirects to account page instead of SumUp

**Symptoms**: Clicking "Connect SumUp" redirects to `/accounts/profile/` or `/accounts/dashboard/`

**Possible Causes**:

1. **Not logged in as artist**
   - User must be logged in with `user_type='artist'`
   - Check: Does user have an `ArtistProfile`?
   - Fix: Register as organiser, not customer

2. **Missing environment variables**
   - Check: `SUMUP_CLIENT_ID` is set
   - Check: `SUMUP_REDIRECT_URI` or `SITE_URL` is set
   - Fix: Set missing variables in Railway dashboard

3. **OAuth URL generation failing**
   - Check Railway logs for error messages
   - Look for: "SUMUP_CLIENT_ID is not configured"
   - Look for: "SUMUP_REDIRECT_URI is not configured"

**Debug Steps**:

1. Check Railway logs:
   ```bash
   railway logs | grep -i sumup
   ```

2. Check for configuration errors:
   ```bash
   railway logs | grep "OAuth"
   ```

3. Verify environment variables:
   - Go to Railway project → Settings → Variables
   - Verify `SUMUP_CLIENT_ID` is set
   - Verify `SITE_URL` is set correctly

### Issue: "Invalid OAuth state" error

**Cause**: Session state mismatch between connect and callback

**Solutions**:
1. Clear browser cookies and try again
2. Check that sessions are working correctly
3. Verify Redis/session backend is configured

### Issue: "Failed to connect to SumUp" after callback

**Causes**:
1. **Invalid authorization code**
   - Code might have expired (10 minutes)
   - Code might have been used already
   - Try connecting again

2. **Token exchange failed**
   - Check Railway logs for API errors
   - Verify `SUMUP_CLIENT_SECRET` is correct
   - Check SumUp API status

3. **Redirect URI mismatch**
   - URL in SumUp dashboard must match exactly
   - Check for missing/extra trailing slashes
   - Verify HTTPS vs HTTP

### Issue: OAuth URL shows "None" in redirect URI

**Cause**: `SUMUP_REDIRECT_URI` is not set and auto-configuration failed

**Solution**:
1. Set `SITE_URL` environment variable:
   ```bash
   SITE_URL=https://your-domain.railway.app
   ```

2. Or set `SUMUP_REDIRECT_URI` explicitly:
   ```bash
   SUMUP_REDIRECT_URI=https://your-domain.railway.app/accounts/sumup/callback/
   ```

3. Redeploy application

## Logging and Monitoring

### OAuth-Specific Logs

The application logs OAuth operations:

```python
logger.info(f"Redirecting user {user_id} to SumUp OAuth: {auth_url[:50]}...")
logger.info(f"Artist {user_id} successfully connected to SumUp")
logger.error(f"SumUp OAuth URL generation failed for user {user_id}")
logger.error(f"Error starting SumUp OAuth for user {user_id}: {error}")
```

### Check Logs

**Railway CLI**:
```bash
railway logs | grep -i "oauth"
```

**Railway Dashboard**:
1. Go to your service
2. Click "Deployments"
3. Select deployment
4. View "Deploy Logs"

### Debug Mode

Enable detailed logging by setting:
```bash
DEBUG=True
DJANGO_LOG_LEVEL=DEBUG
```

## Security Considerations

### State Parameter

The OAuth flow uses a `state` parameter to prevent CSRF attacks:

```python
state = f"{user_id}:{uuid4()}"
```

This state is:
- Stored in session before redirect
- Verified on callback
- Must match exactly or connection fails

### Token Storage

OAuth tokens are stored securely in `ArtistProfile`:

```python
class ArtistProfile(models.Model):
    sumup_access_token = models.TextField(blank=True)      # Encrypted in production
    sumup_refresh_token = models.TextField(blank=True)     # Encrypted in production
    sumup_expires_at = models.DateTimeField(null=True)     # Token expiry
    sumup_connection_status = models.CharField(...)         # Connection state
```

### Token Refresh

Access tokens expire and must be refreshed:

```python
if artist_profile.sumup_token_expired:
    new_token_data = sumup_api.refresh_access_token_direct(
        artist_profile.sumup_refresh_token
    )
    artist_profile.update_sumup_connection(new_token_data)
```

## Code References

### Key Files

- **OAuth Views**: `accounts/sumup_views.py`
  - `SumUpConnectView` - Initiates OAuth flow
  - `SumUpCallbackView` - Handles OAuth callback
  - `SumUpDisconnectView` - Disconnects OAuth

- **OAuth API**: `payments/sumup.py`
  - `oauth_authorize_url()` - Generates authorization URL
  - `exchange_code_for_tokens()` - Exchanges code for tokens
  - `refresh_access_token_direct()` - Refreshes expired tokens

- **Settings**: `events/settings.py`
  - Lines 411-427: SumUp OAuth configuration
  - Lines 545-550: Auto-configuration logic

### URL Configuration

**accounts/urls.py**:
```python
path('sumup/connect/', sumup_views.SumUpConnectView.as_view(), name='sumup_connect'),
path('sumup/callback/', sumup_views.SumUpCallbackView.as_view(), name='sumup_callback'),
path('sumup/disconnect/', sumup_views.SumUpDisconnectView.as_view(), name='sumup_disconnect'),
```

## Quick Reference

### Environment Variables Checklist

For OAuth to work, you need:

- ✅ `SUMUP_CLIENT_ID` - From SumUp developer dashboard
- ✅ `SUMUP_CLIENT_SECRET` - From SumUp developer dashboard
- ✅ `SITE_URL` - Your platform's public URL
- ⚙️ `SUMUP_REDIRECT_URI` - Auto-configured from SITE_URL if not set

### SumUp Dashboard Checklist

- ✅ OAuth application created
- ✅ Redirect URI registered: `https://your-domain.com/accounts/sumup/callback/`
- ✅ Scopes enabled: `payments`, `user.profile_readonly`, `transactions.history`
- ✅ Client ID and Secret generated

### Testing Checklist

- ✅ Artist account created
- ✅ Artist profile completed
- ✅ Can access `/accounts/sumup/connect/`
- ✅ Redirects to SumUp login page
- ✅ After login, redirects back to platform
- ✅ Success message displayed
- ✅ `artist_profile.is_sumup_connected` is `True`

## Support

If you're still experiencing issues:

1. Check Railway deployment logs
2. Verify all environment variables are set
3. Confirm SumUp dashboard configuration matches
4. Test with a fresh artist account
5. Review the security checklist above

For SumUp API issues, consult:
- https://developer.sumup.com/docs/
- https://developer.sumup.com/api/oauth

---

**Last Updated**: 2025-11-23
**OAuth Implementation**: accounts/sumup_views.py
**Configuration**: events/settings.py:411-550
