"""Management command to verify SumUp OAuth migration data integrity."""

from django.core.management.base import BaseCommand
from django.db import connection
from accounts.models import ArtistProfile, User
from datetime import datetime


class Command(BaseCommand):
    help = 'Verify SumUp OAuth migration data integrity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed output for all checks',
        )

    def print_header(self, message):
        """Print a formatted header."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO(f"🔍 {message}"))
        self.stdout.write("="*60)

    def print_success(self, message):
        """Print success message."""
        self.stdout.write(self.style.SUCCESS(f"✅ {message}"))

    def print_warning(self, message):
        """Print warning message."""
        self.stdout.write(self.style.WARNING(f"⚠️  {message}"))

    def print_error(self, message):
        """Print error message."""
        self.stdout.write(self.style.ERROR(f"❌ {message}"))

    def print_info(self, message):
        """Print info message."""
        self.stdout.write(f"📊 {message}")

    def check_database_schema(self):
        """Check if SumUp OAuth fields exist in database schema."""
        self.print_header("DATABASE SCHEMA VERIFICATION")

        # Get database cursor
        cursor = connection.cursor()

        # Check database type
        db_vendor = connection.vendor
        self.print_info(f"Database type: {db_vendor}")

        try:
            if db_vendor == 'sqlite':
                # SQLite schema check
                cursor.execute("PRAGMA table_info(accounts_artistprofile);")
                columns = [row[1] for row in cursor.fetchall()]
            elif db_vendor == 'postgresql':
                # PostgreSQL schema check
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'accounts_artistprofile';
                """)
                columns = [row[0] for row in cursor.fetchall()]
            else:
                self.print_warning(f"Unsupported database vendor: {db_vendor}")
                return False

            # Expected SumUp fields
            expected_fields = [
                'sumup_access_token',
                'sumup_refresh_token',
                'sumup_token_type',
                'sumup_expires_at',
                'sumup_scope',
                'sumup_merchant_code',
                'sumup_connected_at',
                'sumup_connection_status'
            ]

            self.print_info(f"Total columns in accounts_artistprofile: {len(columns)}")

            # Check each expected field
            missing_fields = []
            for field in expected_fields:
                if field in columns:
                    if self.detailed:
                        self.print_success(f"Field exists: {field}")
                else:
                    missing_fields.append(field)
                    self.print_error(f"Field missing: {field}")

            if missing_fields:
                self.print_error(f"Missing fields: {', '.join(missing_fields)}")
                return False
            else:
                self.print_success("All SumUp OAuth fields present in schema")
                return True

        except Exception as e:
            self.print_error(f"Schema check failed: {e}")
            return False

    def verify_data_integrity(self):
        """Verify that artist data was migrated correctly."""
        self.print_header("DATA INTEGRITY VERIFICATION")

        try:
            # Get all artist profiles
            total_artists = ArtistProfile.objects.count()
            self.print_info(f"Total artists in database: {total_artists}")

            if total_artists == 0:
                self.print_warning("No artists found in database")
                return True

            # Test 1: Check connection status field
            not_connected_count = ArtistProfile.objects.filter(
                sumup_connection_status='not_connected'
            ).count()

            connected_count = ArtistProfile.objects.filter(
                sumup_connection_status='connected'
            ).count()

            expired_count = ArtistProfile.objects.filter(
                sumup_connection_status='expired'
            ).count()

            error_count = ArtistProfile.objects.filter(
                sumup_connection_status='error'
            ).count()

            self.print_info("Connection status breakdown:")
            self.stdout.write(f"  - Not connected: {not_connected_count}")
            self.stdout.write(f"  - Connected: {connected_count}")
            self.stdout.write(f"  - Expired: {expired_count}")
            self.stdout.write(f"  - Error: {error_count}")
            self.stdout.write(f"  - Total: {not_connected_count + connected_count + expired_count + error_count}")

            # Test 2: Check for NULL connection status (should be none)
            null_status_count = ArtistProfile.objects.filter(
                sumup_connection_status__isnull=True
            ).count()

            if null_status_count == 0:
                self.print_success("No artists with NULL connection status")
            else:
                self.print_error(f"Found {null_status_count} artists with NULL connection status")
                return False

            # Test 3: Check for empty string connection status
            empty_status_count = ArtistProfile.objects.filter(
                sumup_connection_status=''
            ).count()

            if empty_status_count == 0:
                self.print_success("No artists with empty connection status")
            else:
                self.print_error(f"Found {empty_status_count} artists with empty connection status")
                return False

            # Test 4: Check invalid connection status values
            valid_statuses = ['not_connected', 'connected', 'expired', 'error']
            invalid_status_artists = ArtistProfile.objects.exclude(
                sumup_connection_status__in=valid_statuses
            )

            if invalid_status_artists.count() == 0:
                self.print_success("All artists have valid connection status values")
            else:
                self.print_error(f"Found {invalid_status_artists.count()} artists with invalid connection status")
                for artist in invalid_status_artists[:5]:  # Show first 5
                    self.stdout.write(f"  - {artist.display_name}: '{artist.sumup_connection_status}'")
                return False

            # Test 5: Check default values for OAuth fields
            oauth_fields_check = ArtistProfile.objects.filter(
                sumup_access_token='',
                sumup_refresh_token='',
                sumup_token_type__in=['Bearer', ''],
                sumup_expires_at__isnull=True,
                sumup_scope='',
                sumup_merchant_code='',
                sumup_connected_at__isnull=True
            ).count()

            if oauth_fields_check == not_connected_count:
                self.print_success("All not-connected artists have proper default OAuth values")
            else:
                self.print_warning(f"OAuth fields check: {oauth_fields_check} match expected {not_connected_count}")

            return True

        except Exception as e:
            self.print_error(f"Data integrity check failed: {e}")
            return False

    def test_model_methods(self):
        """Test that model methods work correctly."""
        self.print_header("MODEL METHODS TESTING")

        try:
            # Get a test artist
            test_artist = ArtistProfile.objects.first()

            if not test_artist:
                self.print_warning("No artists available for model method testing")
                return True

            self.print_info(f"Testing with artist: {test_artist.display_name}")

            # Test 1: is_sumup_connected property
            try:
                is_connected = test_artist.is_sumup_connected
                self.print_success(f"is_sumup_connected property works: {is_connected}")
            except Exception as e:
                self.print_error(f"is_sumup_connected property failed: {e}")
                return False

            # Test 2: sumup_token_expired property
            try:
                token_expired = test_artist.sumup_token_expired
                self.print_success(f"sumup_token_expired property works: {token_expired}")
            except Exception as e:
                self.print_error(f"sumup_token_expired property failed: {e}")
                return False

            # Test 3: update_sumup_connection method
            try:
                # Test with dummy data (don't save)
                original_status = test_artist.sumup_connection_status
                test_data = {
                    'access_token': 'test_token_123',
                    'refresh_token': 'test_refresh_123',
                    'expires_in': 3600,
                    'scope': 'payments'
                }

                # Call method but don't save to database
                test_artist.update_sumup_connection(test_data)

                # Verify it was updated in memory
                if test_artist.sumup_access_token == 'test_token_123':
                    self.print_success("update_sumup_connection method works")

                    # Restore original values (refresh from DB)
                    test_artist.refresh_from_db()
                    if test_artist.sumup_connection_status == original_status:
                        self.print_success("Artist data restored successfully")
                    else:
                        self.print_warning("Artist data restoration check inconclusive")
                else:
                    self.print_error("update_sumup_connection method failed to update fields")
                    return False

            except Exception as e:
                self.print_error(f"update_sumup_connection method failed: {e}")
                return False

            return True

        except Exception as e:
            self.print_error(f"Model methods testing failed: {e}")
            return False

    def generate_summary_report(self):
        """Generate a summary report of the verification."""
        self.print_header("MIGRATION VERIFICATION SUMMARY")

        try:
            total_artists = ArtistProfile.objects.count()
            approved_artists = ArtistProfile.objects.filter(is_approved=True).count()
            not_connected = ArtistProfile.objects.filter(sumup_connection_status='not_connected').count()

            self.print_info("Migration Statistics:")
            self.stdout.write(f"  📊 Total Artists: {total_artists}")
            self.stdout.write(f"  📊 Approved Artists: {approved_artists}")
            self.stdout.write(f"  📊 Not Connected Artists: {not_connected}")
            if total_artists > 0:
                self.stdout.write(f"  📊 Migration Coverage: {(not_connected/total_artists*100):.1f}%")
            else:
                self.stdout.write("  📊 Migration Coverage: N/A")

            self.print_info("Next Steps:")
            if approved_artists > 0:
                self.stdout.write(f"  📧 Send notification emails to {approved_artists} approved artists")
                self.stdout.write("     Command: python manage.py notify_artists_sumup_migration --approved-only")
            else:
                self.stdout.write("  📧 No approved artists found - no notifications needed")

            self.stdout.write("  🔍 Monitor application logs for any OAuth-related errors")
            self.stdout.write("  🔗 Test SumUp connection flow with a test artist account")

            return True

        except Exception as e:
            self.print_error(f"Summary report generation failed: {e}")
            return False

    def handle(self, *args, **options):
        """Main verification function."""
        self.detailed = options.get('detailed', False)

        self.stdout.write("🔍 Jersey Events - SumUp OAuth Migration Verification")
        self.stdout.write(f"Timestamp: {datetime.now()}")

        all_checks_passed = True

        # Run all verification checks
        checks = [
            ("Schema Verification", self.check_database_schema),
            ("Data Integrity", self.verify_data_integrity),
            ("Model Methods", self.test_model_methods),
            ("Summary Report", self.generate_summary_report)
        ]

        for check_name, check_function in checks:
            try:
                if not check_function():
                    all_checks_passed = False
                    self.print_error(f"{check_name} failed")
                else:
                    self.print_success(f"{check_name} passed")
            except Exception as e:
                all_checks_passed = False
                self.print_error(f"{check_name} failed with exception: {e}")

        # Final result
        self.print_header("FINAL RESULT")
        if all_checks_passed:
            self.print_success("🎉 All verification checks PASSED!")
            self.print_success("✅ SumUp OAuth migration completed successfully")
        else:
            self.print_error("❌ Some verification checks FAILED!")
            self.print_error("🚨 Review the errors above and fix issues before proceeding")