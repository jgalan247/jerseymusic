# payments/sumup.py
import time, requests, datetime
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_platform_access_token():
    """Get or refresh the platform's SumUp access token using client credentials."""
    # Check cache first
    cached_token = cache.get('sumup_platform_token')
    if cached_token:
        return cached_token

    try:
        # Request new token using client credentials
        response = requests.post(
            f"{settings.SUMUP_BASE_URL}/token",
            data={
                'grant_type': 'client_credentials',
                'client_id': settings.SUMUP_CLIENT_ID,
                'client_secret': settings.SUMUP_CLIENT_SECRET,
                'scope': 'payments'
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        access_token = data.get('access_token')
        expires_in = data.get('expires_in', 3600)

        # Cache the token for slightly less than its expiry time
        cache_duration = max(expires_in - 300, 60)  # At least 1 minute
        cache.set('sumup_platform_token', access_token, cache_duration)

        logger.info(f"Successfully obtained new SumUp platform token, expires in {expires_in}s")
        return access_token

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get SumUp platform token: {e}")
        # Fall back to API key if available
        if settings.SUMUP_API_KEY:
            logger.info("Falling back to API key authentication")
            return settings.SUMUP_API_KEY
        raise

def oauth_authorize_url(state: str):
    """
    Generate SumUp OAuth authorization URL for artist OAuth connection.

    Args:
        state: Security state parameter to prevent CSRF attacks

    Returns:
        str: Full OAuth authorization URL to redirect user to SumUp login

    Raises:
        ValueError: If required OAuth credentials are missing
    """
    # Validate required configuration
    if not settings.SUMUP_CLIENT_ID:
        logger.error("SUMUP_CLIENT_ID is not configured")
        raise ValueError("SumUp Client ID is not configured. Please set SUMUP_CLIENT_ID environment variable.")

    if not settings.SUMUP_REDIRECT_URI:
        logger.error("SUMUP_REDIRECT_URI is not configured")
        raise ValueError("SumUp Redirect URI is not configured. Please set SUMUP_REDIRECT_URI or SITE_URL environment variable.")

    base = f"{settings.SUMUP_BASE_URL}/authorize"
    auth_url = (
        f"{base}?response_type=code"
        f"&client_id={settings.SUMUP_CLIENT_ID}"
        f"&redirect_uri={settings.SUMUP_REDIRECT_URI}"
        f"&scope=payments%20user.profile_readonly%20transactions.history"
        f"&state={state}"
    )

    logger.info(f"Generated OAuth URL: {base}?... (client_id and redirect_uri configured)")
    logger.debug(f"Full OAuth URL: {auth_url}")

    return auth_url

def exchange_code_for_tokens(code: str):
    """Exchange OAuth authorization code for access/refresh tokens with comprehensive logging."""
    logger.info("=" * 80)
    logger.info("📞 API Call: exchange_code_for_tokens()")
    logger.info("=" * 80)

    # Log configuration (mask sensitive data)
    token_url = f"{settings.SUMUP_BASE_URL}/token"
    logger.info(f"🔗 Token URL: {token_url}")
    logger.info(f"🔑 Client ID: {settings.SUMUP_CLIENT_ID[:20]}..." if settings.SUMUP_CLIENT_ID else "❌ NOT SET")
    logger.info(f"🔐 Client Secret: {'SET (length: ' + str(len(settings.SUMUP_CLIENT_SECRET)) + ')' if settings.SUMUP_CLIENT_SECRET else '❌ NOT SET'}")
    logger.info(f"🔄 Redirect URI: {settings.SUMUP_REDIRECT_URI}")
    logger.info(f"📝 Code preview: {code[:20]}...{code[-10:] if len(code) > 30 else ''}")

    # Prepare request data
    request_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.SUMUP_CLIENT_ID,
        "client_secret": settings.SUMUP_CLIENT_SECRET,
        "redirect_uri": settings.SUMUP_REDIRECT_URI,
    }

    logger.info("📤 Sending POST request to SumUp token endpoint...")

    try:
        r = requests.post(
            token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=request_data,
            timeout=20,
        )

        logger.info(f"📥 Response received:")
        logger.info(f"   Status code: {r.status_code}")
        logger.info(f"   Response headers: {dict(r.headers)}")

        # Check for errors before raising
        if not r.ok:
            logger.error("=" * 80)
            logger.error(f"❌ SumUp API returned error status {r.status_code}")
            logger.error(f"   Response body: {r.text}")
            logger.error(f"   Response headers: {dict(r.headers)}")
            logger.error("=" * 80)

        r.raise_for_status()

        # Parse response
        data = r.json()
        logger.info("✅ Successfully parsed JSON response")
        logger.info(f"   Response keys: {list(data.keys())}")

        # Extract fields
        expires_in = data.get("expires_in", 600)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token", "")
        token_type = data.get("token_type", "Bearer")
        scope = data.get("scope", "")

        logger.info(f"📋 Token details:")
        logger.info(f"   Token type: {token_type}")
        logger.info(f"   Expires in: {expires_in} seconds")
        logger.info(f"   Scope: {scope}")
        logger.info(f"   Access token length: {len(access_token) if access_token else 0}")
        logger.info(f"   Refresh token length: {len(refresh_token) if refresh_token else 0}")

        # Validate required fields
        if not access_token:
            logger.error("=" * 80)
            logger.error("❌ CRITICAL: No access_token in response!")
            logger.error(f"   Full response: {data}")
            logger.error("=" * 80)
            raise KeyError("access_token")

        expires_at = timezone.now() + datetime.timedelta(seconds=expires_in - 30)
        logger.info(f"⏰ Token expires at: {expires_at}")

        result = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
            "scope": scope,
        }

        logger.info("=" * 80)
        logger.info("✅ Token exchange completed successfully")
        logger.info("=" * 80)

        return result

    except requests.exceptions.HTTPError as e:
        logger.error("=" * 80)
        logger.error(f"❌ HTTP Error during token exchange")
        logger.error(f"   Status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        logger.error(f"   Response body: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 80)
        raise

    except requests.exceptions.Timeout as e:
        logger.error("=" * 80)
        logger.error(f"❌ Timeout during token exchange (20 seconds)")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 80)
        raise

    except requests.exceptions.RequestException as e:
        logger.error("=" * 80)
        logger.error(f"❌ Network error during token exchange")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 80)
        raise

    except KeyError as e:
        logger.error("=" * 80)
        logger.error(f"❌ Missing required field in token response: {str(e)}")
        logger.error(f"   Response data: {data if 'data' in locals() else 'Not available'}")
        logger.error("=" * 80)
        raise

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ Unexpected error during token exchange")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise

def refresh_access_token(artist_sumup):
    r = requests.post(
        f"{settings.SUMUP_BASE_URL}/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": artist_sumup.refresh_token,
            "client_id": settings.SUMUP_CLIENT_ID,
            "client_secret": settings.SUMUP_CLIENT_SECRET,
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    artist_sumup.access_token = data["access_token"]
    if "refresh_token" in data:
        artist_sumup.refresh_token = data["refresh_token"]
    artist_sumup.expires_at = timezone.now() + datetime.timedelta(seconds=data.get("expires_in", 600) - 30)
    artist_sumup.token_type = data.get("token_type", "Bearer")
    artist_sumup.save()
    return artist_sumup.access_token

def get_artist_token(artist_sumup):
    if not artist_sumup:
        raise ValueError("Artist not connected to SumUp.")
    if artist_sumup.expires_at <= timezone.now():
        return refresh_access_token(artist_sumup)
    return artist_sumup.access_token

def create_checkout_for_artist(artist_sumup, *, amount, currency, reference, description, return_url):
    token = get_artist_token(artist_sumup)
    r = requests.post(
        f"{settings.SUMUP_API_URL}/checkouts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "amount": float(amount),
            "currency": currency,
            "checkout_reference": reference,
            "description": description,
            "return_url": return_url,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def get_checkout(artist_sumup, checkout_id):
    token = get_artist_token(artist_sumup)
    r = requests.get(
        f"{settings.SUMUP_API_URL}/checkouts/{checkout_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def get_merchant_info(access_token):
    """Get merchant information from SumUp."""
    try:
        r = requests.get(
            f"{settings.SUMUP_API_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return {
            'merchant_code': data.get('merchant_profile', {}).get('merchant_code', ''),
            'business_name': data.get('merchant_profile', {}).get('business_name', ''),
            'email': data.get('email', '')
        }
    except Exception as e:
        logger.error(f"Failed to get merchant info: {e}")
        return {}

def refresh_access_token_direct(refresh_token):
    """Refresh access token using refresh token."""
    r = requests.post(
        f"{settings.SUMUP_BASE_URL}/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.SUMUP_CLIENT_ID,
            "client_secret": settings.SUMUP_CLIENT_SECRET,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def create_checkout_simple(amount, currency, reference, description, return_url, redirect_url=None, enable_hosted_checkout=False, expected_amount=None):
    """Create checkout using platform's merchant code (no OAuth).

    Args:
        amount: The amount to charge
        currency: Currency code (e.g., 'GBP')
        reference: Unique reference for this checkout
        description: Description of the purchase
        return_url: URL to return to after payment
        redirect_url: Optional redirect URL
        enable_hosted_checkout: Enable SumUp hosted checkout
        expected_amount: Optional expected amount to validate against (SECURITY)

    ⚠️  CRITICAL SECURITY: Always pass expected_amount to prevent amount manipulation!
    """
    # SECURITY: Validate amount matches expected amount
    if expected_amount is not None:
        if float(amount) != float(expected_amount):
            logger.error(
                f"SECURITY WARNING: Payment amount mismatch! "
                f"Requested: {amount}, Expected: {expected_amount}, "
                f"Reference: {reference}"
            )
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Payment amount validation failed. Amount {amount} does not match expected {expected_amount}"
            )

    # Log all payment attempts for audit trail
    logger.info(
        f"Creating SumUp checkout: Amount={amount} {currency}, "
        f"Reference={reference}, Description={description}"
    )

    # Get a valid access token
    access_token = get_platform_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Ensure amount is properly formatted
    validated_amount = float(amount)
    if validated_amount <= 0:
        raise ValidationError("Payment amount must be greater than 0")

    payload = {
        "checkout_reference": reference,
        "amount": validated_amount,
        "currency": currency,
        "description": description,
        "merchant_code": settings.SUMUP_MERCHANT_CODE,
        "return_url": return_url
    }

    if redirect_url:
        payload["redirect_url"] = redirect_url

    # Enable hosted checkout for direct redirects
    if enable_hosted_checkout:
        payload["hosted_checkout"] = {"enabled": True}

    try:
        r = requests.post(
            f"{settings.SUMUP_API_URL}/checkouts",
            headers=headers,
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        result = r.json()

        # Log successful checkout creation
        logger.info(f"SumUp checkout created successfully: {result.get('id', 'unknown')}")
        return result

    except Exception as e:
        logger.error(f"Failed to create SumUp checkout: {e}, Reference: {reference}")
        raise

def get_checkout_status(checkout_id):
    """Get checkout status using platform credentials."""
    access_token = get_platform_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        f"{settings.SUMUP_API_URL}/checkouts/{checkout_id}",
        headers=headers,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def list_transactions(limit=50, order="desc"):
    """List recent transactions."""
    access_token = get_platform_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    params = {
        "limit": limit,
        "order": order
    }

    r = requests.get(
        f"{settings.SUMUP_API_URL}/me/transactions/history",
        headers=headers,
        params=params,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def get_transaction(transaction_id):
    """Get specific transaction details."""
    access_token = get_platform_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        f"{settings.SUMUP_API_URL}/me/transactions/{transaction_id}",
        headers=headers,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def process_refund(transaction_id, amount=None):
    """Process a refund for a transaction."""
    access_token = get_platform_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {}
    if amount:
        payload["amount"] = float(amount)

    r = requests.post(
        f"{settings.SUMUP_API_URL}/me/transactions/{transaction_id}/refund",
        headers=headers,
        json=payload if payload else None,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

# Removed duplicate functions - they are defined earlier in the file

def create_checkout_for_connected_artist(artist_profile, *, amount, currency, reference, description, return_url):
    """Create checkout for artist with their own SumUp connection."""
    # Check if artist token is still valid
    if artist_profile.sumup_token_expired:
        # Try to refresh token
        try:
            new_token_data = refresh_access_token_direct(artist_profile.sumup_refresh_token)
            artist_profile.update_sumup_connection(new_token_data)
        except Exception as e:
            raise ValueError(f"Artist SumUp token expired and refresh failed: {e}")

    r = requests.post(
        f"{settings.SUMUP_API_URL}/checkouts",
        headers={
            "Authorization": f"Bearer {artist_profile.sumup_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "amount": float(amount),
            "currency": currency,
            "checkout_reference": reference,
            "description": description,
            "return_url": return_url,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def get_checkout_for_artist(artist_profile, checkout_id):
    """Get checkout status for artist with their own connection."""
    if artist_profile.sumup_token_expired:
        try:
            new_token_data = refresh_access_token_direct(artist_profile.sumup_refresh_token)
            artist_profile.update_sumup_connection(new_token_data)
        except Exception as e:
            raise ValueError(f"Artist SumUp token expired and refresh failed: {e}")

    r = requests.get(
        f"{settings.SUMUP_API_URL}/checkouts/{checkout_id}",
        headers={"Authorization": f"Bearer {artist_profile.sumup_access_token}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()
