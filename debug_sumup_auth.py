#!/usr/bin/env python3
"""
Debug script for SumUp authentication setup.
"""

import os
import sys
import requests
import json
from urllib.parse import urlencode
import base64

# Load environment variables from .env file
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)
    print("✅ Loaded .env file")
else:
    print("❌ No .env file found")

def check_environment_variables():
    """Check and display SumUp environment variables."""
    print("\n" + "=" * 60)
    print("SumUp Environment Variables")
    print("=" * 60)

    env_vars = {
        'SUMUP_CLIENT_ID': os.getenv('SUMUP_CLIENT_ID'),
        'SUMUP_CLIENT_SECRET': os.getenv('SUMUP_CLIENT_SECRET'),
        'SUMUP_API_KEY': os.getenv('SUMUP_API_KEY'),
        'SUMUP_MERCHANT_ID': os.getenv('SUMUP_MERCHANT_ID'),
        'SUMUP_MERCHANT_CODE': os.getenv('SUMUP_MERCHANT_CODE'),
        'SUMUP_BASE_URL': os.getenv('SUMUP_BASE_URL'),
        'SUMUP_API_URL': os.getenv('SUMUP_API_URL'),
        'SUMUP_API_BASE_URL': os.getenv('SUMUP_API_BASE_URL'),
        'SUMUP_REDIRECT_URI': os.getenv('SUMUP_REDIRECT_URI'),
        'SUMUP_WEBHOOK_URL': os.getenv('SUMUP_WEBHOOK_URL'),
    }

    for key, value in env_vars.items():
        if value:
            if 'SECRET' in key:
                # Mask secret values
                masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
                print(f"{key:25} = {masked}")
            else:
                print(f"{key:25} = {value}")
        else:
            print(f"{key:25} = [NOT SET]")

    # Check for issues
    issues = []
    if not env_vars['SUMUP_CLIENT_ID']:
        issues.append("❌ SUMUP_CLIENT_ID is not set")
    if not env_vars['SUMUP_CLIENT_SECRET']:
        issues.append("❌ SUMUP_CLIENT_SECRET is not set")

    # Check for spaces or quotes
    for key, value in env_vars.items():
        if value:
            if value.startswith('"') or value.endswith('"'):
                issues.append(f"⚠️  {key} has quotes - remove them")
            if value.startswith(' ') or value.endswith(' '):
                issues.append(f"⚠️  {key} has extra spaces")

    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ Environment variables look correct")

    return env_vars

def test_oauth_token_request(client_id, client_secret):
    """Test getting an OAuth access token."""
    print("\n" + "=" * 60)
    print("Testing OAuth Token Request")
    print("=" * 60)

    if not client_id or not client_secret:
        print("❌ Missing client credentials")
        return None

    # Try different API endpoints
    endpoints = [
        ("Production", "https://api.sumup.com/token"),
        ("Sandbox", "https://api.sandbox.sumup.com/token"),
    ]

    for env_name, token_url in endpoints:
        print(f"\n🔍 Testing {env_name}: {token_url}")

        # Method 1: Form data with client credentials
        print("  Method 1: Form data authentication")
        try:
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': 'payments'
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=10
            )

            print(f"    Status: {response.status_code}")
            if response.status_code == 200:
                token_data = response.json()
                print(f"    ✅ Success! Token type: {token_data.get('token_type')}")
                print(f"    Access token: {token_data.get('access_token', '')[:20]}...")
                print(f"    Scope: {token_data.get('scope')}")
                print(f"    Expires in: {token_data.get('expires_in')} seconds")
                return token_data
            else:
                print(f"    ❌ Failed: {response.text[:200]}")
        except Exception as e:
            print(f"    ❌ Error: {e}")

        # Method 2: Basic authentication
        print("  Method 2: Basic authentication")
        try:
            credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'scope': 'payments'
                },
                headers={
                    'Authorization': f'Basic {credentials}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=10
            )

            print(f"    Status: {response.status_code}")
            if response.status_code == 200:
                token_data = response.json()
                print(f"    ✅ Success! Token type: {token_data.get('token_type')}")
                print(f"    Access token: {token_data.get('access_token', '')[:20]}...")
                return token_data
            else:
                print(f"    ❌ Failed: {response.text[:200]}")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    return None

def test_api_key_authentication(api_key):
    """Test API key authentication."""
    print("\n" + "=" * 60)
    print("Testing API Key Authentication")
    print("=" * 60)

    if not api_key:
        print("❌ No API key set")
        return False

    endpoints = [
        ("Production", "https://api.sumup.com/v0.1/me"),
        ("Sandbox", "https://api.sandbox.sumup.com/v0.1/me"),
    ]

    for env_name, url in endpoints:
        print(f"\n🔍 Testing {env_name}: {url}")

        try:
            response = requests.get(
                url,
                headers={
                    'Authorization': f'Bearer {api_key}'
                },
                timeout=10
            )

            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ API key works for {env_name}")
                data = response.json()
                print(f"  Merchant: {data.get('merchant_profile', {}).get('merchant_code', 'Unknown')}")
                return True
            else:
                print(f"  ❌ Failed: {response.text[:200]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    return False

def test_checkout_creation(token_data):
    """Test creating a checkout with the token."""
    print("\n" + "=" * 60)
    print("Testing Checkout Creation")
    print("=" * 60)

    if not token_data:
        print("❌ No access token available")
        return

    access_token = token_data.get('access_token')

    endpoints = [
        ("Production", "https://api.sumup.com/v0.1/checkouts"),
        ("Sandbox", "https://api.sandbox.sumup.com/v0.1/checkouts"),
    ]

    checkout_data = {
        "checkout_reference": "test_checkout_123",
        "amount": 10.00,
        "currency": "GBP",
        "description": "Test checkout",
        "return_url": "https://86a7ab44d9e2.ngrok-free.app/payments/success/"
    }

    for env_name, url in endpoints:
        print(f"\n🔍 Testing {env_name}: {url}")

        try:
            response = requests.post(
                url,
                json=checkout_data,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )

            print(f"  Status: {response.status_code}")
            if response.status_code in [200, 201]:
                print(f"  ✅ Checkout created successfully!")
                data = response.json()
                print(f"  Checkout ID: {data.get('id')}")
                print(f"  Checkout URL: {data.get('checkout_url', 'N/A')}")
                return True
            else:
                print(f"  ❌ Failed: {response.text[:300]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    return False

def main():
    """Run all authentication tests."""
    print("=" * 60)
    print("SumUp Authentication Debug Tool")
    print("=" * 60)

    # Step 1: Check environment variables
    env_vars = check_environment_variables()

    # Extract key variables
    client_id = env_vars.get('SUMUP_CLIENT_ID')
    client_secret = env_vars.get('SUMUP_CLIENT_SECRET')
    api_key = env_vars.get('SUMUP_API_KEY')

    # Step 2: Test OAuth token request
    token_data = test_oauth_token_request(client_id, client_secret)

    # Step 3: Test API key authentication (if available)
    if api_key:
        test_api_key_authentication(api_key)

    # Step 4: Test checkout creation
    if token_data:
        test_checkout_creation(token_data)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if token_data:
        print("✅ OAuth authentication works")
        print("📝 Next steps:")
        print("  1. Store the access token in your application")
        print("  2. Use Bearer authentication with the access token")
        print("  3. Include merchant_code in checkout requests if required")
    else:
        print("❌ OAuth authentication failed")
        print("📝 Troubleshooting:")
        print("  1. Verify client credentials are correct")
        print("  2. Check if using sandbox vs production credentials")
        print("  3. Ensure no extra spaces or quotes in .env file")
        print("  4. Contact SumUp support if credentials are correct")

if __name__ == "__main__":
    main()