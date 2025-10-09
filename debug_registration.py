#!/usr/bin/env python
"""Debug script to test registration form validation and user creation"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import transaction
from accounts.forms import CustomerRegistrationForm, ArtistRegistrationForm
from accounts.models import User, CustomerProfile, ArtistProfile

def test_customer_registration():
    """Test customer registration form validation"""
    print("\n" + "="*60)
    print("TESTING CUSTOMER REGISTRATION FORM")
    print("="*60)

    # Test data
    test_data = {
        'email': 'testcustomer@example.com',
        'first_name': 'Test',
        'last_name': 'Customer',
        'password1': 'TestPassword123!',
        'password2': 'TestPassword123!',
        'phone_number': '+44 7700 900123',
        'address_line_1': '123 Test Street',
        'address_line_2': 'Test Area',
        'parish': 'st_helier',
        'postcode': 'JE2 3AB'
    }

    print(f"\n📋 Test data:")
    for key, value in test_data.items():
        if 'password' not in key:
            print(f"  {key}: {value}")

    # Create form
    form = CustomerRegistrationForm(data=test_data)

    print(f"\n🔍 Form class: {form.__class__.__name__}")
    print(f"🔍 Form bound: {form.is_bound}")

    # Validate form
    is_valid = form.is_valid()
    print(f"\n✅ Form is valid: {is_valid}")

    if not is_valid:
        print(f"\n❌ Form errors:")
        print(f"  All errors: {form.errors}")
        print(f"  Non-field errors: {form.non_field_errors()}")
        for field_name, errors in form.errors.items():
            print(f"  Field '{field_name}': {errors}")
    else:
        print(f"\n✅ Form validated successfully!")
        print(f"📋 Cleaned data:")
        for key, value in form.cleaned_data.items():
            if 'password' not in key:
                print(f"  {key}: {value}")

    # Try to save (in a transaction we'll rollback)
    if is_valid:
        try:
            with transaction.atomic():
                print(f"\n🔍 Attempting to save user...")
                user = form.save(commit=False)
                print(f"✅ User object created (not saved)")
                print(f"  Email: {user.email}")
                print(f"  Name: {user.get_full_name()}")
                print(f"  User type: {user.user_type}")

                # Actually save to test full process
                user.save()
                print(f"✅ User saved to database")
                print(f"  User ID: {user.id}")

                # Check if profile creation works
                profile = CustomerProfile.objects.filter(user=user).first()
                if profile:
                    print(f"✅ Customer profile created")
                    print(f"  Address: {profile.address_line_1}")
                    print(f"  Parish: {profile.parish}")
                else:
                    print(f"❌ Customer profile NOT created")

                # Rollback to keep database clean
                raise Exception("Rolling back test transaction")
        except Exception as e:
            if "Rolling back" not in str(e):
                print(f"❌ Save failed: {e}")
                import traceback
                traceback.print_exc()

def test_organiser_registration():
    """Test organiser/artist registration form validation"""
    print("\n" + "="*60)
    print("TESTING ORGANISER REGISTRATION FORM")
    print("="*60)

    # Test data
    test_data = {
        'email': 'testorganiser@example.com',
        'first_name': 'Test',
        'last_name': 'Organiser',
        'password1': 'TestPassword123!',
        'password2': 'TestPassword123!',
        'phone_number': '+44 7700 900456',
        'address_line_1': '456 Artist Street',
        'parish': 'st_brelade',
        'postcode': 'JE3 4CD',
        'artist_name': 'Test Artist Studio',
        'business_name': 'Test Business Ltd',
        'bio': 'Test bio for artist',
        'portfolio_website': 'https://testartist.com'
    }

    print(f"\n📋 Test data:")
    for key, value in test_data.items():
        if 'password' not in key:
            print(f"  {key}: {value}")

    # Create form
    form = ArtistRegistrationForm(data=test_data)

    print(f"\n🔍 Form class: {form.__class__.__name__}")
    print(f"🔍 Form bound: {form.is_bound}")

    # Validate form
    is_valid = form.is_valid()
    print(f"\n✅ Form is valid: {is_valid}")

    if not is_valid:
        print(f"\n❌ Form errors:")
        print(f"  All errors: {form.errors}")
        print(f"  Non-field errors: {form.non_field_errors()}")
        for field_name, errors in form.errors.items():
            print(f"  Field '{field_name}': {errors}")
    else:
        print(f"\n✅ Form validated successfully!")
        print(f"📋 Cleaned data:")
        for key, value in form.cleaned_data.items():
            if 'password' not in key:
                print(f"  {key}: {value}")

    # Try to save (in a transaction we'll rollback)
    if is_valid:
        try:
            with transaction.atomic():
                print(f"\n🔍 Attempting to save user...")
                user = form.save(commit=False)
                print(f"✅ User object created (not saved)")
                print(f"  Email: {user.email}")
                print(f"  Name: {user.get_full_name()}")
                print(f"  User type: {user.user_type}")

                # Actually save to test full process
                user.save()
                print(f"✅ User saved to database")
                print(f"  User ID: {user.id}")

                # Check if profile creation works
                profile = ArtistProfile.objects.filter(user=user).first()
                if profile:
                    print(f"✅ Artist profile created")
                    print(f"  Display name: {profile.display_name}")
                    print(f"  Bio: {profile.bio[:50]}...")
                else:
                    print(f"❌ Artist profile NOT created")

                # Rollback to keep database clean
                raise Exception("Rolling back test transaction")
        except Exception as e:
            if "Rolling back" not in str(e):
                print(f"❌ Save failed: {e}")
                import traceback
                traceback.print_exc()

def check_existing_users():
    """Check for any existing test users"""
    print("\n" + "="*60)
    print("CHECKING EXISTING TEST USERS")
    print("="*60)

    test_emails = ['testcustomer@example.com', 'testorganiser@example.com']

    for email in test_emails:
        user = User.objects.filter(email=email).first()
        if user:
            print(f"⚠️  User exists: {email}")
            print(f"    ID: {user.id}, Type: {user.user_type}, Verified: {user.email_verified}")
        else:
            print(f"✅ No user with email: {email}")

def test_form_field_validation():
    """Test individual field validation"""
    print("\n" + "="*60)
    print("TESTING FIELD VALIDATION")
    print("="*60)

    # Test invalid postcode
    print("\n🔍 Testing invalid postcode:")
    form = CustomerRegistrationForm(data={
        'postcode': 'INVALID'
    })
    form.is_valid()
    if 'postcode' in form.errors:
        print(f"  ✅ Postcode validation works: {form.errors['postcode']}")
    else:
        print(f"  ❌ Postcode validation failed")

    # Test duplicate email
    print("\n🔍 Testing duplicate email:")
    # First check if admin@example.com exists
    admin_user = User.objects.filter(email='admin@example.com').first()
    if admin_user:
        form = CustomerRegistrationForm(data={
            'email': 'admin@example.com'
        })
        form.is_valid()
        if 'email' in form.errors:
            print(f"  ✅ Email duplication check works: {form.errors['email']}")
        else:
            print(f"  ❌ Email duplication check failed")
    else:
        print(f"  ⚠️  No admin user to test duplication with")

    # Test password mismatch
    print("\n🔍 Testing password mismatch:")
    form = CustomerRegistrationForm(data={
        'password1': 'Password123!',
        'password2': 'Different123!'
    })
    form.is_valid()
    if 'password2' in form.errors:
        print(f"  ✅ Password mismatch check works: {form.errors['password2']}")
    else:
        print(f"  ❌ Password mismatch check failed")

if __name__ == '__main__':
    print("="*60)
    print("REGISTRATION FORM DEBUG SCRIPT")
    print("="*60)

    # Check existing users first
    check_existing_users()

    # Test field validation
    test_form_field_validation()

    # Test customer registration
    test_customer_registration()

    # Test organiser registration
    test_organiser_registration()

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)