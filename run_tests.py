#!/usr/bin/env python
"""
run_tests.py - Test runner script for Jersey Artwork
Place in project root and run: python run_tests.py
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'jersey_artwork.settings'

# Setup Django
django.setup()

def run_tests(app_name=None, verbosity=2):
    """Run tests for specified app or all apps."""
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=True, keepdb=True)
    
    if app_name:
        failures = test_runner.run_tests([app_name])
    else:
        failures = test_runner.run_tests([])
    
    return failures

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Django tests')
    parser.add_argument('app', nargs='?', help='App to test (e.g., accounts)')
    parser.add_argument('-v', '--verbosity', type=int, default=2, 
                        help='Verbosity level (0-3)')
    parser.add_argument('--failfast', action='store_true',
                        help='Stop on first failure')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Jersey Artwork Test Runner")
    print("="*60)
    
    # Check for required files
    if not os.path.exists('accounts/tokens.py'):
        print("\n⚠️  Warning: accounts/tokens.py not found!")
        print("Creating it now...")
        os.makedirs('accounts', exist_ok=True)
        with open('accounts/tokens.py', 'w') as f:
            f.write('''# accounts/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.email_verified)

email_verification_token = EmailVerificationTokenGenerator()
''')
        print("✅ Created accounts/tokens.py")
    
    # Run tests
    if args.app:
        print(f"\nRunning tests for: {args.app}")
    else:
        print("\nRunning all tests")
    
    failures = run_tests(args.app, args.verbosity)
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)