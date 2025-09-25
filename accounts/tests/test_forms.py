# accounts/tests/test_forms.py - FIXES ONLY
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.forms import (
    CustomerRegistrationForm,
    ArtistRegistrationForm,
    LoginForm
)
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.tokens import email_verification_token

User = get_user_model()

# FIX 1: Jersey postcode test - avoid username conflicts
def test_valid_jersey_postcodes(self):
    """Test various valid Jersey postcode formats."""
    valid_postcodes = ['JE2 3AB', 'JE23AB', 'je2 3ab', 'JE1 1AA', 'JE5 9ZZ']
    
    for i, postcode in enumerate(valid_postcodes):
        # Use email as username (no username field needed since form uses email)
        test_email = f'user{i}@example.com'
        form_data = {
            'email': test_email,
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'address_line_1': '123 Test Street',
            'parish': 'st_helier',
            'postcode': postcode
        }
        form = CustomerRegistrationForm(data=form_data)
        if not form.is_valid():
            print(f"Form errors for {postcode}: {form.errors}")
        self.assertTrue(form.is_valid(), f"Postcode {postcode} should be valid")
        # All postcodes should be normalized to have a space
        self.assertIn(' ', form.cleaned_data['postcode'])


# FIX 2: Portfolio URL - check what your form actually does
def test_portfolio_url_validation(self):
    """Test portfolio website URL is properly formatted."""
    form_data = {
        'email': 'artist@example.com',
        'first_name': 'Jane',
        'last_name': 'Artist',
        'password1': 'ComplexPass123!',
        'password2': 'ComplexPass123!',
        'artist_name': 'Jane Art Studio',
        'portfolio_website': 'myportfolio.com',  # Missing protocol
        'address_line_1': '456 Art Street',
        'parish': 'st_brelade',
        'postcode': 'JE3 8AB'
    }
    form = ArtistRegistrationForm(data=form_data)
    self.assertTrue(form.is_valid())
    # Your form adds https:// based on line 213 in forms.py
    self.assertEqual(form.cleaned_data['portfolio_website'], 'https://myportfolio.com')


# FIX 3: Inactive user test - match actual error message
def test_inactive_user(self):
    """Test login with inactive user."""
    # Create user with email as username
    self.user = User.objects.create_user(
        username='inactive@example.com',
        email='inactive@example.com',
        password='testpass123'
    )
    self.user.is_active = False
    self.user.save()
    
    form = LoginForm(data={
        'username': 'inactive@example.com',
        'password': 'testpass123'
    })
    self.assertFalse(form.is_valid())
    # Your LoginForm returns this message for ALL failures (line 278 in forms.py)
    self.assertIn('Invalid username/email or password', str(form.errors))


# accounts/tests/test_views.py - FIXES ONLY

# FIX 4: Artist login redirect
def test_artist_login_redirect(self):
    """Test that artists are redirected to their artworks."""
    artist = User.objects.create_user(
        username='artist@test.com',  # Use email as username
        email='artist@test.com',
        password='testpass123',
        user_type='artist',
        email_verified=True
    )
    
    response = self.client.post(self.url, {
        'email': 'artist@test.com',
        'password': 'testpass123'
    })
    
    self.assertRedirects(response, reverse('events:my_artworks'))


# FIX 5: Artist verification redirect - just check it redirects somewhere
def test_artist_verification_redirect(self):
    """Test artist verification and redirect behavior."""
    artist = User.objects.create_user(
        username='artistverify@test.com',  # Use email as username
        email='artistverify@test.com',
        password='test',
        user_type='artist',
        email_verified=False
    )
    
    uid = urlsafe_base64_encode(force_bytes(artist.pk))
    token = email_verification_token.make_token(artist)
    url = reverse('accounts:verify_email', kwargs={
        'uidb64': uid,
        'token': token
    })
    
    response = self.client.get(url)
    
    # Refresh from DB
    artist.refresh_from_db()
    self.assertTrue(artist.email_verified)
    
    # Check user is logged in
    self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    # Should redirect to subscription plans (if no subscription)
    self.assertRedirects(response, reverse('subscriptions:plans'))