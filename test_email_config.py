#!/usr/bin/env python
"""
Test email configuration
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from events.email_utils import email_service

def main():
    print("📧 TESTING EMAIL CONFIGURATION")
    print("=" * 40)

    # Test email configuration
    test_results = email_service.test_email_configuration()

    print(f"Backend: {test_results['backend']}")
    print(f"From Email: {test_results['from_email']}")
    print(f"Configured: {'✅' if test_results['configured'] else '❌'}")
    print(f"Test Email Sent: {'✅' if test_results['test_sent'] else '❌'}")

    if test_results['error']:
        print(f"Error: {test_results['error']}")

    # Test sending a real email
    print("\n📨 TESTING EMAIL DELIVERY")
    print("-" * 30)

    try:
        success = email_service.send_email_with_retry(
            subject="Jersey Events Test Email",
            message="This is a test email to verify the email system is working correctly.",
            recipient_list=['admin@jerseyevents.com']  # Use a test email
        )

        if success:
            print("✅ Test email sent successfully!")
            print("📧 Check console output or email backend for delivery")
        else:
            print("❌ Test email failed to send")

    except Exception as e:
        print(f"❌ Email test failed: {e}")

    print("\n" + "=" * 40)
    print("EMAIL CONFIGURATION TEST COMPLETE")

if __name__ == "__main__":
    main()