from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json
from unittest import skip
from orders.models import Order, OrderItem, OrderStatusHistory, RefundRequest
from orders.forms import CheckoutForm, RefundRequestForm, OrderStatusForm
from cart.models import Cart, CartItem
from artworks.models import Artwork, Category
from accounts.models import User
from payments.models import SumUpCheckout


class OrderModelTests(TestCase):
    """Test Order model methods and properties."""
    
    def setUp(self):
        # Create test users
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
            user_type='customer',
            first_name='John',
            last_name='Doe'
        )
        
        # Create test category and artwork
        self.category = Category.objects.create(name='Paintings')
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('200.00'),
            stock_quantity=5,
            status='active'
        )
    
    def test_order_number_generation(self):
        """Test automatic order number generation."""
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
        
        self.assertTrue(order.order_number.startswith('JA-'))
        self.assertEqual(len(order.order_number), 11)  # JA- + 8 chars
    
    def test_order_str(self):
        """Test order string representation."""
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
        
        self.assertEqual(str(order), f"Order {order.order_number}")
    
    def test_can_cancel_property(self):
        """Test can_cancel property for different statuses."""
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
        
        # Can cancel in these statuses
        for status in ['pending', 'processing', 'confirmed']:
            order.status = status
            order.save()
            self.assertTrue(order.can_cancel)
        
        # Cannot cancel in these statuses
        for status in ['shipped', 'delivered', 'cancelled', 'refunded']:
            order.status = status
            order.save()
            self.assertFalse(order.can_cancel)
    
    def test_full_name_property(self):
        """Test full_name property."""
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
        
        self.assertEqual(order.full_name, 'John Doe')
    
    def test_full_address_property(self):
        """Test full_address property."""
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_address_line_2='Apt 4B',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
        
        expected = "123 Test Street, Apt 4B, st_helier, JE2 4UH, Jersey"
        self.assertEqual(order.full_address, expected)


class OrderItemModelTests(TestCase):
    """Test OrderItem model."""
    
    def setUp(self):
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
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('150.00'),
            stock_quantity=3,
            status='active'
        )
        
        self.order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('150.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('155.00')
        )
    
    def test_order_item_str(self):
        """Test order item string representation."""
        item = OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            artwork_title='Test Painting',
            artwork_artist='Test Artist',
            artwork_type='original',
            quantity=2,
            price=Decimal('150.00')
        )
        
        self.assertEqual(str(item), '2x Test Painting')
    
    def test_order_item_total_calculation(self):
        """Test automatic total calculation."""
        item = OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            quantity=3,
            price=Decimal('150.00')
        )
        
        self.assertEqual(item.total, Decimal('450.00'))
    
    def test_order_item_stores_artwork_details(self):
        """Test that artwork details are stored at order time."""
        item = OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            quantity=1,
            price=self.artwork.price
        )
        
        # Should automatically store artwork details
        self.assertEqual(item.artwork_title, self.artwork.title)
        self.assertEqual(item.artwork_artist, self.artwork.artist.get_full_name())
        self.assertEqual(item.artwork_type, self.artwork.artwork_type)


class CheckoutFormTests(TestCase):
    """Test checkout form validation."""
    
    def test_valid_checkout_form(self):
        """Test valid checkout form submission."""
        form_data = {
            'customer_email': 'test@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '01534123456',
            'shipping_address_line_1': '123 Test Street',
            'shipping_address_line_2': '',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': True,
            'order_notes': ''
        }
        
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_jersey_postcode(self):
        """Test invalid Jersey postcode validation."""
        form_data = {
            'customer_email': 'test@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '01534123456',
            'shipping_address_line_1': '123 Test Street',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'ABC123',  # Invalid
            'billing_same_as_shipping': True
        }
        
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_postcode', form.errors)
    
    def test_valid_jersey_postcodes(self):
        """Test various valid Jersey postcode formats."""
        valid_postcodes = ['JE1 1AA', 'JE2 4UH', 'JE3 5ZZ', 'JE24UH', 'JE5 9XX']
        
        for postcode in valid_postcodes:
            form_data = {
                'customer_email': 'test@example.com',
                'customer_name': 'John Doe',
                'customer_phone': '01534123456',
                'shipping_address_line_1': '123 Test Street',
                'shipping_parish': 'ST_HELIER',
                'shipping_postcode': postcode,
                'billing_same_as_shipping': True
            }
            
            form = CheckoutForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Postcode {postcode} should be valid")
    
    def test_different_billing_address_required(self):
        """Test that billing address is required when not same as shipping."""
        form_data = {
            'customer_email': 'test@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '01534123456',
            'shipping_address_line_1': '123 Test Street',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': False,
            # Missing billing address fields
        }
        
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('billing_address_line_1', form.errors)
        self.assertIn('billing_parish', form.errors)
        self.assertIn('billing_postcode', form.errors)


class CustomerOrderViewTests(TestCase):
    """Test customer order views."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
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
        
        # Create test orders
        self.order1 = Order.objects.create(
            user=self.customer,
            order_number='JA-TEST0001',
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            status='delivered',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00'),
            is_paid=True
        )
        
        self.order2 = Order.objects.create(
            user=self.customer,
            order_number='JA-TEST0002',
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            status='processing',
            subtotal=Decimal('150.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('155.00'),
            is_paid=True
        )
    
    def test_customer_order_list_requires_login(self):
        """Test that order list requires authentication."""
        response = self.client.get(reverse('orders:my_orders'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_customer_order_list_view(self):
        """Test customer can view their orders."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.get(reverse('orders:my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'JA-TEST0001')
        self.assertContains(response, 'JA-TEST0002')
        self.assertEqual(len(response.context['orders']), 2)
    
    def test_customer_order_detail_view(self):
        """Test customer can view order details."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:detail', kwargs={'order_number': 'JA-TEST0001'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'JA-TEST0001')
        self.assertContains(response, '205.00')
    
    def test_customer_cannot_view_others_orders(self):
        """Test customer cannot view other users' orders."""
        other_customer = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123',
            user_type='customer'
        )
        
        other_order = Order.objects.create(
            user=other_customer,
            order_number='JA-OTHER001',
            email='other@example.com',
            phone='01534123456',
            delivery_first_name='Other',
            delivery_last_name='User',
            delivery_address_line_1='456 Other Street',
            delivery_parish='st_brelade',
            delivery_postcode='JE3 5XX',
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('105.00')
        )
        
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:detail', kwargs={'order_number': 'JA-OTHER001'})
        )
        self.assertEqual(response.status_code, 404)
    
    def test_guest_order_tracking(self):
        """Test guest order tracking with order number and email."""
        response = self.client.post(
            reverse('orders:track'),
            {
                'order_number': 'JA-TEST0001',
                'email': 'customer@example.com'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'JA-TEST0001')
    
    def test_guest_order_tracking_wrong_email(self):
        """Test guest tracking fails with wrong email."""
        response = self.client.post(
            reverse('orders:track'),
            {
                'order_number': 'JA-TEST0001',
                'email': 'wrong@example.com'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order not found')


class ArtistOrderViewTests(TestCase):
    """Test artist order views."""
    
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
            description='Test',
            category=self.category,
            price=Decimal('200.00'),
            stock_quantity=5,
            status='active'
        )
        
        # Create order with artist's artwork
        self.order = Order.objects.create(
            user=self.customer,
            order_number='JA-ARTIST01',
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00'),
            is_paid=True
        )
        
        # Add order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            artwork_title='Test Painting',
            artwork_artist='Test Artist',
            artwork_type='original',
            quantity=1,
            price=Decimal('200.00'),
            total=Decimal('200.00')
        )
    
    def test_artist_dashboard_requires_artist_user(self):
        """Test artist dashboard requires artist user type."""
        # Try as customer
        self.client.login(username='customer@example.com', password='testpass123')
        response = self.client.get(reverse('orders:artist_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirects
        
        # Try as artist
        self.client.login(username='artist@example.com', password='testpass123')
        response = self.client.get(reverse('orders:artist_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_artist_can_see_orders_with_their_artwork(self):
        """Test artist can see orders containing their artwork."""
        self.client.login(username='artist@example.com', password='testpass123')
        
        response = self.client.get(reverse('orders:artist_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'JA-ARTIST01')
        self.assertEqual(len(response.context['orders']), 1)
    
    def test_artist_order_detail_view(self):
        """Test artist can view order details for orders with their artwork."""
        self.client.login(username='artist@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:artist_order_detail', kwargs={'order_number': 'JA-ARTIST01'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Painting')
        
        # Check artist revenue calculation (90% after 10% platform fee)
        self.assertEqual(response.context['artist_revenue'], Decimal('200.00'))
        self.assertEqual(response.context['platform_fee'], Decimal('20.00'))
        self.assertEqual(response.context['artist_earnings'], Decimal('180.00'))
    
    def test_artist_sales_statistics(self):
        """Test artist sales statistics calculation."""
        self.client.login(username='artist@example.com', password='testpass123')
        
        response = self.client.get(reverse('orders:artist_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check calculated statistics
        self.assertEqual(response.context['total_revenue'], Decimal('200.00'))
        self.assertEqual(response.context['this_month_earnings'], Decimal('180.00'))  # 90% of 200
        self.assertEqual(response.context['platform_fees'], Decimal('20.00'))  # 10% of 200

@skip("Refunds handled via SumUp")
class RefundRequestTests(TestCase):
    """Test refund request functionality."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
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
        
        # Create category and artwork
        self.category = Category.objects.create(name='Paintings')
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('200.00'),
            stock_quantity=5,
            status='active'
        )
        
        # Create delivered order
        self.order = Order.objects.create(
            user=self.customer,
            order_number='JA-REFUND01',
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            status='delivered',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00'),
            is_paid=True
        )
        
        # Add order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            artwork_title='Test Painting',
            artwork_artist='Test Artist',
            artwork_type='original',
            quantity=1,
            price=Decimal('200.00')
        )
    
    def test_customer_can_request_refund(self):
        """Test customer can request refund for delivered order."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:request_refund', kwargs={'order_number': 'JA-REFUND01'})
        )
        self.assertEqual(response.status_code, 200)
        
        # Submit refund request
        response = self.client.post(
            reverse('orders:request_refund', kwargs={'order_number': 'JA-REFUND01'}),
            {
                'reason': 'damaged',
                'description': 'Item arrived damaged'
            }
        )
        
        # Should redirect to order detail
        self.assertRedirects(
            response,
            reverse('orders:detail', kwargs={'order_number': 'JA-REFUND01'})
        )
        
        # Check refund request was created
        refund_exists = RefundRequest.objects.filter(
            order=self.order,
            customer=self.customer
        ).exists()
        self.assertTrue(refund_exists)
    
    def test_cannot_request_refund_for_pending_order(self):
        """Test cannot request refund for pending order."""
        self.order.status = 'pending'
        self.order.save()
        
        self.client.login(username='customer@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:request_refund', kwargs={'order_number': 'JA-REFUND01'})
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
    
    def test_artist_can_handle_refund_request(self):
        """Test artist can approve/reject refund requests."""
        # Create refund request
        refund_request = RefundRequest.objects.create(
            order=self.order,
            customer=self.customer,
            artist=self.artist,
            reason='Item arrived damaged',
            status='requested'
        )
        
        self.client.login(username='artist@example.com', password='testpass123')
        
        # View refund request
        response = self.client.get(
            reverse('orders:artist_handle_refund', kwargs={'refund_id': refund_request.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Approve refund
        response = self.client.post(
            reverse('orders:artist_handle_refund', kwargs={'refund_id': refund_request.id}),
            {
                'action': 'approve',
                'response_message': 'Refund approved, processing through SumUp'
            }
        )
        
        # Should redirect to refund list
        self.assertRedirects(response, reverse('orders:artist_refund_list'))
        
        # Check refund status updated
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'approved')
        self.assertTrue(refund_request.artist_approved)


class OrderStatusHistoryTests(TestCase):
    """Test order status history tracking."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            user_type='customer'
        )
        
        self.order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00')
        )
    
    def test_status_history_creation(self):
        """Test creating status history entries."""
        # Create status history
        history1 = OrderStatusHistory.objects.create(
            order=self.order,
            status='processing',
            note='Payment confirmed'
        )
        
        history2 = OrderStatusHistory.objects.create(
            order=self.order,
            status='shipped',
            note='Dispatched via Royal Mail'
        )
        
        # Check history is associated with order
        self.assertEqual(self.order.status_history.count(), 2)
        
        # Check ordering (newest first)
        histories = self.order.status_history.all()
        self.assertEqual(histories[0].status, 'shipped')
        self.assertEqual(histories[1].status, 'processing')


class OrderIntegrationTests(TestCase):
    """Integration tests for order flow."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
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
        
        # Create category and artwork
        self.category = Category.objects.create(name='Paintings')
        
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist,
            description='Test',
            category=self.category,
            price=Decimal('200.00'),
            stock_quantity=5,
            status='active'
        )
    
    def test_complete_order_flow(self):
        """Test complete order flow from cart to order."""
        self.client.login(username='customer@example.com', password='testpass123')
        
        # Add item to cart
        cart = Cart.objects.create(user=self.customer)
        cart_item = CartItem.objects.create(
            cart=cart,
            artwork=self.artwork,
            quantity=1,
            price_at_time=self.artwork.price
        )
        
        # Create order from cart
        order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=cart.subtotal,
            shipping_cost=cart.shipping_cost,
            total=cart.total
        )
        
        # Create order items from cart items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                artwork=cart_item.artwork,
                artwork_title=cart_item.artwork.title,
                artwork_artist=cart_item.artwork.artist.get_full_name(),
                artwork_type=cart_item.artwork.artwork_type,
                quantity=cart_item.quantity,
                price=cart_item.price_at_time
            )
        
        # Clear cart after order
        cart.clear()
        
        # Verify order created correctly
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total, Decimal('200.00'))  # 200 + 5 shipping
        self.assertEqual(cart.items.count(), 0)  # Cart should be empty
    
    def test_order_statistics_api(self):
        """Test order statistics API endpoint for artists."""
        # Create some orders
        order1 = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            phone='01534123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('205.00'),
            is_paid=True
        )
        
        OrderItem.objects.create(
            order=order1,
            artwork=self.artwork,
            artwork_title='Test Painting',
            artwork_artist='Test Artist',
            quantity=1,
            price=Decimal('200.00')
        )
        
        self.client.login(username='artist@example.com', password='testpass123')
        
        response = self.client.get(reverse('orders:statistics') + '?period=30')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('daily_sales', data)
        self.assertIn('total_orders', data)
        self.assertIn('total_revenue', data)
