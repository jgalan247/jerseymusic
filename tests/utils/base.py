"""
Base test classes and utilities for Jersey Artwork testing
"""
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
import io
import json
from decimal import Decimal

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common utilities"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
    
    def create_user(self, username='testuser', email='test@example.com', 
                   password='testpass123', is_artist=False, is_active=True):
        """Helper to create a user"""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=is_active
        )
        if is_artist:
            user.is_artist = True
            user.save()
        return user
    
    def create_artist(self, username='artist', email='artist@example.com',
                     password='artistpass123'):
        """Helper to create an artist user"""
        return self.create_user(
            username=username,
            email=email,
            password=password,
            is_artist=True
        )
    
    def create_customer(self, username='customer', email='customer@example.com',
                       password='customerpass123'):
        """Helper to create a customer user"""
        return self.create_user(
            username=username,
            email=email,
            password=password,
            is_artist=False
        )
    
    def login_user(self, user, password='testpass123'):
        """Helper to login a user"""
        self.client.login(username=user.username, password=password)
        return self.client
    
    def create_test_image(self, name='test.jpg', size=(100, 100), 
                         image_format='JPEG', color='red'):
        """Create a test image file"""
        file = io.BytesIO()
        image = Image.new('RGB', size, color)
        image.save(file, image_format)
        file.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file.read(),
            content_type=f'image/{image_format.lower()}'
        )
    
    def assert_redirect_to_login(self, response, next_url=None):
        """Assert that response redirects to login page"""
        self.assertEqual(response.status_code, 302)
        if next_url:
            self.assertIn('/accounts/login/', response.url)
            self.assertIn(f'next={next_url}', response.url)
    
    def assert_permission_denied(self, response):
        """Assert that response is 403 Forbidden"""
        self.assertEqual(response.status_code, 403)
    
    def get_json_response(self, response):
        """Parse JSON response"""
        return json.loads(response.content.decode('utf-8'))


class EmailTestMixin:
    """Mixin for testing email functionality"""
    
    def assert_email_sent(self, subject=None, to=None, body_contains=None):
        """Assert that an email was sent with given criteria"""
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        if subject:
            self.assertEqual(email.subject, subject)
        if to:
            self.assertIn(to, email.to)
        if body_contains:
            self.assertIn(body_contains, email.body)
        
        return email
    
    def assert_no_emails_sent(self):
        """Assert that no emails were sent"""
        self.assertEqual(len(mail.outbox), 0)
    
    def clear_mail_outbox(self):
        """Clear the test mail outbox"""
        mail.outbox = []
    
    def get_email_confirmation_url(self, email):
        """Extract confirmation URL from email"""
        import re
        # Adjust this regex based on your email template
        pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(pattern, email.body)
        return urls[0] if urls else None


class ArtworkTestMixin:
    """Mixin for artwork-related test utilities"""
    
    def create_artwork(self, artist, title='Test Artwork', price=Decimal('100.00'),
                      description='Test description', stock=10, is_active=True):
        """Create a test artwork"""
        from artworks.models import Artwork
        
        artwork = Artwork.objects.create(
            artist=artist,
            title=title,
            price=price,
            description=description,
            stock=stock,
            is_active=is_active,
            image=self.create_test_image()
        )
        return artwork
    
    def create_multiple_artworks(self, artist, count=5):
        """Create multiple test artworks"""
        artworks = []
        for i in range(count):
            artwork = self.create_artwork(
                artist=artist,
                title=f'Artwork {i+1}',
                price=Decimal(f'{(i+1) * 50}.00')
            )
            artworks.append(artwork)
        return artworks


class OrderTestMixin:
    """Mixin for order-related test utilities"""
    
    def create_order(self, customer, status='pending'):
        """Create a test order"""
        from orders.models import Order
        
        order = Order.objects.create(
            customer=customer,
            status=status,
            total_amount=Decimal('0.00'),
            shipping_address='123 Test St',
            shipping_city='Test City',
            shipping_postal_code='12345',
            shipping_country='JE'
        )
        return order
    
    def add_item_to_order(self, order, artwork, quantity=1):
        """Add an item to an order"""
        from orders.models import OrderItem
        
        item = OrderItem.objects.create(
            order=order,
            artwork=artwork,
            quantity=quantity,
            price=artwork.price
        )
        
        # Update order total
        order.total_amount += item.price * quantity
        order.save()
        
        return item
    
    def create_complete_order(self, customer, artist, num_items=2):
        """Create a complete order with items"""
        order = self.create_order(customer)
        
        for i in range(num_items):
            artwork = self.create_artwork(
                artist=artist,
                title=f'Order Item {i+1}',
                price=Decimal(f'{(i+1) * 25}.00')
            )
            self.add_item_to_order(order, artwork)
        
        return order


class AuthenticatedTestCase(BaseTestCase, EmailTestMixin):
    """Base test case for authenticated views"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_customer()
        self.client = self.login_user(self.user)
    
    def assert_requires_login(self, url, method='get', **kwargs):
        """Assert that a URL requires login"""
        self.client.logout()
        
        if method == 'get':
            response = self.client.get(url, **kwargs)
        elif method == 'post':
            response = self.client.post(url, **kwargs)
        elif method == 'put':
            response = self.client.put(url, **kwargs)
        elif method == 'delete':
            response = self.client.delete(url, **kwargs)
        
        self.assert_redirect_to_login(response, url)


class ArtistTestCase(BaseTestCase, EmailTestMixin, ArtworkTestMixin):
    """Base test case for artist-specific functionality"""
    
    def setUp(self):
        super().setUp()
        self.artist = self.create_artist()
        self.client = self.login_user(self.artist, 'artistpass123')
    
    def assert_artist_only(self, url, method='get', **kwargs):
        """Assert that a URL is only accessible to artists"""
        # Test with customer
        customer = self.create_customer('customer2', 'customer2@example.com')
        self.client.logout()
        self.login_user(customer, 'customerpass123')
        
        if method == 'get':
            response = self.client.get(url, **kwargs)
        elif method == 'post':
            response = self.client.post(url, **kwargs)
        
        self.assert_permission_denied(response)


class IntegrationTestCase(TransactionTestCase, EmailTestMixin, 
                         ArtworkTestMixin, OrderTestMixin):
    """Base test case for integration tests"""
    
    def setUp(self):
        super().setUp()
        self.client = Client()
    
    def simulate_user_registration(self, username='newuser', 
                                  email='newuser@example.com',
                                  password='newpass123'):
        """Simulate complete user registration flow"""
        # Submit registration form
        response = self.client.post(reverse('accounts:register'), {
            'username': username,
            'email': email,
            'password1': password,
            'password2': password,
        })
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Extract and visit confirmation URL
        confirmation_url = self.get_email_confirmation_url(mail.outbox[0])
        if confirmation_url:
            self.client.get(confirmation_url)
        
        # Return the created user
        return User.objects.get(username=username)
    
    def simulate_purchase_flow(self, customer, artwork):
        """Simulate complete purchase flow"""
        # Login
        self.client.login(username=customer.username, password='testpass123')
        
        # Add to cart
        self.client.post(reverse('cart:add_to_cart'), {
            'artwork_id': artwork.id,
            'quantity': 1
        })
        
        # Checkout
        response = self.client.post(reverse('orders:checkout'), {
            'shipping_address': '123 Test St',
            'shipping_city': 'Test City',
            'shipping_postal_code': '12345',
            'shipping_country': 'JE',
            'payment_method': 'test'
        })
        
        # Get the created order
        from orders.models import Order
        order = Order.objects.filter(customer=customer).first()
        
        return order