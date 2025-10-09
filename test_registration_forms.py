#!/usr/bin/env python
"""
Test registration forms independently to identify validation issues
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/josegalan/Documents/jersey_music')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from accounts.forms import CustomerRegistrationForm, ArtistRegistrationForm
from accounts.models import User

def test_customer_registration_form():
    """Test customer registration form with minimal data"""
    print("🧪 TESTING CUSTOMER REGISTRATION FORM")
    print("=" * 50)

    # Test 1: Valid minimal data
    print("\n1. Testing with valid minimal data:")
    valid_data = {
        'email': 'test.customer@formtest.com',
        'password1': 'TestPass123!',
        'password2': 'TestPass123!',
        'first_name': 'Test',
        'last_name': 'Customer',
        'address_line_1': '123 Test Street',
        'parish': 'st_helier',
        'postcode': 'JE2 3AB'
    }

    form = CustomerRegistrationForm(data=valid_data)
    print(f"📋 Form data: {valid_data}")

    try:
        is_valid = form.is_valid()
        print(f"✅ Form validation result: {is_valid}")

        if not is_valid:
            print(f"❌ Validation errors: {form.errors}")
            for field, errors in form.errors.items():
                print(f"   - {field}: {errors}")
        else:
            print("✅ Form is valid!")

            # Test saving
            try:
                user = form.save()
                print(f"✅ User saved successfully!")
                print(f"   - Email: {user.email}")
                print(f"   - Type: {user.user_type}")
                print(f"   - Profile created: {hasattr(user, 'customerprofile')}")
            except Exception as e:
                print(f"❌ User save failed: {e}")

    except Exception as e:
        print(f"❌ Form validation exception: {e}")

    # Test 2: Missing required fields
    print("\n2. Testing with missing required fields:")
    incomplete_data = {
        'email': 'incomplete@test.com',
        'password1': 'TestPass123!',
        'password2': 'TestPass123!',
        # Missing name and address fields
    }

    incomplete_form = CustomerRegistrationForm(data=incomplete_data)
    is_valid = incomplete_form.is_valid()
    print(f"📋 Incomplete form valid: {is_valid}")
    if not is_valid:
        print(f"❌ Expected errors: {incomplete_form.errors}")

    # Test 3: Invalid email
    print("\n3. Testing with invalid email:")
    invalid_email_data = valid_data.copy()
    invalid_email_data['email'] = 'invalid-email'

    invalid_form = CustomerRegistrationForm(data=invalid_email_data)
    is_valid = invalid_form.is_valid()
    print(f"📋 Invalid email form valid: {is_valid}")
    if not is_valid:
        print(f"❌ Expected errors: {invalid_form.errors}")

def test_artist_registration_form():
    """Test artist registration form with minimal data"""
    print("\n🧪 TESTING ARTIST REGISTRATION FORM")
    print("=" * 50)

    # Test with valid data
    print("\n1. Testing with valid minimal data:")
    valid_data = {
        'email': 'test.artist@formtest.com',
        'password1': 'TestPass123!',
        'password2': 'TestPass123!',
        'first_name': 'Test',
        'last_name': 'Artist',
        'address_line_1': '456 Artist Lane',
        'parish': 'st_brelade',
        'postcode': 'JE3 8PQ',
        'artist_name': 'Test Artist Studio',
        'bio': 'Test artist biography',
        'portfolio_website': 'https://testartist.com'
    }

    form = ArtistRegistrationForm(data=valid_data)
    print(f"📋 Form data: {valid_data}")

    try:
        is_valid = form.is_valid()
        print(f"✅ Form validation result: {is_valid}")

        if not is_valid:
            print(f"❌ Validation errors: {form.errors}")
            for field, errors in form.errors.items():
                print(f"   - {field}: {errors}")
        else:
            print("✅ Form is valid!")

            # Test saving
            try:
                user = form.save()
                print(f"✅ User saved successfully!")
                print(f"   - Email: {user.email}")
                print(f"   - Type: {user.user_type}")
                print(f"   - Profile created: {hasattr(user, 'artistprofile')}")
                if hasattr(user, 'artistprofile'):
                    print(f"   - Display name: {user.artistprofile.display_name}")
            except Exception as e:
                print(f"❌ User save failed: {e}")

    except Exception as e:
        print(f"❌ Form validation exception: {e}")

def test_form_field_requirements():
    """Test what fields are actually required"""
    print("\n🧪 TESTING FORM FIELD REQUIREMENTS")
    print("=" * 50)

    # Check CustomerRegistrationForm fields
    print("\n1. Customer Registration Form Fields:")
    customer_form = CustomerRegistrationForm()
    for field_name, field in customer_form.fields.items():
        required = field.required
        print(f"   - {field_name}: {'REQUIRED' if required else 'optional'}")

    # Check ArtistRegistrationForm fields
    print("\n2. Artist Registration Form Fields:")
    artist_form = ArtistRegistrationForm()
    for field_name, field in artist_form.fields.items():
        required = field.required
        print(f"   - {field_name}: {'REQUIRED' if required else 'optional'}")

def test_duplicate_email_handling():
    """Test duplicate email handling"""
    print("\n🧪 TESTING DUPLICATE EMAIL HANDLING")
    print("=" * 50)

    # Create a user first
    test_email = 'duplicate@test.com'

    # Check if user already exists
    existing_user = User.objects.filter(email=test_email).first()
    if existing_user:
        print(f"🔍 Test user already exists: {test_email}")
    else:
        # Create test user
        User.objects.create_user(email=test_email, password='test123')
        print(f"🔍 Created test user: {test_email}")

    # Try to register with same email
    duplicate_data = {
        'email': test_email,
        'password1': 'TestPass123!',
        'password2': 'TestPass123!',
        'first_name': 'Duplicate',
        'last_name': 'Test',
        'address_line_1': '123 Duplicate Street',
        'parish': 'st_helier',
        'postcode': 'JE2 3AB'
    }

    form = CustomerRegistrationForm(data=duplicate_data)
    is_valid = form.is_valid()
    print(f"📋 Duplicate email form valid: {is_valid}")

    if not is_valid:
        print(f"✅ Duplicate email correctly rejected: {form.errors}")
    else:
        print(f"❌ Duplicate email incorrectly accepted!")

def main():
    """Run all form tests"""
    print("🔍 COMPREHENSIVE REGISTRATION FORM TESTING")
    print("=" * 60)

    test_form_field_requirements()
    test_customer_registration_form()
    test_artist_registration_form()
    test_duplicate_email_handling()

    print("\n" + "=" * 60)
    print("🏁 FORM TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()