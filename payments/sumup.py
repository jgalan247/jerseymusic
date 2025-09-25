# payments/sumup.py
import time, requests, datetime
from django.utils import timezone
from django.conf import settings

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
        f"{settings.SUMUP_BASE_URL}/v0.1/checkouts",
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
        f"{settings.SUMUP_BASE_URL}/v0.1/checkouts/{checkout_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def create_checkout_simple(amount, currency, reference, description, return_url, redirect_url=None):
    """Create checkout using platform's merchant code (no OAuth)."""
    headers = {
        "Authorization": f"Bearer {settings.SUMUP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "checkout_reference": reference,
        "amount": float(amount),
        "currency": currency,
        "description": description,
        "merchant_code": settings.SUMUP_MERCHANT_CODE,
        "return_url": return_url
    }

    if redirect_url:
        payload["redirect_url"] = redirect_url

    r = requests.post(
        f"{settings.SUMUP_API_URL}/checkouts",
        headers=headers,
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def get_checkout_status(checkout_id):
    """Get checkout status using platform credentials."""
    headers = {
        "Authorization": f"Bearer {settings.SUMUP_ACCESS_TOKEN}"
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
    headers = {
        "Authorization": f"Bearer {settings.SUMUP_ACCESS_TOKEN}"
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
    headers = {
        "Authorization": f"Bearer {settings.SUMUP_ACCESS_TOKEN}"
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
    headers = {
        "Authorization": f"Bearer {settings.SUMUP_ACCESS_TOKEN}",
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
