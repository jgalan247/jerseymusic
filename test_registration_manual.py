#!/usr/bin/env python
"""Test registration through Django's test client to simulate actual web requests"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.urls import reverse
from accounts.models import User, CustomerProfile, ArtistProfile
import random

def test_customer_registration():
    """Test customer registration via HTTP POST"""
    print("\n" + "="*60)
    print("TESTING CUSTOMER REGISTRATION VIA WEB")
    print("="*60)

    client = Client()

    # First, get the registration page
    url = reverse('accounts:register_customer')
    response = client.get(url)
    print(f"\n✅ GET {url}: {response.status_code}")

    # Generate unique email for this test
    random_suffix = random.randint(1000, 9999)
    test_email = f"testcustomer{random_suffix}@example.com"

    # Submit registration form
    test_data = {
        'email': test_email,
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

    print(f"\n📋 Submitting form with email: {test_email}")
    response = client.post(url, test_data, follow=True)

    print(f"\n✅ POST {url}: {response.status_code}")

    # Check redirect
    if response.redirect_chain:
        print(f"📍 Redirected to: {response.redirect_chain}")

    # Check for messages
    if hasattr(response, 'context') and response.context:
        messages = list(response.context.get('messages', []))
        if messages:
            print(f"\n📬 Messages:")
            for msg in messages:
                print(f"  - [{msg.level_tag}] {msg.message}")

    # Check for form errors
    if hasattr(response, 'context') and response.context and 'form' in response.context:
        form = response.context['form']
        if form.errors:
            print(f"\n❌ Form errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")

    # Check if user was created
    user = User.objects.filter(email=test_email).first()
    if user:
        print(f"\n✅ User created:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.get_full_name()}")
        print(f"  Type: {user.user_type}")
        print(f"  Email verified: {user.email_verified}")

        # Check profile
        profile = CustomerProfile.objects.filter(user=user).first()
        if profile:
            print(f"\n✅ Customer profile created:")
            print(f"  Address: {profile.address_line_1}, {profile.address_line_2}")
            print(f"  Parish: {profile.parish}")
            print(f"  Postcode: {profile.postcode}")
            print(f"  Phone: {profile.phone_number}")
        else:
            print(f"\n❌ No customer profile found")
    else:
        print(f"\n❌ User was NOT created")

    return user

def test_organiser_registration():
    """Test organiser registration via HTTP POST"""
    print("\n" + "="*60)
    print("TESTING ORGANISER REGISTRATION VIA WEB")
    print("="*60)

    client = Client()

    # First, get the registration page
    url = reverse('accounts:register_organiser')
    response = client.get(url)
    print(f"\n✅ GET {url}: {response.status_code}")

    # Generate unique email for this test
    random_suffix = random.randint(1000, 9999)
    test_email = f"testorganiser{random_suffix}@example.com"

    # Submit registration form
    test_data = {
        'email': test_email,
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

    print(f"\n📋 Submitting form with email: {test_email}")
    response = client.post(url, test_data, follow=True)

    print(f"\n✅ POST {url}: {response.status_code}")

    # Check redirect
    if response.redirect_chain:
        print(f"📍 Redirected to: {response.redirect_chain}")

    # Check for messages
    if hasattr(response, 'context') and response.context:
        messages = list(response.context.get('messages', []))
        if messages:
            print(f"\n📬 Messages:")
            for msg in messages:
                print(f"  - [{msg.level_tag}] {msg.message}")

    # Check for form errors
    if hasattr(response, 'context') and response.context and 'form' in response.context:
        form = response.context['form']
        if form.errors:
            print(f"\n❌ Form errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")

    # Check if user was created
    user = User.objects.filter(email=test_email).first()
    if user:
        print(f"\n✅ User created:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.get_full_name()}")
        print(f"  Type: {user.user_type}")
        print(f"  Email verified: {user.email_verified}")

        # Check profile
        profile = ArtistProfile.objects.filter(user=user).first()
        if profile:
            print(f"\n✅ Artist profile created:")
            print(f"  Display name: {profile.display_name}")
            print(f"  Business: {profile.business_name}")
            print(f"  Phone: {profile.phone_number}")
        else:
            print(f"\n❌ No artist profile found")
    else:
        print(f"\n❌ User was NOT created")

    return user

def cleanup_test_users(users_to_clean):
    """Clean up test users"""
    print("\n" + "="*60)
    print("CLEANING UP TEST USERS")
    print("="*60)

    for user in users_to_clean:
        if user:
            print(f"  Deleting user: {user.email}")
            user.delete()

if __name__ == '__main__':
    print("="*60)
    print("MANUAL REGISTRATION TEST")
    print("="*60)

    users_created = []

    try:
        # Test customer registration
        customer = test_customer_registration()
        if customer:
            users_created.append(customer)

        # Test organiser registration
        organiser = test_organiser_registration()
        if organiser:
            users_created.append(organiser)

    finally:
        # Clean up test users
        cleanup_test_users(users_created)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)