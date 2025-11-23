"""Management command to check SumUp OAuth configuration."""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
import sys


class Command(BaseCommand):
    help = 'Check SumUp OAuth configuration and identify issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed configuration values (masks secrets)',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("SumUp OAuth Configuration Check"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        issues = []
        warnings = []

        # Check SUMUP_CLIENT_ID
        if not settings.SUMUP_CLIENT_ID:
            issues.append("❌ SUMUP_CLIENT_ID is not set")
        else:
            self.stdout.write(self.style.SUCCESS("✓ SUMUP_CLIENT_ID is configured"))
            if verbose:
                masked = settings.SUMUP_CLIENT_ID[:20] + "..." if len(settings.SUMUP_CLIENT_ID) > 20 else settings.SUMUP_CLIENT_ID
                self.stdout.write(f"  Value: {masked}")

        # Check SUMUP_CLIENT_SECRET
        if not settings.SUMUP_CLIENT_SECRET:
            issues.append("❌ SUMUP_CLIENT_SECRET is not set")
        else:
            self.stdout.write(self.style.SUCCESS("✓ SUMUP_CLIENT_SECRET is configured"))
            if verbose:
                self.stdout.write(f"  Length: {len(settings.SUMUP_CLIENT_SECRET)} characters")

        # Check SUMUP_REDIRECT_URI
        if not settings.SUMUP_REDIRECT_URI:
            issues.append("❌ SUMUP_REDIRECT_URI is not set - THIS IS CRITICAL!")
        else:
            self.stdout.write(self.style.SUCCESS("✓ SUMUP_REDIRECT_URI is configured"))
            self.stdout.write(f"  Value: {settings.SUMUP_REDIRECT_URI}")

            # Validate redirect URI format
            if not settings.SUMUP_REDIRECT_URI.startswith('https://'):
                warnings.append("⚠️  SUMUP_REDIRECT_URI should use HTTPS in production")

            if '/accounts/sumup/callback/' not in settings.SUMUP_REDIRECT_URI:
                warnings.append("⚠️  SUMUP_REDIRECT_URI should point to /accounts/sumup/callback/")

        # Check SUMUP_API_URL and SUMUP_BASE_URL
        self.stdout.write(self.style.SUCCESS("✓ SUMUP_API_URL is configured"))
        self.stdout.write(f"  Value: {settings.SUMUP_API_URL}")
        self.stdout.write(self.style.SUCCESS("✓ SUMUP_BASE_URL is configured"))
        self.stdout.write(f"  Value: {settings.SUMUP_BASE_URL}")

        # Check SUMUP_MERCHANT_CODE
        if not settings.SUMUP_MERCHANT_CODE:
            warnings.append("⚠️  SUMUP_MERCHANT_CODE is not set (needed for platform payments)")
        else:
            self.stdout.write(self.style.SUCCESS("✓ SUMUP_MERCHANT_CODE is configured"))
            if verbose:
                self.stdout.write(f"  Value: {settings.SUMUP_MERCHANT_CODE}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Expected OAuth Flow"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        if settings.SUMUP_REDIRECT_URI:
            # Extract base URL from redirect URI
            from urllib.parse import urlparse
            parsed = urlparse(settings.SUMUP_REDIRECT_URI)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            self.stdout.write("1. User clicks 'Connect to SumUp' button")
            self.stdout.write(f"2. User is redirected to: {settings.SUMUP_BASE_URL}/authorize")
            self.stdout.write("3. User authorizes the application on SumUp")
            self.stdout.write(f"4. SumUp redirects back to: {settings.SUMUP_REDIRECT_URI}")
            self.stdout.write(f"5. Django processes the callback at: /accounts/sumup/callback/")
        else:
            self.stdout.write(self.style.ERROR("Cannot show expected flow - SUMUP_REDIRECT_URI not set"))

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Summary"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        if issues:
            self.stdout.write(self.style.ERROR("CRITICAL ISSUES:"))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f"  {issue}"))
            self.stdout.write("")

        if warnings:
            self.stdout.write(self.style.WARNING("WARNINGS:"))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f"  {warning}"))
            self.stdout.write("")

        if not issues and not warnings:
            self.stdout.write(self.style.SUCCESS("✓ All SumUp OAuth settings are properly configured!"))
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("1. Ensure your SumUp OAuth application has this redirect URI whitelisted:")
            self.stdout.write(f"   {settings.SUMUP_REDIRECT_URI}")
            self.stdout.write("2. Verify the redirect URI in your SumUp Developer Dashboard")
            self.stdout.write("3. Test the OAuth flow by clicking 'Connect to SumUp' in your dashboard")
        elif issues:
            self.stdout.write(self.style.ERROR("Configuration has critical issues. Please fix the above issues."))
            self.stdout.write("")
            self.stdout.write("To fix, set the following environment variables:")
            for issue in issues:
                if "CLIENT_ID" in issue:
                    self.stdout.write("  export SUMUP_CLIENT_ID='your-client-id'")
                if "CLIENT_SECRET" in issue:
                    self.stdout.write("  export SUMUP_CLIENT_SECRET='your-client-secret'")
                if "REDIRECT_URI" in issue:
                    self.stdout.write("  export SUMUP_REDIRECT_URI='https://tickets.coderra.je/accounts/sumup/callback/'")
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("Configuration looks good with minor warnings."))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 80))
