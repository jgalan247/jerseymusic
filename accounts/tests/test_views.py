# accounts/tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.models import CustomerProfile, ArtistProfile
from accounts.tokens import email_verification_token
from unittest.mock import patch

User = get_user_model()


class CustomerRegistrationViewTest(TestCase):
    """Test customer registration view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:register_customer')
    
    def test_get_registration_page(self):
        """Test GET request to registration page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register_customer.html')
        self.assertContains(response, 'Customer Registration')
    
    @patch('accounts.views.send_verification_email')
    def test_successful_registration(self, mock_send_email):
        """Test successful customer registration."""
        form_data = {
            'username': 'newcustomer',
            'email': 'customer@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'phone_number': '07700123456',
            'address_line_1': '123 Test Street',
            'parish': 'st_helier',
            'postcode': 'JE2 3AB'
        }
        
        response = self.client.post(self.url, form_data)
        
        # Check redirect to login
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check user was created
        user = User.objects.get(email='customer@example.com')
        self.assertEqual(user.user_type, 'customer')
        self.assertFalse(user.email_verified)
        
        # Check profile was created
        self.assertTrue(hasattr(user, 'customerprofile'))
        
        # Check verification email was sent
        mock_send_email.assert_called_once()
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Registration successful', str(messages[0]))
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated users are redirected."""
        user = User.objects.create_user('test', 'test@test.com', 'test')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, '/')


class ArtistRegistrationViewTest(TestCase):
    """Test artist registration view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:register_artist')
    
    def test_get_registration_page(self):
        """Test GET request to artist registration page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register_artist.html')
        self.assertContains(response, 'Artist Registration')
    
    @patch('accounts.views.send_verification_email')
    def test_successful_artist_registration(self, mock_send_email):
        """Test successful artist registration."""
        form_data = {
            'username': 'newartist',
            'email': 'artist@example.com',
            'first_name': 'Jane',
            'last_name': 'Artist',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'artist_name': 'Jane Art Studio',
            'bio': 'I create art',
            'address_line_1': '456 Art Street',
            'parish': 'st_brelade',
            'postcode': 'JE3 8AB'
        }
        
        response = self.client.post(self.url, form_data)
        
        # Check redirect to login
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check user was created
        user = User.objects.get(email='artist@example.com')
        self.assertEqual(user.user_type, 'artist')
        self.assertFalse(user.email_verified)
        
        # Check profile was created
        self.assertTrue(hasattr(user, 'artistprofile'))
        self.assertEqual(user.artistprofile.display_name, 'Jane Art Studio')
        
        # Check verification email was sent
        mock_send_email.assert_called_once()


class LoginViewTest(TestCase):
    """Test login view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='test@example.com',  # NOT 'testuser'
            email='test@example.com',
            password='testpass123',
            email_verified=True,
            user_type='customer'
        )
    
    def test_get_login_page(self):
        """Test GET request to login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
    
    def test_successful_login(self):
        """Test successful login with email."""
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Check redirect (customer goes to gallery)
        self.assertRedirects(response, reverse('events:gallery'))
        
        # Check user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_unverified_email_login(self):
        """Test login with unverified email shows warning."""
        self.user.email_verified = False
        self.user.save()
        
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
        # Check warning message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('verify your email' in str(m).lower() for m in messages))
    
    def test_artist_login_redirect(self):
        """Test that artists are redirected to their artworks."""
        # Use a unique email to avoid conflicts
        artist = User.objects.create_user(
            username='artist_unique@test.com',  # More unique
            email='artist_unique@test.com',
            password='testpass123',
            user_type='artist',
            email_verified=True
        )
        
        response = self.client.post(self.url, {
            'email': 'artist_unique@test.com',
            'password': 'testpass123'
        })
    
        self.assertRedirects(response, reverse('events:my_artworks'))
    
    def test_next_parameter_redirect(self):
        """Test redirect to 'next' parameter after login."""
        next_url = reverse('accounts:profile')
        response = self.client.post(f'{self.url}?next={next_url}', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertRedirects(response, next_url)
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid email or password' in str(m) for m in messages))


class EmailVerificationViewTest(TestCase):
    """Test email verification view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            email_verified=False
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = email_verification_token.make_token(self.user)
        self.url = reverse('accounts:verify_email', kwargs={
            'uidb64': self.uid,
            'token': self.token
        })
    
    def test_successful_verification(self):
        """Test successful email verification."""
        response = self.client.get(self.url)
        
        # Refresh user from database
        self.user.refresh_from_db()
        
        # Check email is verified
        self.assertTrue(self.user.email_verified)
        
        # Check user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        
        # Check redirect
        self.assertRedirects(response, '/')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('verified successfully' in str(m) for m in messages))
    
    def test_invalid_token(self):
        """Test verification with invalid token."""
        url = reverse('accounts:verify_email', kwargs={
            'uidb64': self.uid,
            'token': 'invalid-token'
        })
        response = self.client.get(url)
        
        # Check email is still unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)
        
        # Check redirect to resend verification
        self.assertRedirects(response, reverse('accounts:resend_verification'))
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid verification link' in str(m) for m in messages))
    
    def test_invalid_uid(self):
        """Test verification with invalid uid."""
        url = reverse('accounts:verify_email', kwargs={
            'uidb64': 'invalid-uid',
            'token': self.token
        })
        response = self.client.get(url)
        
        self.assertRedirects(response, reverse('accounts:resend_verification'))
    
    
    def test_artist_verification_redirect(self):
        """Test artist is redirected to subscription plans after verification."""
        artist = User.objects.create_user(
            username='artistverify_unique@test.com',
            email='artistverify_unique@test.com',
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
        
        # Should redirect to subscription plans
        self.assertRedirects(response, reverse('subscriptions:plans'))

class ProfileViewTest(TestCase):
    """Test profile view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:profile')
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='test',
            user_type='customer'
        )
        self.artist = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='test',
            user_type='artist'
        )
    
    def test_login_required(self):
        """Test that login is required to access profile."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')
    
    def test_customer_profile_view(self):
        """Test customer can view their profile."""
        self.client.force_login(self.customer)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertContains(response, 'customer@test.com')
    
    def test_artist_profile_view(self):
        """Test artist can view their profile."""
        self.client.force_login(self.artist)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertContains(response, 'artist@test.com')
    
    def test_profile_update(self):
        """Test updating profile information."""
        self.client.force_login(self.customer)
        
        # Create profile first
        profile = CustomerProfile.objects.create(
            user=self.customer,
            address_line_1='Old Address',
            parish='st_helier',
            postcode='JE2 3AB'
        )
        
        # Update profile
        response = self.client.post(self.url, {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'customer@test.com',
            'phone': '07700123456',
            'address_line_1': 'New Address',
            'parish': 'st_brelade',
            'postcode': 'JE3 8CD',
            'marketing_consent': True
        })
        
        self.assertRedirects(response, self.url)
        
        # Check updates
        self.customer.refresh_from_db()
        profile.refresh_from_db()
        
        self.assertEqual(self.customer.first_name, 'Updated')
        self.assertEqual(self.customer.last_name, 'Name')
        self.assertEqual(profile.address_line_1, 'New Address')
        self.assertEqual(profile.parish, 'st_brelade')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('updated successfully' in str(m) for m in messages))


class ArtistDashboardViewTest(TestCase):
    """Test artist dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:artist_dashboard')
        self.artist = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='test',
            user_type='artist'
        )
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='test',
            user_type='customer'
        )
    
    def test_login_required(self):
        """Test that login is required for dashboard."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')
    
    def test_artist_only_access(self):
        """Test that only artists can access dashboard."""
        self.client.force_login(self.customer)
        response = self.client.get(self.url)
        
        self.assertRedirects(response, '/')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Artists only' in str(m) for m in messages))
    
    def test_artist_dashboard_display(self):
        """Test artist dashboard displays correctly."""
        self.client.force_login(self.artist)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/artist_dashboard.html')
        self.assertIn('subscription', response.context)
        self.assertIn('artwork_count', response.context)


class LogoutViewTest(TestCase):
    """Test logout view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:logout')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='test'
        )
    
    def test_logout(self):
        """Test user can logout."""
        self.client.force_login(self.user)
        
        # Confirm logged in
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        response = self.client.get(self.url)
        
        # Check redirect
        self.assertRedirects(response, '/')
        
        # Check user is logged out
        self.assertFalse(self.client.session.get('_auth_user_id'))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('logged out successfully' in str(m) for m in messages))


class ResendVerificationViewTest(TestCase):
    """Test resend verification email view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:resend_verification')
        self.user = User.objects.create_user(
            username='unverified',
            email='unverified@test.com',
            password='test',
            email_verified=False
        )
    
    def test_get_resend_page(self):
        """Test GET request to resend verification page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/resend_verification.html')
    
    @patch('accounts.views.send_verification_email')
    def test_resend_verification_email(self, mock_send_email):
        """Test resending verification email."""
        response = self.client.post(self.url, {
            'email': 'unverified@test.com'
        })
        
        # Check redirect to login
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check email was sent
        mock_send_email.assert_called_once_with(response.wsgi_request, self.user)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Verification email sent' in str(m) for m in messages))