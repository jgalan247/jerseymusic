# accounts/tests/test_models.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import CustomerProfile, ArtistProfile

User = get_user_model()


class UserModelTest(TestCase):
    """Test the custom User model."""
    
    def setUp(self):
        """Create test users."""
        self.customer_user = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        
        self.artist_user = User.objects.create_user(
            username='artist1',
            email='artist@test.com',
            password='testpass123',
            first_name='Jane',
            last_name='Artist',
            user_type='artist'
        )
    
    def test_user_creation(self):
        """Test user is created with correct attributes."""
        self.assertEqual(self.customer_user.email, 'customer@test.com')
        self.assertEqual(self.customer_user.user_type, 'customer')
        self.assertFalse(self.customer_user.email_verified)
        self.assertTrue(self.customer_user.check_password('testpass123'))
    
    def test_get_full_name(self):
        """Test the get_full_name method."""
        self.assertEqual(self.customer_user.get_full_name(), 'John Doe')
        self.assertEqual(self.artist_user.get_full_name(), 'Jane Artist')
    
    def test_user_str(self):
        """Test the string representation of User."""
        self.assertEqual(str(self.customer_user), 'customer1')
    
    def test_default_email_verified(self):
        """Test email_verified defaults to False."""
        user = User.objects.create_user(
            username='test',
            email='test@test.com',
            password='test'
        )
        self.assertFalse(user.email_verified)


class CustomerProfileModelTest(TestCase):
    """Test the CustomerProfile model."""
    
    def setUp(self):
        """Create test customer and profile."""
        self.user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123',
            user_type='customer'
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            address_line_1='123 Test Street',
            parish='st_helier',
            postcode='JE2 3AB'
        )
    
    def test_profile_creation(self):
        """Test customer profile is created correctly."""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.address_line_1, '123 Test Street')
        self.assertEqual(self.profile.parish, 'st_helier')
        self.assertEqual(self.profile.postcode, 'JE2 3AB')
        self.assertFalse(self.profile.marketing_consent)
    
    def test_profile_str(self):
        """Test string representation of CustomerProfile."""
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()
        self.assertEqual(str(self.profile), 'John Doe - Customer')
    
    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        self.assertEqual(self.profile.get_absolute_url(), '/accounts/profile/')


class ArtistProfileModelTest(TestCase):
    """Test the ArtistProfile model."""
    
    def setUp(self):
        """Create test artist and profile."""
        self.user = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='testpass123',
            user_type='artist'
        )
        self.profile = ArtistProfile.objects.create(
            user=self.user,
            display_name='Test Artist Studio',
            bio='I create beautiful art',
            commission_rate=15.00
        )
    
    def test_profile_creation(self):
        """Test artist profile is created correctly."""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.display_name, 'Test Artist Studio')
        self.assertEqual(self.profile.bio, 'I create beautiful art')
        self.assertEqual(self.profile.commission_rate, 15.00)
        self.assertFalse(self.profile.is_approved)
    
    def test_profile_str(self):
        """Test string representation of ArtistProfile."""
        self.assertEqual(str(self.profile), 'Test Artist Studio - Artist')
    
    def test_default_commission_rate(self):
        """Test commission_rate defaults to 15.00."""
        profile = ArtistProfile.objects.create(
            user=User.objects.create_user('test', 'test@test.com', 'test'),
            display_name='Test'
        )
        self.assertEqual(profile.commission_rate, 15.00)


