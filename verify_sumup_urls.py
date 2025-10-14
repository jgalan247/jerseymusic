#!/usr/bin/env python
"""
SumUp URL Verification Script

This script verifies that all SumUp-related URLs are properly configured
and accessible in the Django project.

Usage:
    python verify_sumup_urls.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.urls import resolve, reverse, NoReverseMatch
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

# Simple color helper (fallback if termcolor not available)
def colored(text, color=None, attrs=None):
    """Simple color wrapper."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'magenta': '\033[95m',
    }
    reset = '\033[0m'
    bold = '\033[1m' if attrs and 'bold' in attrs else ''
    dim = '\033[2m' if attrs and 'dim' in attrs else ''

    color_code = colors.get(color, '')
    return f"{bold}{dim}{color_code}{text}{reset}"


class URLVerifier:
    """Verifies SumUp URL configuration."""

    def __init__(self):
        self.factory = RequestFactory()
        self.results = []

    def verify_url_pattern(self, url_name, url_path=None, needs_args=None):
        """
        Verify a URL pattern exists and resolves correctly.

        Args:
            url_name: Django URL name (e.g., 'accounts:sumup_connect')
            url_path: Expected URL path (e.g., '/accounts/sumup/connect/')
            needs_args: Dict of args needed for reverse (e.g., {'order_id': 1})
        """
        try:
            # Test reverse URL lookup
            if needs_args:
                reversed_url = reverse(url_name, kwargs=needs_args)
            else:
                reversed_url = reverse(url_name)

            # Test URL resolution
            resolved = resolve(reversed_url)

            # Check if path matches expected
            if url_path and reversed_url != url_path:
                self.results.append({
                    'name': url_name,
                    'status': 'warning',
                    'message': f"URL mismatch: expected '{url_path}', got '{reversed_url}'"
                })
            else:
                self.results.append({
                    'name': url_name,
                    'status': 'success',
                    'url': reversed_url,
                    'view': f"{resolved.func.__module__}.{resolved.func.__name__}"
                })

        except NoReverseMatch as e:
            self.results.append({
                'name': url_name,
                'status': 'error',
                'message': f"URL not found: {e}"
            })
        except Exception as e:
            self.results.append({
                'name': url_name,
                'status': 'error',
                'message': f"Error: {e}"
            })

    def verify_all(self):
        """Verify all SumUp URLs."""
        print(colored("\n" + "=" * 80, "cyan"))
        print(colored("SumUp URL Verification", "cyan", attrs=["bold"]))
        print(colored("=" * 80 + "\n", "cyan"))

        # OAuth URLs (accounts app)
        print(colored("OAuth URLs (Accounts App)", "yellow", attrs=["bold"]))
        print("-" * 80)

        self.verify_url_pattern(
            'accounts:sumup_connect',
            '/accounts/sumup/connect/'
        )
        self.verify_url_pattern(
            'accounts:sumup_callback',
            '/accounts/sumup/callback/'
        )
        self.verify_url_pattern(
            'accounts:sumup_disconnect',
            '/accounts/sumup/disconnect/'
        )
        self.verify_url_pattern(
            'accounts:sumup_status',
            '/accounts/sumup/status/'
        )

        # Payment URLs (payments app)
        print(colored("\nPayment URLs (Payments App)", "yellow", attrs=["bold"]))
        print("-" * 80)

        self.verify_url_pattern(
            'payments:simple_checkout',
            '/payments/simple-checkout/'
        )
        self.verify_url_pattern(
            'payments:redirect_checkout',
            '/payments/redirect/checkout/1/',
            needs_args={'order_id': 1}
        )
        self.verify_url_pattern(
            'payments:sumup_checkout',
            '/payments/sumup/checkout/1/',
            needs_args={'order_id': 1}
        )
        self.verify_url_pattern(
            'payments:connected_sumup_checkout',
            '/payments/sumup/connected-checkout/1/',
            needs_args={'order_id': 1}
        )
        self.verify_url_pattern(
            'payments:sumup_success',
            '/payments/sumup/success/'
        )
        self.verify_url_pattern(
            'payments:sumup_callback',
            '/payments/sumup/callback/'
        )
        self.verify_url_pattern(
            'payments:sumup_webhook',
            '/payments/sumup/webhook/'
        )

        # Legacy OAuth URLs (payments app)
        print(colored("\nLegacy OAuth URLs (Payments App)", "yellow", attrs=["bold"]))
        print("-" * 80)

        self.verify_url_pattern(
            'payments:sumup_connect_start',
            '/payments/sumup/oauth/connect/1/',
            needs_args={'artist_id': 1}
        )
        self.verify_url_pattern(
            'payments:sumup_oauth_callback',
            '/payments/sumup/oauth/callback/'
        )

        # Widget URLs
        print(colored("\nWidget URLs (Payments App)", "yellow", attrs=["bold"]))
        print("-" * 80)

        self.verify_url_pattern(
            'payments:widget_checkout',
            '/payments/widget/checkout/1/',
            needs_args={'order_id': 1}
        )
        self.verify_url_pattern(
            'payments:widget_checkout_fixed',
            '/payments/widget-fixed/checkout/1/',
            needs_args={'order_id': 1}
        )

    def verify_nonexistent_urls(self):
        """Verify that incorrect URLs DO NOT exist."""
        print(colored("\nVerifying Non-Existent URLs", "magenta", attrs=["bold"]))
        print("-" * 80)

        # Test the URL that user reported as 404
        nonexistent_urls = [
            '/payments/sumup/initiate/',
            '/events/sumup/callback/',
            '/auth/sumup/callback/',
        ]

        for url_path in nonexistent_urls:
            try:
                resolved = resolve(url_path)
                self.results.append({
                    'name': url_path,
                    'status': 'warning',
                    'message': f"URL exists but shouldn't: {resolved.func}"
                })
            except:
                self.results.append({
                    'name': url_path,
                    'status': 'expected',
                    'message': "Correctly returns 404 (as expected)"
                })

    def print_results(self):
        """Print verification results."""
        print(colored("\n" + "=" * 80, "cyan"))
        print(colored("Verification Results", "cyan", attrs=["bold"]))
        print(colored("=" * 80 + "\n", "cyan"))

        success_count = 0
        warning_count = 0
        error_count = 0
        expected_count = 0

        for result in self.results:
            status = result['status']
            name = result['name']

            if status == 'success':
                success_count += 1
                icon = colored("✅", "green")
                print(f"{icon} {colored(name, 'green')}")
                if 'url' in result:
                    print(f"   URL: {result['url']}")
                if 'view' in result:
                    print(f"   View: {colored(result['view'], 'white', attrs=['dim'])}")

            elif status == 'expected':
                expected_count += 1
                icon = colored("✓", "cyan")
                print(f"{icon} {colored(name, 'cyan')}")
                if 'message' in result:
                    print(f"   {colored(result['message'], 'cyan', attrs=['dim'])}")

            elif status == 'warning':
                warning_count += 1
                icon = colored("⚠️", "yellow")
                print(f"{icon} {colored(name, 'yellow')}")
                if 'message' in result:
                    print(f"   {colored(result['message'], 'yellow')}")

            elif status == 'error':
                error_count += 1
                icon = colored("❌", "red")
                print(f"{icon} {colored(name, 'red', attrs=['bold'])}")
                if 'message' in result:
                    print(f"   {colored(result['message'], 'red')}")

            print()

        # Summary
        print(colored("=" * 80, "cyan"))
        print(colored("Summary", "cyan", attrs=["bold"]))
        print(colored("=" * 80, "cyan"))
        print(f"{colored('✅ Success:', 'green')} {success_count} URLs")
        print(f"{colored('✓  Expected:', 'cyan')} {expected_count} non-existent URLs (correct)")
        print(f"{colored('⚠️  Warnings:', 'yellow')} {warning_count} URLs")
        print(f"{colored('❌ Errors:', 'red')} {error_count} URLs")
        print()

        if error_count > 0:
            print(colored("❌ FAILED: Some URLs are not configured correctly.", "red", attrs=["bold"]))
            return False
        elif warning_count > 0:
            print(colored("⚠️  PASSED with warnings: Some URLs have minor issues.", "yellow", attrs=["bold"]))
            return True
        else:
            print(colored("✅ PASSED: All URLs are configured correctly!", "green", attrs=["bold"]))
            return True

    def run(self):
        """Run all verifications."""
        try:
            self.verify_all()
            self.verify_nonexistent_urls()
            success = self.print_results()

            print(colored("\n" + "=" * 80, "cyan"))
            print(colored("Documentation", "cyan", attrs=["bold"]))
            print(colored("=" * 80, "cyan"))
            print("For complete URL reference, see:")
            print(colored("  📄 SUMUP_URLS_REFERENCE.md", "white", attrs=["bold"]))
            print()

            sys.exit(0 if success else 1)

        except Exception as e:
            print(colored(f"\n❌ Error running verification: {e}", "red", attrs=["bold"]))
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    print(colored("\n🔍 Verifying SumUp URL Configuration...\n", "cyan", attrs=["bold"]))

    verifier = URLVerifier()
    verifier.run()


if __name__ == '__main__':
    main()
