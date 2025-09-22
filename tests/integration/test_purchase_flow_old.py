"""
Integration tests for complete purchase workflow
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from artworks.models import Artwork
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem

User = get_user_model()


class CompletePurchaseFlowTest(TestCase):
    """Test complete customer purchase journey"""
    
    def setUp(self):
        # Create artist and customer
        self.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='pass123',
            user_type='artist'
        )
        
        self.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='pass123',
            user_type='customer'
        )
        
        # Create artwork
        self.artwork = Artwork.objects.create(
            title='Beautiful Jersey Sunset',
            slug='beautiful-jersey-sunset',
            artist=self.artist,
            description='A sunset over St. Ouen\'s Bay',
            price=Decimal('250.00'),
            status='active',
            is_available=True,
            stock_quantity=5
        )
        
        self.client = Client()
    
    def test_browse_to_purchase_flow(self):
        """Test: Browse → Add to Cart → Checkout → Order Creation"""
        # Step 1: Customer logs in
        login_success = self.client.login(
            username='customer@test.com',
            password='pass123'
        )
        self.assertTrue(login_success)
        
        # Step 2: Browse artwork (gallery page)
        response = self.client.get('/gallery/')
        self.assertEqual(response.status_code, 200)
        
        # Step 3: View artwork details
        response = self.client.get(f'/artwork/{self.artwork.pk}/')
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Add to cart
        response = self.client.post(
            f'/cart/add/{self.artwork.id}/',
            {'quantity': 1}
        )
        self.assertIn(response.status_code, [200, 302])
        
        # Verify item in cart
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 1)
        cart_item = cart.items.first()
        self.assertEqual(cart_item.artwork, self.artwork)
        self.assertEqual(cart_item.quantity, 1)
        
        # Step 5: View cart
        response = self.client.get('/cart/')
        self.assertEqual(response.status_code, 200)
        
        # Step 6: Proceed to checkout (would need checkout implementation)
        # This is a simplified version - adapt to your actual checkout process
    
    def test_cart_persistence_across_sessions(self):
        """Test cart persists when user logs out and back in"""
        # Login and add item
        self.client.login(username='customer@test.com', password='pass123')
        self.client.post(f'/cart/add/{self.artwork.id}/', {'quantity': 2})
        
        # Verify cart has item
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 1)
        
        # Logout
        self.client.logout()
        
        # Login again
        self.client.login(username='customer@test.com', password='pass123')
        
        # Cart should still have items
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)


class RegistrationToPurchaseTest(TestCase):
    """Test new user registration through to first purchase"""
    
    def setUp(self):
        self.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='pass123',
            user_type='artist'
        )
        
        self.artwork = Artwork.objects.create(
            title='Jersey Lighthouse',
            slug='jersey-lighthouse',
            artist=self.artist,
            description='Corbière Lighthouse at sunset',
            price=Decimal('150.00'),
            status='active',
            is_available=True,
            stock_quantity=3
        )
        
        self.client = Client()
    
    def test_new_customer_journey(self):
        """Test: Registration → Email Verification → First Purchase"""
        # Step 1: Register new customer
        response = self.client.post('/accounts/register/customer/', {
            'email': 'newcustomer@example.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!'
        })
        self.assertIn(response.status_code, [200, 302])
        
        # Verify user created but not verified
        new_user = User.objects.get(email='newcustomer@example.com')
        self.assertFalse(new_user.email_verified)
        self.assertEqual(new_user.user_type, 'customer')
        
        # Step 2: Simulate email verification (in real test would check email)
        new_user.email_verified = True
        new_user.save()
        
        # Step 3: Login
        login_success = self.client.login(
            username='newcustomer@example.com',
            password='TestPass123!'
        )
        self.assertTrue(login_success)
        
        # Step 4: Add artwork to cart
        response = self.client.post(
            f'/cart/add/{self.artwork.id}/',
            {'quantity': 1}
        )
        
        # Verify cart created for new user
        cart = Cart.objects.get(user=new_user)
        self.assertEqual(cart.items.count(), 1)


class ArtistWorkflowTest(TestCase):
    """Test artist workflow from registration to receiving orders"""
    
    def setUp(self):
        self.client = Client()
    
    def test_artist_upload_to_sale(self):
        """Test: Artist Registration → Upload Artwork → Customer Purchase"""
        # Step 1: Register as artist
        response = self.client.post('/accounts/register/artist/', {
            'email': 'newartist@example.com',
            'first_name': 'New',
            'last_name': 'Artist',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'business_name': 'New Art Studio',
            'phone_number': '07700900000'
        })
        
        artist = User.objects.get(email='newartist@example.com')
        artist.email_verified = True
        artist.save()
        
        # Step 2: Artist logs in
        self.client.login(username='newartist@example.com', password='TestPass123!')
        
        # Step 3: Upload artwork (simplified - would need file upload)
        artwork = Artwork.objects.create(
            artist=artist,
            title='My First Artwork',
            slug='my-first-artwork',
            description='First piece for sale',
            price=Decimal('200.00'),
            status='active',
            is_available=True
        )
        
        # Step 4: Customer purchases the artwork
        customer = User.objects.create_user(
            username='buyer@test.com',
            email='buyer@test.com',
            password='pass123',
            user_type='customer'
        )
        
        # Create order
        order = Order.objects.create(
            user=customer,
            email='buyer@test.com',
            phone='123456',
            delivery_first_name='Buyer',
            delivery_last_name='Name',
            delivery_address_line_1='123 Test St',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00'),
            status='confirmed',
            is_paid=True
        )
        
        OrderItem.objects.create(
            order=order,
            artwork=artwork,
            artwork_title=artwork.title,
            artwork_artist=artist.get_full_name(),
            artwork_type='original',
            quantity=1,
            price=artwork.price,
            total=artwork.price
        )
        
        # Step 5: Verify artist can see the order
        self.client.login(username='newartist@example.com', password='TestPass123!')
        response = self.client.get('/orders/artist/orders/')
        self.assertEqual(response.status_code, 200)
        
        # Artist should see this order
        artist_orders = Order.objects.filter(
            items__artwork__artist=artist,
            is_paid=True
        ).distinct()
        self.assertEqual(artist_orders.count(), 1)
        self.assertEqual(artist_orders.first(), order)
