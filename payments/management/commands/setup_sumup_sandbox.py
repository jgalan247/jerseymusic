"""Management command to configure SumUp sandbox environment for testing."""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
import os
import requests
import json

from accounts.models import ArtistProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up SumUp sandbox environment for payment testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-connection',
            action='store_true',
            help='Verify sandbox API connection',
        )
        parser.add_argument(
            '--create-test-tokens',
            action='store_true',
            help='Create test OAuth tokens for connected artists',
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Show current SumUp configuration',
        )

    def print_success(self, message):
        self.stdout.write(self.style.SUCCESS(f"✅ {message}"))

    def print_info(self, message):
        self.stdout.write(f"📊 {message}")

    def print_warning(self, message):
        self.stdout.write(self.style.WARNING(f"⚠️ {message}"))

    def print_error(self, message):
        self.stdout.write(self.style.ERROR(f"❌ {message}"))

    def check_environment_variables(self):
        """Check if SumUp environment variables are configured."""
        self.print_info("Checking SumUp environment configuration...")

        required_vars = [
            'SUMUP_CLIENT_ID',
            'SUMUP_CLIENT_SECRET',
            'SUMUP_REDIRECT_URI',
            'SUMUP_BASE_URL',
            'SITE_URL'
        ]

        missing_vars = []
        for var in required_vars:
            value = getattr(settings, var, None) or os.getenv(var)
            if not value or value.startswith('your_'):
                missing_vars.append(var)
            else:
                # Mask sensitive values
                if 'SECRET' in var:
                    display_value = '***CONFIGURED***'
                else:
                    display_value = value
                self.print_success(f"{var}: {display_value}")

        if missing_vars:
            self.print_error(f"Missing or placeholder environment variables: {', '.join(missing_vars)}")
            return False

        return True

    def show_sandbox_configuration(self):
        """Show current SumUp sandbox configuration."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO("🔧 SUMUP SANDBOX CONFIGURATION"))
        self.stdout.write("="*60)

        config_items = [
            ('Client ID', getattr(settings, 'SUMUP_CLIENT_ID', 'Not configured')),
            ('Sandbox Base URL', getattr(settings, 'SUMUP_BASE_URL', 'Not configured')),
            ('API URL', getattr(settings, 'SUMUP_API_URL', 'Not configured')),
            ('Redirect URI', getattr(settings, 'SUMUP_REDIRECT_URI', 'Not configured')),
            ('Site URL', getattr(settings, 'SITE_URL', 'Not configured')),
        ]

        for label, value in config_items:
            if 'Not configured' in str(value) or str(value).startswith('your_'):
                self.print_error(f"{label}: {value}")
            else:
                self.print_success(f"{label}: {value}")

        # Show environment recommendations
        self.print_info("\nSandbox Environment Variables:")
        sandbox_config = """
# SumUp Sandbox Configuration
SUMUP_CLIENT_ID=your_sandbox_client_id
SUMUP_CLIENT_SECRET=your_sandbox_client_secret
SUMUP_REDIRECT_URI=http://localhost:8000/accounts/sumup/callback/
SUMUP_BASE_URL=https://api.sandbox.sumup.com
SUMUP_API_URL=https://api.sandbox.sumup.com/v0.1
SITE_URL=http://localhost:8000

# Test Mode
SUMUP_SANDBOX_MODE=True
        """.strip()

        self.stdout.write(sandbox_config)

    def verify_api_connection(self):
        """Verify connection to SumUp sandbox API."""
        self.print_info("Verifying SumUp sandbox API connection...")

        try:
            base_url = getattr(settings, 'SUMUP_BASE_URL', 'https://api.sandbox.sumup.com')

            # Test basic API connectivity
            response = requests.get(f"{base_url}/v0.1/me", timeout=10)

            if response.status_code == 401:
                self.print_success("API endpoint is accessible (401 Unauthorized expected without token)")
                return True
            elif response.status_code == 200:
                self.print_success("API endpoint is accessible and responding")
                return True
            else:
                self.print_warning(f"API returned status code: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_error("Cannot connect to SumUp sandbox API")
            return False
        except requests.exceptions.Timeout:
            self.print_error("SumUp sandbox API request timed out")
            return False
        except Exception as e:
            self.print_error(f"API connection test failed: {e}")
            return False

    def create_test_oauth_tokens(self):
        """Create realistic test OAuth tokens for connected artists."""
        self.print_info("Creating test OAuth tokens for connected artists...")

        # Find artists marked as connected but without proper tokens
        connected_artists = ArtistProfile.objects.filter(
            sumup_connection_status='connected'
        )

        if not connected_artists.exists():
            self.print_warning("No connected artists found. Run setup_sumup_test_data first.")
            return

        test_tokens = [
            {
                'access_token': 'sk_test_12345abcdef67890ghijklmnop123456',
                'refresh_token': 'rt_test_abcdef123456789012345678901234567890',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': 'payments',
                'merchant_code': 'MERCH001'
            },
            {
                'access_token': 'sk_test_67890fedcba54321ponmlkjihgfed6543',
                'refresh_token': 'rt_test_fedcba098765432109876543210987654321',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': 'payments',
                'merchant_code': 'MERCH002'
            },
            {
                'access_token': 'sk_test_abcdef1234567890fedcba0987654321',
                'refresh_token': 'rt_test_1234567890abcdef0987654321fedcba',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': 'payments',
                'merchant_code': 'MERCH003'
            }
        ]

        updated_artists = []
        for i, artist in enumerate(connected_artists):
            if i < len(test_tokens):
                token_data = test_tokens[i]
                artist.update_sumup_connection(token_data)
                artist.save()

                updated_artists.append(artist)
                self.print_success(f"Updated tokens for {artist.display_name} (Merchant: {token_data['merchant_code']})")

        return updated_artists

    def test_payment_creation(self):
        """Test creating a payment request with sandbox tokens."""
        self.print_info("Testing payment request creation...")

        # Get a connected artist
        connected_artist = ArtistProfile.objects.filter(
            sumup_connection_status='connected',
            sumup_access_token__isnull=False
        ).exclude(sumup_access_token='').first()

        if not connected_artist:
            self.print_warning("No connected artist with tokens found")
            return False

        try:
            # Create a test payment request (don't actually process)
            test_payment_data = {
                'checkout_reference': f'TEST_CHECKOUT_{connected_artist.id}',
                'amount': 25.50,
                'currency': 'GBP',
                'description': 'Test ticket purchase',
                'return_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/payments/success/",
                'merchant_code': connected_artist.sumup_merchant_code
            }

            self.print_success(f"Test payment data prepared for {connected_artist.display_name}:")
            for key, value in test_payment_data.items():
                self.stdout.write(f"  {key}: {value}")

            return True

        except Exception as e:
            self.print_error(f"Payment test preparation failed: {e}")
            return False

    def validate_webhook_endpoints(self):
        """Validate webhook endpoint configuration."""
        self.print_info("Validating webhook endpoints...")

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        webhook_endpoints = [
            f"{site_url}/payments/sumup/webhook/",
            f"{site_url}/payments/webhook/success/",
            f"{site_url}/payments/webhook/failure/"
        ]

        for endpoint in webhook_endpoints:
            self.print_info(f"Webhook endpoint: {endpoint}")

        # Check if webhook handling is configured
        try:
            from payments.views import SumUpWebhookView
            self.print_success("SumUp webhook view is available")
        except ImportError:
            self.print_warning("SumUp webhook view not found - may need to be created")

        return webhook_endpoints

    def generate_test_summary(self):
        """Generate a comprehensive testing summary."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO("🧪 SANDBOX TESTING GUIDE"))
        self.stdout.write("="*60)

        # Test scenarios
        scenarios = [
            "1. 🔗 Connected Artist Payment Flow",
            "   - Login as test_artist_1 (connected)",
            "   - Customer purchases tickets",
            "   - Payment routes to artist's sandbox account",
            "   - Platform fee is calculated and tracked",
            "",
            "2. ❌ Non-Connected Artist Payment Flow",
            "   - Login as test_artist_2 (not connected)",
            "   - Customer purchases tickets",
            "   - Payment routes to platform account",
            "   - Full amount collected for later payout",
            "",
            "3. 💰 Listing Fee Testing",
            "   - Connected artist creates new event",
            "   - Listing fee charged to platform account",
            "   - Fee amount tracked in database",
            "",
            "4. 📧 Ticket Generation & Delivery",
            "   - Complete purchase flow",
            "   - Verify PDF ticket generation",
            "   - Check email delivery to customer",
            "   - Validate QR code functionality",
            "",
            "5. 🔄 Webhook & Transaction Logging",
            "   - Process test payments",
            "   - Verify webhook reception",
            "   - Check transaction logging",
            "   - Validate status updates"
        ]

        for scenario in scenarios:
            self.stdout.write(scenario)

        # Test URLs
        self.print_info("\nTest URLs:")
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        test_urls = [
            f"{site_url}/accounts/dashboard/",
            f"{site_url}/events/",
            f"{site_url}/accounts/sumup/connect/",
            f"{site_url}/admin/",
            f"{site_url}/payments/"
        ]

        for url in test_urls:
            self.stdout.write(f"  {url}")

        # Sandbox tools
        self.print_info("\nSandbox Tools:")
        self.stdout.write("  📱 SumUp Developer Dashboard: https://developer.sumup.com/")
        self.stdout.write("  🧪 Test Cards: Use SumUp sandbox test card numbers")
        self.stdout.write("  📊 Transaction Logs: Check Django admin and server logs")
        self.stdout.write("  🔍 API Testing: Use provided test tokens")

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(self.style.HTTP_INFO("🧪 SumUp Sandbox Environment Setup"))
        self.stdout.write(f"Timestamp: {timezone.now()}")

        success = True

        # Check environment variables
        if not self.check_environment_variables():
            success = False

        # Show configuration if requested
        if options.get('show_config'):
            self.show_sandbox_configuration()

        # Verify API connection if requested
        if options.get('verify_connection'):
            if not self.verify_api_connection():
                success = False

        # Create test tokens if requested
        if options.get('create_test_tokens'):
            self.create_test_oauth_tokens()

        # Always validate webhooks and test payment creation
        self.validate_webhook_endpoints()
        self.test_payment_creation()

        # Generate testing guide
        self.generate_test_summary()

        if success:
            self.print_success("Sandbox environment setup completed!")
        else:
            self.print_error("Sandbox setup completed with warnings - check configuration")

        return success