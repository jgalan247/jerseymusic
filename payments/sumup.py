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
    base = f"{settings.SUMUP_BASE_URL}/authorize"
    return (
        f"{base}?response_type=code"
        f"&client_id={settings.SUMUP_CLIENT_ID}"
        f"&redirect_uri={settings.SUMUP_REDIRECT_URI}"
        f"&scope=payments%20checkouts"  # add scopes you need
        f"&state={state}"
    )

def exchange_code_for_tokens(code: str):
    r = requests.post(
        f"{settings.SUMUP_BASE_URL}/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.SUMUP_CLIENT_ID,
            "client_secret": settings.SUMUP_CLIENT_SECRET,
            "redirect_uri": settings.SUMUP_REDIRECT_URI,
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    expires_in = data.get("expires_in", 600)
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "token_type": data.get("token_type", "Bearer"),
        "expires_at": timezone.now() + datetime.timedelta(seconds=expires_in - 30),
        "scope": data.get("scope", ""),
    }

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
