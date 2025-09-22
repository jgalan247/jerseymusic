from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from decimal import Decimal
from unittest.mock import patch

from cart.models import Cart, CartItem, SavedItem
from artworks.models import Artwork, Category
from accounts.models import User


class CartModelTests(TestCase):
    """Test Cart model methods and properties."""
    
    def setUp(self):
        # Create test user (artist)
        self.artist = User.objects.create_user(
            username='artist@example.com',
            email='artist@example.com',
            password='testpass123',
            user_type='artist',
            first_name='Test',
            last_name='Artist'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Paintings',
            slug='paintings'
        )
        
        # Create test artwork
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            slug='test-painting',
            artist=self.artist,
            description='A test painting',
            category=self.category,
            price=Decimal('100.00'),
            stock_quantity=5,
            status='active',
            is_available=True
        )
        
        # Create cart for authenticated user
        self.cart = Cart.objects.create(user=self.artist)
    
    def test_cart_str(self):
        """Test cart string representation."""
        self.assertEqual(str(self.cart), f"Cart for {self.artist.username}")
        
        # Test anonymous cart
        anon_cart = Cart.objects.create(session_key='abc123def456')
        self.assertEqual(str(anon_cart), "Anonymous cart (abc123de...)")
    
    def test_empty_cart_properties(self):
        """Test empty cart calculations."""
        self.assertEqual(self.cart.total_items, 0)
        self.assertEqual(self.cart.subtotal, Decimal('0.00'))
        self.assertEqual(self.cart.shipping_cost, Decimal('5.00'))
        self.assertEqual(self.cart.total, Decimal('5.00'))
    
    def test_cart_with_items(self):
        """Test cart calculations with items."""
        # Add items to cart
        CartItem.objects.create(
            cart=self.cart,
            artwork=self.artwork,
            quantity=2,
            price_at_time=self.artwork.price
        )
        
        self.assertEqual(self.cart.total_items, 2)
        self.assertEqual(self.cart.subtotal, Decimal('200.00'))
        self.assertEqual(self.cart.shipping_cost, Decimal('0.00'))  # Free over £100
        self.assertEqual(self.cart.total, Decimal('200.00'))
    
    def test_shipping_calculation(self):
        """Test shipping cost calculation."""
        # Create cheaper artwork
        cheap_artwork = Artwork.objects.create(
            title='Cheap Print',
            slug='cheap-print',
            artist=self.artist,
            description='A cheap print',
            category=self.category,
            price=Decimal('25.00'),
            stock_quantity=10,
            status='active'
        )
        
        CartItem.objects.create(
            cart=self.cart,
            artwork=cheap_artwork,
            quantity=1,
            price_at_time=cheap_artwork.price
        )
        
        # Under £100 - should charge shipping
        self.assertEqual(self.cart.subtotal, Decimal('25.00'))
        self.assertEqual(self.cart.shipping_cost, Decimal('5.00'))
        self.assertEqual(self.cart.total, Decimal('30.00'))
    
    def test_cart_clear(self):
        """Test clearing cart."""
        CartItem.objects.create(
            cart=self.cart,
            artwork=self.artwork,
            quantity=1,
            price_at_time=self.artwork.price
        )
        
        self.assertEqual(self.cart.items.count(), 1)
        self.cart.clear()
        self.assertEqual(self.cart.items.count(), 0)
    
    def test_cart_merge(self):
        """Test merging carts after login."""
        # Create anonymous cart
        anon_cart = Cart.objects.create(session_key='test123')
        
        # Add items to anonymous cart
        CartItem.objects.create(
            cart=anon_cart,
            artwork=self.artwork,
            quantity=2,
            price_at_time=self.artwork.price
        )
        
        # Merge into user cart
        self.cart.merge_with(anon_cart)
        
        # Check item was transferred
        self.assertEqual(self.cart.items.count(), 1)
        self.assertEqual(self.cart.items.first().quantity, 2)
        
        # Check anonymous cart was deleted
        self.assertFalse(Cart.objects.filter(session_key='test123').exists())


class CartItemModelTests(TestCase):
    """Test CartItem model."""
    
    def setUp(self):
        self.artist = User.objects.create_user(
            username='artist@example.com',
            email='artist@example.com',
            password='testpass123',
            user_type='artist'
        )
        
        self.category = Category.objects.create(name='Paintings')
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('150.00'),
            stock_quantity=3,
            status='active',
            artwork_type='original'
        )
        
        self.cart = Cart.objects.create(user=self.artist)
    
    def test_cart_item_str(self):
        """Test cart item string representation."""
        item = CartItem.objects.create(
            cart=self.cart,
            artwork=self.artwork,
            quantity=2,
            price_at_time=self.artwork.price
        )
        self.assertEqual(str(item), "2x Test Painting")
    
    def test_cart_item_total_price(self):
        """Test cart item total price calculation."""
        item = CartItem.objects.create(
            cart=self.cart,
            artwork=self.artwork,
            quantity=3,
            price_at_time=Decimal('150.00')
        )
        self.assertEqual(item.total_price, Decimal('450.00'))
    
    def test_cart_item_auto_price(self):
        """Test automatic price setting on save."""
        item = CartItem(
            cart=self.cart,
            artwork=self.artwork,
            quantity=1
        )
        item.save()
        self.assertEqual(item.price_at_time, self.artwork.price)
    
    def test_is_available_original(self):
        """Test availability check for original artwork."""
        item = CartItem.objects.create(
            cart=self.cart,
            artwork=self.artwork,
            quantity=1,
            price_at_time=self.artwork.price
        )
        
        # Original available
        self.assertTrue(item.is_available)
        
        # Make artwork unavailable
        self.artwork.stock_quantity = 0
        self.artwork.save()
        self.assertFalse(item.is_available)
    
    def test_is_available_print(self):
        """Test availability check for prints."""
        print_artwork = Artwork.objects.create(
            title='Test Print',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('50.00'),
            stock_quantity=10,
            status='active',
            artwork_type='print'
        )
        
        item = CartItem.objects.create(
            cart=self.cart,
            artwork=print_artwork,
            quantity=5,
            price_at_time=print_artwork.price
        )
        
        # Should be available
        self.assertTrue(item.is_available)
        
        # Request more than available
        item.quantity = 15
        item.save()
        self.assertFalse(item.is_available)


class CartViewTests(TestCase):
    """Test cart views."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.artist = User.objects.create_user(
            username='artist@example.com',
            email='artist@example.com',
            password='testpass123',
            user_type='artist',
            first_name='Test',
            last_name='Artist'
        )
        
        self.customer = User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            user_type='customer'
        )
        
        # Create category and artwork
        self.category = Category.objects.create(name='Paintings')
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test painting',
            category=self.category,
            price=Decimal('200.00'),
            stock_quantity=5,
            status='active',
            is_available=True
        )
    
    def test_cart_view_empty(self):
        """Test viewing empty cart."""
        response = self.client.get(reverse('cart:view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your cart is empty')
    
    def test_add_to_cart_anonymous(self):
        """Test adding item to cart as anonymous user."""
        response = self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 2}
        )
        
        # Should redirect to cart view
        self.assertRedirects(response, reverse('cart:view'))
        
        # Check cart was created with session
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)
    
    def test_add_to_cart_authenticated(self):
        """Test adding item to cart as authenticated user."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 1}
        )
        
        self.assertRedirects(response, reverse('cart:view'))
        
        # Check cart was created for user
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 1)
    
    def test_add_to_cart_invalid_quantity(self):
        """Test adding item with invalid quantity."""
        response = self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': -1}
        )
        
        # Should redirect with error message
        self.assertRedirects(response, f'/artwork/{self.artwork.id}/')
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), "Invalid quantity.")
    
    def test_add_to_cart_exceeds_stock(self):
        """Test adding more items than available."""
        response = self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 10}  # Stock is only 5
        )
        
        self.assertRedirects(response, f'/artwork/{self.artwork.id}/')
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), "Only 5 available.")
    
    def test_add_to_cart_ajax(self):
        """Test AJAX add to cart."""
        response = self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_total_items'], 1)
    
    def test_update_cart_item(self):
        """Test updating cart item quantity."""
        # Add item first
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 1}
        )
        
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        item = cart.items.first()
        
        # Update quantity
        response = self.client.post(
            reverse('cart:update', kwargs={'item_id': item.id}),
            {'quantity': 3}
        )
        
        self.assertRedirects(response, reverse('cart:view'))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
    
    def test_remove_from_cart(self):
        """Test removing item from cart."""
        # Add item first
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 1}
        )
        
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        item = cart.items.first()
        
        # Remove item
        response = self.client.post(
            reverse('cart:remove', kwargs={'item_id': item.id})
        )
        
        self.assertRedirects(response, reverse('cart:view'))
        self.assertEqual(cart.items.count(), 0)
    
    def test_clear_cart(self):
        """Test clearing all items from cart."""
        # Add multiple items
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork.id}),
            {'quantity': 2}
        )
        
        response = self.client.post(reverse('cart:clear'))
        
        self.assertRedirects(response, reverse('cart:view'))
        
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        self.assertEqual(cart.items.count(), 0)
    
    def test_save_for_later_authenticated(self):
        """Test saving item for later (requires authentication)."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('cart:save', kwargs={'artwork_id': self.artwork.id})
        )
        
        self.assertRedirects(response, reverse('cart:view'))
        
        # Check saved item was created
        saved = SavedItem.objects.filter(
            user=self.customer,
            artwork=self.artwork
        )
        self.assertTrue(saved.exists())
    
    def test_save_for_later_unauthenticated(self):
        """Test saving for later redirects to login for anonymous users."""
        response = self.client.post(
            reverse('cart:save', kwargs={'artwork_id': self.artwork.id})
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_move_to_cart(self):
        """Test moving saved item back to cart."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        # Create saved item
        saved_item = SavedItem.objects.create(
            user=self.customer,
            artwork=self.artwork
        )
        
        response = self.client.post(
            reverse('cart:move_to_cart', kwargs={'item_id': saved_item.id})
        )
        
        self.assertRedirects(response, reverse('cart:view'))
        
        # Check item is in cart and removed from saved
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 1)
        self.assertFalse(SavedItem.objects.filter(id=saved_item.id).exists())


class CartIntegrationTests(TestCase):
    """Integration tests for cart functionality."""
    
    def setUp(self):
        self.client = Client()
        
        # Create test data
        self.artist = User.objects.create_user(
            username='artist@example.com',
            email='artist@example.com',
            password='testpass123',
            user_type='artist'
        )
        
        self.customer = User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            user_type='customer'
        )
        
        self.category = Category.objects.create(name='Paintings')
        
        # Create multiple artworks
        self.artwork1 = Artwork.objects.create(
            title='Artwork 1',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('75.00'),
            stock_quantity=3,
            status='active'
        )
        
        self.artwork2 = Artwork.objects.create(
            title='Artwork 2',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('50.00'),
            stock_quantity=5,
            status='active'
        )
    
    def test_anonymous_to_authenticated_cart_merge(self):
        """Test cart persistence from anonymous to authenticated."""
        # Add items as anonymous
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork1.id}),
            {'quantity': 1}
        )
        
        # Get anonymous cart
        session_key = self.client.session.session_key
        anon_cart = Cart.objects.get(session_key=session_key)
        self.assertEqual(anon_cart.items.count(), 1)
        
        # Login - this should trigger cart merge in real scenario
        # Note: In actual implementation, merge would happen in login view
        self.client.login(username='customer@example.com', password='testpass123')
        
        # Cart should still have items (in real app, merge would be handled by login view)
        # For this test, we'll manually simulate what should happen
        user_cart, created = Cart.objects.get_or_create(
            user=self.customer,
            is_active=True
        )
        if anon_cart.pk != user_cart.pk:
            user_cart.merge_with(anon_cart)
        
        self.assertEqual(user_cart.items.count(), 1)
    
    def test_cart_totals_with_multiple_items(self):
        """Test cart calculations with multiple items."""
        # Add first item
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork1.id}),
            {'quantity': 2}  # 2 x £75 = £150
        )
        
        # Add second item
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork2.id}),
            {'quantity': 1}  # 1 x £50 = £50
        )
        
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        
        # Check totals
        self.assertEqual(cart.total_items, 3)
        self.assertEqual(cart.subtotal, Decimal('200.00'))
        self.assertEqual(cart.shipping_cost, Decimal('0.00'))  # Free over £100
        self.assertEqual(cart.total, Decimal('200.00'))
    
    def test_cart_view_with_unavailable_items(self):
        """Test cart view when items become unavailable."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        # Add item to cart
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork1.id}),
            {'quantity': 1}
        )
        
        # Make artwork unavailable
        self.artwork1.stock_quantity = 0
        self.artwork1.save()
        
        # View cart
        response = self.client.get(reverse('cart:view'))
        self.assertEqual(response.status_code, 200)
        
        # Should show warning about availability
        messages = list(response.wsgi_request._messages)
        self.assertIn('no longer available', str(messages[-1]))
    
    def test_add_existing_item_updates_quantity(self):
        """Test adding an item that's already in cart updates quantity."""
        # Add item first time
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork1.id}),
            {'quantity': 1}
        )
        
        # Add same item again
        self.client.post(
            reverse('cart:add', kwargs={'artwork_id': self.artwork1.id}),
            {'quantity': 2}
        )
        
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        
        # Should have one item with quantity 3
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 3)