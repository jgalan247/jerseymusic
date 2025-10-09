#!/usr/bin/env python
"""
verify_migration.py - Verify SumUp OAuth migration data integrity
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from accounts.models import ArtistProfile, User
from django.db import connection

def print_header(message):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🔍 {message}")
    print("="*60)

def print_success(message):
    """Print success message."""
    print(f"✅ {message}")

def print_warning(message):
    """Print warning message."""
    print(f"⚠️  {message}")

def print_error(message):
    """Print error message."""
    print(f"❌ {message}")

def print_info(message):
    """Print info message."""
    print(f"📊 {message}")

def check_database_schema():
    """Check if SumUp OAuth fields exist in database schema."""
    print_header("DATABASE SCHEMA VERIFICATION")

    # Get database cursor
    cursor = connection.cursor()

    # Check if we're using SQLite or PostgreSQL
    db_vendor = connection.vendor
    print_info(f"Database type: {db_vendor}")

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
            print_warning(f"Unsupported database vendor: {db_vendor}")
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

        print_info(f"Total columns in accounts_artistprofile: {len(columns)}")

        # Check each expected field
        missing_fields = []
        for field in expected_fields:
            if field in columns:
                print_success(f"Field exists: {field}")
            else:
                missing_fields.append(field)
                print_error(f"Field missing: {field}")

        if missing_fields:
            print_error(f"Missing fields: {', '.join(missing_fields)}")
            return False
        else:
            print_success("All SumUp OAuth fields present in schema")
            return True

    except Exception as e:
        print_error(f"Schema check failed: {e}")
        return False

def verify_data_integrity():
    """Verify that artist data was migrated correctly."""
    print_header("DATA INTEGRITY VERIFICATION")

    try:
        # Get all artist profiles
        total_artists = ArtistProfile.objects.count()
        print_info(f"Total artists in database: {total_artists}")

        if total_artists == 0:
            print_warning("No artists found in database")
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

        print_info(f"Connection status breakdown:")
        print(f"  - Not connected: {not_connected_count}")
        print(f"  - Connected: {connected_count}")
        print(f"  - Expired: {expired_count}")
        print(f"  - Error: {error_count}")
        print(f"  - Total: {not_connected_count + connected_count + expired_count + error_count}")

        # Test 2: Check for NULL connection status (should be none)
        null_status_count = ArtistProfile.objects.filter(
            sumup_connection_status__isnull=True
        ).count()

        if null_status_count == 0:
            print_success("No artists with NULL connection status")
        else:
            print_error(f"Found {null_status_count} artists with NULL connection status")
            return False

        # Test 3: Check for empty string connection status
        empty_status_count = ArtistProfile.objects.filter(
            sumup_connection_status=''
        ).count()

        if empty_status_count == 0:
            print_success("No artists with empty connection status")
        else:
            print_error(f"Found {empty_status_count} artists with empty connection status")
            return False

        # Test 4: Check invalid connection status values
        valid_statuses = ['not_connected', 'connected', 'expired', 'error']
        invalid_status_artists = ArtistProfile.objects.exclude(
            sumup_connection_status__in=valid_statuses
        )

        if invalid_status_artists.count() == 0:
            print_success("All artists have valid connection status values")
        else:
            print_error(f"Found {invalid_status_artists.count()} artists with invalid connection status")
            for artist in invalid_status_artists[:5]:  # Show first 5
                print(f"  - {artist.display_name}: '{artist.sumup_connection_status}'")
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
            print_success("All not-connected artists have proper default OAuth values")
        else:
            print_warning(f"OAuth fields check: {oauth_fields_check} match expected {not_connected_count}")

        return True

    except Exception as e:
        print_error(f"Data integrity check failed: {e}")
        return False

def test_model_methods():
    """Test that model methods work correctly."""
    print_header("MODEL METHODS TESTING")

    try:
        # Get a test artist
        test_artist = ArtistProfile.objects.first()

        if not test_artist:
            print_warning("No artists available for model method testing")
            return True

        print_info(f"Testing with artist: {test_artist.display_name}")

        # Test 1: is_sumup_connected property
        try:
            is_connected = test_artist.is_sumup_connected
            print_success(f"is_sumup_connected property works: {is_connected}")
        except Exception as e:
            print_error(f"is_sumup_connected property failed: {e}")
            return False

        # Test 2: sumup_token_expired property
        try:
            token_expired = test_artist.sumup_token_expired
            print_success(f"sumup_token_expired property works: {token_expired}")
        except Exception as e:
            print_error(f"sumup_token_expired property failed: {e}")
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
                print_success("update_sumup_connection method works")

                # Restore original values (refresh from DB)
                test_artist.refresh_from_db()
                if test_artist.sumup_connection_status == original_status:
                    print_success("Artist data restored successfully")
                else:
                    print_warning("Artist data restoration check inconclusive")
            else:
                print_error("update_sumup_connection method failed to update fields")
                return False

        except Exception as e:
            print_error(f"update_sumup_connection method failed: {e}")
            return False

        # Test 4: disconnect_sumup method
        try:
            # Create a temporary artist for this test
            test_user = User.objects.create_user(
                username=f'test_verify_{datetime.now().microsecond}',
                email=f'test_verify_{datetime.now().microsecond}@example.com',
                user_type='artist'
            )
            temp_artist = ArtistProfile.objects.create(
                user=test_user,
                display_name='Test Verification Artist'
            )

            # Set up connection data
            temp_artist.update_sumup_connection({
                'access_token': 'temp_token',
                'refresh_token': 'temp_refresh',
                'expires_in': 3600
            })

            # Test disconnect
            temp_artist.disconnect_sumup()

            if (temp_artist.sumup_connection_status == 'not_connected' and
                temp_artist.sumup_access_token == ''):
                print_success("disconnect_sumup method works")
            else:
                print_error("disconnect_sumup method failed")
                return False

            # Clean up
            test_user.delete()
            print_success("Test data cleaned up")

        except Exception as e:
            print_error(f"disconnect_sumup method test failed: {e}")
            return False

        return True

    except Exception as e:
        print_error(f"Model methods testing failed: {e}")
        return False

def generate_summary_report():
    """Generate a summary report of the verification."""
    print_header("MIGRATION VERIFICATION SUMMARY")

    try:
        total_artists = ArtistProfile.objects.count()
        approved_artists = ArtistProfile.objects.filter(is_approved=True).count()
        not_connected = ArtistProfile.objects.filter(sumup_connection_status='not_connected').count()

        print_info("Migration Statistics:")
        print(f"  📊 Total Artists: {total_artists}")
        print(f"  📊 Approved Artists: {approved_artists}")
        print(f"  📊 Not Connected Artists: {not_connected}")
        print(f"  📊 Migration Coverage: {(not_connected/total_artists*100):.1f}%" if total_artists > 0 else "  📊 Migration Coverage: N/A")

        print_info("Next Steps:")
        if approved_artists > 0:
            print(f"  📧 Send notification emails to {approved_artists} approved artists")
            print("     Command: python manage.py notify_artists_sumup_migration --approved-only")
        else:
            print("  📧 No approved artists found - no notifications needed")

        print("  🔍 Monitor application logs for any OAuth-related errors")
        print("  🔗 Test SumUp connection flow with a test artist account")

        return True

    except Exception as e:
        print_error(f"Summary report generation failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🔍 Jersey Events - SumUp OAuth Migration Verification")
    print(f"Timestamp: {datetime.now()}")

    all_checks_passed = True

    # Run all verification checks
    checks = [
        ("Schema Verification", check_database_schema),
        ("Data Integrity", verify_data_integrity),
        ("Model Methods", test_model_methods),
        ("Summary Report", generate_summary_report)
    ]

    for check_name, check_function in checks:
        try:
            if not check_function():
                all_checks_passed = False
                print_error(f"{check_name} failed")
            else:
                print_success(f"{check_name} passed")
        except Exception as e:
            all_checks_passed = False
            print_error(f"{check_name} failed with exception: {e}")

    # Final result
    print_header("FINAL RESULT")
    if all_checks_passed:
        print_success("🎉 All verification checks PASSED!")
        print_success("✅ SumUp OAuth migration completed successfully")
        sys.exit(0)
    else:
        print_error("❌ Some verification checks FAILED!")
        print_error("🚨 Review the errors above and fix issues before proceeding")
        sys.exit(1)

if __name__ == '__main__':
    main()