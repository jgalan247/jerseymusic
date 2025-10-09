#!/usr/bin/env python
"""
Quick Payment Test After SumUp Credential Setup
Run after configuring SumUp credentials to verify fix
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.conf import settings

def test_sumup_credentials():
    """Test if SumUp credentials are now properly configured"""
    print("🔍 TESTING SUMUP CREDENTIALS AFTER SETUP")
    print("-" * 50)

    required_settings = [
        'SUMUP_CLIENT_ID', 'SUMUP_CLIENT_SECRET',
        'SUMUP_MERCHANT_CODE', 'SUMUP_ACCESS_TOKEN'
    ]

    all_configured = True

    for setting in required_settings:
        value = getattr(settings, setting, None)
        if value:
            print(f"✅ {setting}: {'*' * min(len(str(value)), 8)}...")
        else:
            print(f"❌ {setting}: MISSING")
            all_configured = False

    if all_configured:
        print("\n🟢 SUCCESS: All SumUp credentials configured!")
        print("✅ Payment processing should now work")
        return True
    else:
        print("\n🔴 STILL MISSING CREDENTIALS")
        print("❌ Update your .env file with actual SumUp values")
        return False

if __name__ == "__main__":
    success = test_sumup_credentials()
    sys.exit(0 if success else 1)