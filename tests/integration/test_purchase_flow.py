# tests/integration/test_purchase_flow.py

import pytest
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch, Mock

from accounts.models import CustomerProfile, ArtistProfile
from artworks.models import Artwork, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem, OrderStatusHistory
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestCompletePurchaseFlow(TransactionTestCase):
    """Test complete purchase flow from registration to order completion."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create artist with artwork
        self.artist_user = User.objects.create_user(
            username='testartist',
            email='artist@test.com',
            password='TestPass123!',
            user_type='artist',
            email_verified=True
        )
        self.artist_profile = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Test Artist',
            commission_rate=Decimal('15.00')
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Paintings',
            slug='paintings'
        )
        
        # Create artwork
        self.artwork = Artwork.objects.create(
            title='Test Painting',
            artist=self.artist_user,
            category=self.category,
            description='Beautiful test painting',
            price=Decimal('250.00'),
            stock_quantity=5,
            status='active',
            is_available=True
        )
        
    def test_guest_to_customer_purchase_flow(self):
        """Test complete flow: browse → add to cart → register → checkout → payment."""
        
        # 1. Browse artwork as guest
        response = self.client.get(reverse('artworks:gallery'))
        assert response.status_code == 200
        assert self.artwork.title in response.content.decode()
        
        # 2. View artwork detail
        response = self.client.get(
            reverse('artworks:artwork_detail', kwargs={'pk': self.artwork.pk})
        )
        assert response.status_code == 200
        
        # 3. Add to cart
        response = self.client.post(
            reverse('cart:add_to_cart'),
            {'artwork_id': self.artwork.pk, 'quantity': 1}
        )
        assert response.status_code in [200, 302]
        
        # Verify cart has item
        session = self.client.session
        cart_id = session.get('cart_id')
        assert cart_id is not None
        cart = Cart.objects.get(id=cart_id)
        assert cart.items.count() == 1
        assert cart.get_total() == Decimal('250.00')
        
        # 4. Go to checkout (should redirect to register/login)
        response = self.client.get(reverse('orders:checkout'))
        assert response.status_code in [200, 302]
        
        # 5. Register as new customer
        registration_data = {
            'username': '',  # Will use email
            'email': 'newcustomer@test.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'Customer',
            'phone_number': '+44 7797 123456',
            'address_line_1': '123 Test Street',
            'parish': 'st_helier',
            'postcode': 'JE2 3AB',
        }
        
        response = self.client.post(
            reverse('accounts:register_customer'),
            registration_data
        )
        assert response.status_code == 302
        
        # Check email was sent
        assert len(mail.outbox) == 1
        assert 'verify' in mail.outbox[0].subject.lower()
        
        # 6. Simulate email verification
        user = User.objects.get(email='newcustomer@test.com')
        user.email_verified = True
        user.save()
        
        # 7. Login
        login_success = self.client.login(
            username='newcustomer@test.com',
            password='SecurePass123!'
        )
        assert login_success
        
        # 8. Complete checkout
        checkout_data = {
            'first_name': 'New',
            'last_name': 'Customer',
            'email': 'newcustomer@test.com',
            'phone_number': '+44 7797 123456',
            'address_line_1': '123 Test Street',
            'address_line_2': '',
            'parish': 'st_helier',
            'postcode': 'JE2 3AB',
            'delivery_instructions': 'Leave with neighbor if out',
        }
        
        response = self.client.post(reverse('orders:checkout'), checkout_data)
        
        # Should redirect to payment
        assert response.status_code == 302
        
        # Verify order was created
        order = Order.objects.filter(user=user).first()
        assert order is not None
        assert order.total == Decimal('250.00')
        assert order.status == 'pending'
        assert order.items.count() == 1
        
        # 9. Simulate payment completion
        with patch('payments.views.process_payment') as mock_payment:
            mock_payment.return_value = {'status': 'success', 'transaction_id': 'TEST123'}
            
            response = self.client.post(
                reverse('payments:process'),
                {'order_id': order.id, 'payment_method': 'card'}
            )
            
            # Reload order
            order.refresh_from_db()
            assert order.is_paid == True
            assert order.status == 'processing'
            
        # 10. Verify post-purchase state
        # - Cart should be cleared
        cart.refresh_from_db()
        assert cart.items.count() == 0
        
        # - Order confirmation email sent
        assert len(mail.outbox) == 2  # Registration + order confirmation
        
        # - Stock updated
        self.artwork.refresh_from_db()
        assert self.artwork.stock_quantity == 4
    
    def test_existing_customer_purchase_flow(self):
        """Test purchase flow for existing logged-in customer."""
        
        # Create and login customer
        customer = User.objects.create_user(
            username='existing@test.com',
            email='existing@test.com',
            password='TestPass123!',
            user_type='customer',
            email_verified=True
        )
        CustomerProfile.objects.create(
            user=customer,
            address_line_1='456 Existing Street',
            parish='st_brelade',
            postcode='JE3 4CD'
        )
        
        self.client.login(username='existing@test.com', password='TestPass123!')
        
        # Add to cart
        response = self.client.post(
            reverse('cart:add_to_cart'),
            {'artwork_id': self.artwork.pk, 'quantity': 2}
        )
        
        # Go straight to checkout
        response = self.client.get(reverse('orders:checkout'))
        assert response.status_code == 200
        
        # Complete checkout with saved address
        checkout_data = {
            'first_name': customer.first_name or 'Test',
            'last_name': customer.last_name or 'Customer',
            'email': customer.email,
            'phone_number': '+44 7797 123456',
            'address_line_1': '456 Existing Street',
            'parish': 'st_brelade',
            'postcode': 'JE3 4CD',
            'delivery_instructions': '',
        }
        
        response = self.client.post(reverse('orders:checkout'), checkout_data)
        assert response.status_code == 302
        
        # Verify order
        order = Order.objects.filter(user=customer).first()
        assert order is not None
        assert order.total == Decimal('500.00')  # 2 x 250
        assert order.items.first().quantity == 2


@pytest.mark.django_db
class TestCommissionCalculation(TransactionTestCase):
    """Test commission calculation for artists."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create multiple artists with different commission rates
        self.artist1 = User.objects.create_user(
            username='artist1',
            email='artist1@test.com',
            password='TestPass123!',
            user_type='artist'
        )
        self.profile1 = ArtistProfile.objects.create(
            user=self.artist1,
            display_name='Artist One',
            commission_rate=Decimal('10.00')
        )
        
        self.artist2 = User.objects.create_user(
            username='artist2',
            email='artist2@test.com',
            password='TestPass123!',
            user_type='artist'
        )
        self.profile2 = ArtistProfile.objects.create(
            user=self.artist2,
            display_name='Artist Two',
            commission_rate=Decimal('15.00')
        )
        
        # Create artworks
        self.artwork1 = Artwork.objects.create(
            title='Artwork 1',
            artist=self.artist1,
            price=Decimal('100.00'),
            status='active'
        )
        
        self.artwork2 = Artwork.objects.create(
            title='Artwork 2',
            artist=self.artist2,
            price=Decimal('200.00'),
            status='active'
        )
        
        # Create customer
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='TestPass123!',
            user_type='customer'
        )
    
    def test_order_commission_calculation(self):
        """Test that commissions are correctly calculated for each artist."""
        
        # Create order with items from both artists
        order = Order.objects.create(
            user=self.customer,
            email='customer@test.com',
            first_name='Test',
            last_name='Customer',
            phone='123456',
            delivery_address_line_1='123 Test St',
            delivery_parish='st_helier',
            delivery_postcode='JE2 3AB',
            subtotal=Decimal('300.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('300.00'),
            status='processing',
            is_paid=True
        )
        
        # Add items
        item1 = OrderItem.objects.create(
            order=order,
            artwork=self.artwork1,
            artwork_title=self.artwork1.title,
            artwork_artist=str(self.artist1),
            quantity=1,
            price=self.artwork1.price
        )
        
        item2 = OrderItem.objects.create(
            order=order,
            artwork=self.artwork2,
            artwork_title=self.artwork2.title,
            artwork_artist=str(self.artist2),
            quantity=1,
            price=self.artwork2.price
        )
        
        # Calculate commissions
        commissions = order.calculate_commission()
        
        # Verify commission for artist 1 (10% of £100)
        artist1_commission = next(
            (c for c in commissions if c['artist'] == self.artist1), None
        )
        assert artist1_commission is not None
        assert artist1_commission['amount'] == Decimal('10.00')
        assert artist1_commission['rate'] == Decimal('10.00')
        
        # Verify commission for artist 2 (15% of £200)
        artist2_commission = next(
            (c for c in commissions if c['artist'] == self.artist2), None
        )
        assert artist2_commission is not None
        assert artist2_commission['amount'] == Decimal('30.00')
        assert artist2_commission['rate'] == Decimal('15.00')
        
        # Total platform commission: £40
        total_commission = sum(c['amount'] for c in commissions)
        assert total_commission == Decimal('40.00')


@pytest.mark.django_db
class TestShippingCalculation(TransactionTestCase):
    """Test shipping calculation including free shipping over £100."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create artist and artworks with different prices
        self.artist = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='TestPass123!',
            user_type='artist'
        )
        
        self.cheap_artwork = Artwork.objects.create(
            title='Cheap Art',
            artist=self.artist,
            price=Decimal('50.00'),
            status='active'
        )
        
        self.expensive_artwork = Artwork.objects.create(
            title='Expensive Art',
            artist=self.artist,
            price=Decimal('150.00'),
            status='active'
        )
        
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='TestPass123!',
            user_type='customer',
            email_verified=True
        )
    
    def test_standard_shipping_under_100(self):
        """Test that standard shipping is applied for orders under £100."""
        
        self.client.login(username='customer@test.com', password='TestPass123!')
        
        # Add cheap artwork to cart
        self.client.post(
            reverse('cart:add_to_cart'),
            {'artwork_id': self.cheap_artwork.pk, 'quantity': 1}
        )
        
        # Check cart total includes shipping
        response = self.client.get(reverse('cart:view'))
        assert response.status_code == 200
        
        # Cart should show shipping cost
        content = response.content.decode()
        assert '50.00' in content  # Subtotal
        # Shipping should be added (typically £5-10 for Jersey)
        
    def test_free_shipping_over_100(self):
        """Test that free shipping is applied for orders over £100."""
        
        self.client.login(username='customer@test.com', password='TestPass123!')
        
        # Add expensive artwork to cart
        self.client.post(
            reverse('cart:add_to_cart'),
            {'artwork_id': self.expensive_artwork.pk, 'quantity': 1}
        )
        
        # Check cart total
        response = self.client.get(reverse('cart:view'))
        assert response.status_code == 200
        
        content = response.content.decode()
        assert '150.00' in content  # Subtotal
        assert 'free shipping' in content.lower() or 'shipping: £0' in content.lower()


@pytest.mark.django_db
class TestRefundWorkflow(TransactionTestCase):
    """Test the complete refund request and approval workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create artist
        self.artist = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='TestPass123!',
            user_type='artist',
            email_verified=True
        )
        self.artist_profile = ArtistProfile.objects.create(
            user=self.artist,
            display_name='Test Artist'
        )
        
        # Create customer
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='TestPass123!',
            user_type='customer',
            email_verified=True
        )
        
        # Create completed order
        self.artwork = Artwork.objects.create(
            title='Test Art',
            artist=self.artist,
            price=Decimal('200.00'),
            status='active'
        )
        
        self.order = Order.objects.create(
            user=self.customer,
            order_number='JA-TEST123',
            email='customer@test.com',
            first_name='Test',
            last_name='Customer',
            phone='123456',
            delivery_address_line_1='123 Test St',
            delivery_parish='st_helier',
            delivery_postcode='JE2 3AB',
            subtotal=Decimal('200.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('200.00'),
            status='delivered',
            is_paid=True
        )
        
        OrderItem.objects.create(
            order=self.order,
            artwork=self.artwork,
            artwork_title=self.artwork.title,
            artwork_artist=str(self.artist),
            quantity=1,
            price=self.artwork.price
        )
    
    def test_customer_refund_request_flow(self):
        """Test customer requesting a refund."""
        
        # Login as customer
        self.client.login(username='customer@test.com', password='TestPass123!')
        
        # View order
        response = self.client.get(
            reverse('orders:order_detail', kwargs={'order_number': self.order.order_number})
        )
        assert response.status_code == 200
        assert 'request refund' in response.content.decode().lower()
        
        # Request refund
        refund_data = {
            'reason': 'damaged',
            'description': 'Artwork arrived with a tear in the canvas',
            'requested_amount': Decimal('200.00')
        }
        
        response = self.client.post(
            reverse('orders:request_refund', kwargs={'order_number': self.order.order_number}),
            refund_data
        )
        
        # Should redirect after successful submission
        assert response.status_code == 302
        
        # Verify refund request was created
        from orders.models import RefundRequest
        refund = RefundRequest.objects.filter(order=self.order).first()
        assert refund is not None
        assert refund.reason == 'damaged'
        assert refund.status == 'requested'
        
        # Check email notification sent
        assert len(mail.outbox) > 0
        
    def test_artist_refund_approval_flow(self):
        """Test artist approving a refund request."""
        
        # Create refund request
        from orders.models import RefundRequest
        refund = RefundRequest.objects.create(
            order=self.order,
            customer=self.customer,
            artist=self.artist,
            reason='Damaged item',
            status='requested'
        )
        
        # Login as artist
        self.client.login(username='artist@test.com', password='TestPass123!')
        
        # View refund requests
        response = self.client.get(reverse('orders:artist_refund_list'))
        assert response.status_code == 200
        assert self.order.order_number in response.content.decode()
        
        # Approve refund
        response = self.client.post(
            reverse('orders:artist_handle_refund', kwargs={'refund_id': refund.id}),
            {
                'action': 'approve',
                'response_message': 'Sorry for the damaged item. Refund approved.'
            }
        )
        
        # Should redirect after approval
        assert response.status_code == 302
        
        # Verify refund status
        refund.refresh_from_db()
        assert refund.status == 'approved'
        assert refund.artist_approved == True
        assert 'approved' in refund.artist_response.lower()