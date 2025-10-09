"""
Critical Workflow Regression Tests
Tests the most important revenue-generating and user experience flows
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from accounts.models import ArtistProfile, User
from events.models import Event, Venue
from orders.models import Order, OrderItem
from cart.models import CartItem
from payments.models import PaymentTransaction
from payments.services import SumUpPaymentService

User = get_user_model()


class UserAuthenticationWorkflowTests(TestCase):
    """Test user registration, login, and authentication flows"""

    def setUp(self):
        self.client = Client()
        self.registration_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'testpass123',
            'password2': 'testpass123',
        }

    def test_customer_registration_flow(self):
        """Test complete customer registration workflow"""
        # Step 1: Customer registration
        response = self.client.post(reverse('accounts:register'), self.registration_data)

        # Should redirect to email verification
        self.assertEqual(response.status_code, 302)

        # Check user was created
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_verified)

        # Check verification email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your email', mail.outbox[0].subject)

    def test_artist_registration_flow(self):
        """Test complete artist registration workflow"""
        # Step 1: Artist registration
        artist_data = self.registration_data.copy()
        artist_data['account_type'] = 'artist'
        artist_data['display_name'] = 'Test Artist'

        response = self.client.post(reverse('accounts:register'), artist_data)
        self.assertEqual(response.status_code, 302)

        # Check artist profile was created
        user = User.objects.get(username='testuser')
        self.assertTrue(hasattr(user, 'artist_profile'))
        self.assertFalse(user.artist_profile.is_approved)

    def test_login_logout_flow(self):
        """Test user login and logout functionality"""
        # Create verified user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_verified=True
        )

        # Test login
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)

        # Check user is logged in
        user = self.client.session.get('_auth_user_id')
        self.assertIsNotNone(user)

        # Test logout
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_password_reset_flow(self):
        """Test password reset workflow"""
        # Create user
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Request password reset
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)

        # Check reset email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset', mail.outbox[0].subject)


class EventCreationWorkflowTests(TestCase):
    """Test event creation and publishing workflows"""

    def setUp(self):
        self.client = Client()

        # Create approved artist
        self.user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123',
            is_verified=True
        )
        self.artist = ArtistProfile.objects.create(
            user=self.user,
            display_name='Test Artist',
            is_approved=True
        )

        # Create venue
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            capacity=100
        )

        # Login as artist
        self.client.login(username='artist', password='testpass123')

    def test_event_creation_flow(self):
        """Test complete event creation workflow"""
        event_data = {
            'title': 'Test Concert',
            'description': 'A test concert event',
            'venue': self.venue.id,
            'date': (timezone.now() + timedelta(days=30)).date(),
            'time': '19:30',
            'ticket_price': '25.00',
            'total_tickets': 50,
            'category': 'music',
        }

        response = self.client.post(reverse('events:create'), event_data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation

        # Check event was created
        event = Event.objects.get(title='Test Concert')
        self.assertEqual(event.artist, self.artist)
        self.assertEqual(event.status, 'draft')  # Should start as draft

    def test_event_publishing_flow(self):
        """Test event publishing workflow"""
        # Create draft event
        event = Event.objects.create(
            title='Test Concert',
            description='A test concert',
            artist=self.artist,
            venue=self.venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('25.00'),
            total_tickets=50,
            status='draft'
        )

        # Publish event
        response = self.client.post(reverse('events:publish', kwargs={'pk': event.pk}))
        self.assertEqual(response.status_code, 302)

        # Check event is now published
        event.refresh_from_db()
        self.assertEqual(event.status, 'published')

    def test_event_validation(self):
        """Test event creation validation"""
        # Try to create event with past date
        past_date = timezone.now().date() - timedelta(days=1)
        event_data = {
            'title': 'Past Concert',
            'description': 'This should fail',
            'venue': self.venue.id,
            'date': past_date,
            'time': '19:30',
            'ticket_price': '25.00',
            'total_tickets': 50,
        }

        response = self.client.post(reverse('events:create'), event_data)
        # Should show form with errors, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')


class TicketPurchaseWorkflowTests(TestCase):
    """Test end-to-end customer ticket purchasing"""

    def setUp(self):
        self.client = Client()

        # Create customer
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='testpass123',
            is_verified=True
        )

        # Create artist and event
        self.artist_user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Test Artist',
            is_approved=True
        )

        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            capacity=100
        )

        self.event = Event.objects.create(
            title='Test Concert',
            description='A test concert',
            artist=self.artist,
            venue=self.venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('25.00'),
            total_tickets=50,
            status='published'
        )

        # Login as customer
        self.client.login(username='customer', password='testpass123')

    def test_add_to_cart_flow(self):
        """Test adding tickets to cart"""
        response = self.client.post(reverse('cart:add'), {
            'event_id': self.event.id,
            'quantity': 2
        })

        # Should be AJAX response
        self.assertEqual(response.status_code, 200)

        # Check cart item was created
        cart_item = CartItem.objects.get(
            user=self.customer,
            event=self.event
        )
        self.assertEqual(cart_item.quantity, 2)

    def test_cart_to_checkout_flow(self):
        """Test moving from cart to checkout"""
        # Add item to cart
        CartItem.objects.create(
            user=self.customer,
            event=self.event,
            quantity=2
        )

        # Go to checkout
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)

        # Should show cart items
        self.assertContains(response, self.event.title)
        self.assertContains(response, '£50.00')  # 2 tickets × £25

    def test_order_creation_flow(self):
        """Test creating order from cart"""
        # Add item to cart
        CartItem.objects.create(
            user=self.customer,
            event=self.event,
            quantity=2
        )

        # Create order
        checkout_data = {
            'email': 'customer@example.com',
            'first_name': 'Test',
            'last_name': 'Customer',
            'phone': '+441234567890'
        }

        response = self.client.post(reverse('orders:checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)  # Redirect to payment

        # Check order was created
        order = Order.objects.get(user=self.customer)
        self.assertEqual(order.total_amount, Decimal('50.00'))

        # Check order items
        order_item = order.items.first()
        self.assertEqual(order_item.event, self.event)
        self.assertEqual(order_item.quantity, 2)

    def test_sold_out_protection(self):
        """Test protection against overselling"""
        # Set event to 1 ticket remaining
        self.event.total_tickets = 1
        self.event.save()

        # Try to add 2 tickets
        response = self.client.post(reverse('cart:add'), {
            'event_id': self.event.id,
            'quantity': 2
        })

        # Should return error
        self.assertEqual(response.status_code, 400)


class SumUpConnectionWorkflowTests(TestCase):
    """Test SumUp OAuth connection process"""

    def setUp(self):
        self.client = Client()

        # Create artist
        self.user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123',
            is_verified=True
        )
        self.artist = ArtistProfile.objects.create(
            user=self.user,
            display_name='Test Artist',
            is_approved=True,
            sumup_connection_status='not_connected'
        )

        self.client.login(username='artist', password='testpass123')

    def test_connection_initiation(self):
        """Test starting SumUp connection process"""
        response = self.client.get(reverse('payments:sumup_connect'))
        self.assertEqual(response.status_code, 302)

        # Should redirect to SumUp OAuth with correct parameters
        self.assertIn('api.sumup.com', response.url)
        self.assertIn('client_id', response.url)
        self.assertIn('redirect_uri', response.url)

    def test_oauth_callback_success(self):
        """Test successful OAuth callback"""
        # Simulate successful callback
        callback_url = reverse('payments:sumup_callback')
        response = self.client.get(callback_url + '?code=test_auth_code&state=test_state')

        # Should redirect to success page
        self.assertEqual(response.status_code, 302)

    def test_oauth_callback_error(self):
        """Test OAuth callback with error"""
        callback_url = reverse('payments:sumup_callback')
        response = self.client.get(callback_url + '?error=access_denied&error_description=User%20denied')

        # Should redirect to error page
        self.assertEqual(response.status_code, 302)

    def test_connection_status_update(self):
        """Test connection status updates correctly"""
        # Initially not connected
        self.assertEqual(self.artist.sumup_connection_status, 'not_connected')

        # Simulate successful connection (would normally be done in OAuth flow)
        self.artist.sumup_connection_status = 'connected'
        self.artist.sumup_merchant_code = 'MERCH123'
        self.artist.save()

        # Verify status updated
        self.artist.refresh_from_db()
        self.assertEqual(self.artist.sumup_connection_status, 'connected')


class PaymentProcessingWorkflowTests(TestCase):
    """Test payment processing for both customer payments and listing fees"""

    def setUp(self):
        self.client = Client()

        # Create customer and order
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='testpass123'
        )

        self.artist_user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Test Artist',
            sumup_connection_status='connected',
            sumup_merchant_code='MERCH123'
        )

        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City'
        )

        self.event = Event.objects.create(
            title='Test Concert',
            artist=self.artist,
            venue=self.venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('30.00'),
            total_tickets=50,
            status='published'
        )

        self.order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            first_name='Test',
            last_name='Customer',
            status='pending',
            total_amount=Decimal('60.00')
        )

        OrderItem.objects.create(
            order=self.order,
            event=self.event,
            quantity=2,
            price=Decimal('30.00')
        )

    def test_payment_service_initialization(self):
        """Test payment service initializes correctly"""
        service = SumUpPaymentService()
        self.assertIsNotNone(service)

        # Test with connected artist
        connected_service = SumUpPaymentService(artist=self.artist)
        self.assertIsNotNone(connected_service)

    def test_payment_amount_calculation(self):
        """Test payment amounts are calculated correctly"""
        service = SumUpPaymentService(artist=self.artist)

        # For connected artist: customer pays full amount, platform takes 5%
        payment_data = service.calculate_payment_routing(self.order)

        self.assertEqual(payment_data['customer_pays'], Decimal('60.00'))
        self.assertEqual(payment_data['platform_fee'], Decimal('3.00'))  # 5% of 60
        self.assertEqual(payment_data['artist_receives'], Decimal('57.00'))

    def test_listing_fee_calculation(self):
        """Test listing fees are calculated correctly"""
        service = SumUpPaymentService()

        listing_fee = service.calculate_listing_fee(self.event)
        # 5% of ticket price × quantity
        expected_fee = Decimal('30.00') * Decimal('0.05') * 2
        self.assertEqual(listing_fee, expected_fee)

    def test_payment_routing_connected_artist(self):
        """Test payment routing for connected artist"""
        # Connected artist should receive direct payment minus platform fee
        service = SumUpPaymentService(artist=self.artist)
        routing = service.get_payment_routing(self.order)

        self.assertEqual(routing['type'], 'direct_to_artist')
        self.assertEqual(routing['recipient'], self.artist.sumup_merchant_code)

    def test_payment_routing_non_connected_artist(self):
        """Test payment routing for non-connected artist"""
        # Set artist as not connected
        self.artist.sumup_connection_status = 'not_connected'
        self.artist.save()

        service = SumUpPaymentService(artist=self.artist)
        routing = service.get_payment_routing(self.order)

        self.assertEqual(routing['type'], 'platform_collection')
        self.assertIsNone(routing.get('recipient'))


class TicketGenerationWorkflowTests(TestCase):
    """Test ticket generation and email delivery"""

    def setUp(self):
        self.client = Client()

        # Create completed order
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='testpass123'
        )

        self.artist_user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Test Artist'
        )

        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City'
        )

        self.event = Event.objects.create(
            title='Test Concert',
            artist=self.artist,
            venue=self.venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('25.00'),
            total_tickets=50,
            status='published'
        )

        self.order = Order.objects.create(
            user=self.customer,
            email='customer@example.com',
            first_name='Test',
            last_name='Customer',
            status='confirmed',
            total_amount=Decimal('50.00')
        )

        OrderItem.objects.create(
            order=self.order,
            event=self.event,
            quantity=2,
            price=Decimal('25.00')
        )

    def test_ticket_generation_data_structure(self):
        """Test ticket data structure is correct"""
        from orders.services import TicketService

        service = TicketService()
        ticket_data = service.generate_ticket_data(self.order)

        # Check required fields
        self.assertIn('order_number', ticket_data)
        self.assertIn('customer_email', ticket_data)
        self.assertIn('event_title', ticket_data)
        self.assertIn('event_date', ticket_data)
        self.assertIn('venue_name', ticket_data)
        self.assertIn('quantity', ticket_data)
        self.assertIn('qr_code_data', ticket_data)

        # Check values
        self.assertEqual(ticket_data['customer_email'], 'customer@example.com')
        self.assertEqual(ticket_data['event_title'], 'Test Concert')
        self.assertEqual(ticket_data['venue_name'], 'Test Venue')
        self.assertEqual(ticket_data['quantity'], 2)

    def test_email_sending_on_order_confirmation(self):
        """Test email is sent when order is confirmed"""
        # Clear existing emails
        mail.outbox = []

        # Confirm order (simulate payment success)
        self.order.status = 'confirmed'
        self.order.save()

        # Trigger ticket email (normally done in payment webhook)
        from orders.services import TicketService
        service = TicketService()
        service.send_ticket_email(self.order)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Test Concert', email.subject)
        self.assertEqual(email.to, ['customer@example.com'])
        self.assertIn('ticket', email.body.lower())

    def test_qr_code_generation(self):
        """Test QR code is generated for tickets"""
        from orders.services import TicketService

        service = TicketService()
        qr_data = service.generate_qr_code_data(self.order)

        # Should contain order reference
        self.assertIn(str(self.order.id), qr_data)
        # Should be unique and verifiable
        self.assertTrue(len(qr_data) > 10)


class NavigationAndPageLoadingTests(TestCase):
    """Test basic navigation and critical page loading"""

    def setUp(self):
        self.client = Client()

        # Create test data
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_verified=True
        )

        self.artist_user = User.objects.create_user(
            username='artist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Test Artist',
            is_approved=True
        )

        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City'
        )

        self.event = Event.objects.create(
            title='Test Concert',
            artist=self.artist,
            venue=self.venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('25.00'),
            total_tickets=50,
            status='published'
        )

    def test_homepage_loads(self):
        """Test homepage loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jersey Events')  # Assuming site name

    def test_event_listing_page(self):
        """Test event listing page loads and shows events"""
        response = self.client.get(reverse('events:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Concert')

    def test_event_detail_page(self):
        """Test event detail page loads"""
        response = self.client.get(reverse('events:detail', kwargs={'pk': self.event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Concert')
        self.assertContains(response, '£25.00')

    def test_authentication_pages(self):
        """Test authentication pages load"""
        # Login page
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

        # Registration page
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_cart_page_loads(self):
        """Test cart page loads for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('cart:view'))
        self.assertEqual(response.status_code, 200)

    def test_artist_dashboard_loads(self):
        """Test artist dashboard loads for approved artists"""
        self.client.login(username='artist', password='testpass123')
        response = self.client.get(reverse('accounts:artist_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Artist')

    def test_analytics_dashboard_loads_for_staff(self):
        """Test analytics dashboard loads for staff users"""
        # Create staff user
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

        self.client.login(username='staff', password='testpass123')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_404_handling(self):
        """Test 404 pages are handled gracefully"""
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)

        # Test non-existent event
        response = self.client.get(reverse('events:detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_redirect_handling(self):
        """Test authentication redirects work correctly"""
        # Try to access protected page without login
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class CriticalWorkflowIntegrationTests(TestCase):
    """Integration tests covering complete user journeys"""

    def setUp(self):
        self.client = Client()

    def test_complete_customer_journey(self):
        """Test complete customer journey from registration to ticket purchase"""
        # Step 1: Customer registration
        response = self.client.post(reverse('accounts:register'), {
            'username': 'customer',
            'email': 'customer@example.com',
            'first_name': 'Test',
            'last_name': 'Customer',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

        # Step 2: Verify email (simulate)
        user = User.objects.get(username='customer')
        user.is_verified = True
        user.save()

        # Step 3: Login
        login_success = self.client.login(username='customer', password='testpass123')
        self.assertTrue(login_success)

        # Step 4: Browse events (create test event first)
        artist_user = User.objects.create_user(username='artist', email='artist@example.com', password='test')
        artist = ArtistProfile.objects.create(user=artist_user, display_name='Artist', is_approved=True)
        venue = Venue.objects.create(name='Venue', address='123 St', city='City')

        event = Event.objects.create(
            title='Concert',
            artist=artist,
            venue=venue,
            date=timezone.now().date() + timedelta(days=30),
            time='19:30',
            ticket_price=Decimal('25.00'),
            total_tickets=50,
            status='published'
        )

        # Step 5: Add to cart
        response = self.client.post(reverse('cart:add'), {
            'event_id': event.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, 200)

        # Step 6: Checkout
        response = self.client.post(reverse('orders:checkout'), {
            'email': 'customer@example.com',
            'first_name': 'Test',
            'last_name': 'Customer',
            'phone': '+441234567890'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to payment

        # Verify order was created
        order = Order.objects.get(user=user)
        self.assertEqual(order.total_amount, Decimal('50.00'))

    def test_complete_artist_journey(self):
        """Test complete artist journey from registration to event creation"""
        # Step 1: Artist registration
        response = self.client.post(reverse('accounts:register'), {
            'username': 'artist',
            'email': 'artist@example.com',
            'first_name': 'Test',
            'last_name': 'Artist',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'account_type': 'artist',
            'display_name': 'Test Artist'
        })
        self.assertEqual(response.status_code, 302)

        # Step 2: Approve artist (simulate admin action)
        user = User.objects.get(username='artist')
        user.is_verified = True
        user.save()
        artist = user.artist_profile
        artist.is_approved = True
        artist.save()

        # Step 3: Login
        self.client.login(username='artist', password='testpass123')

        # Step 4: Create venue
        venue = Venue.objects.create(name='Test Venue', address='123 St', city='City')

        # Step 5: Create event
        response = self.client.post(reverse('events:create'), {
            'title': 'Test Concert',
            'description': 'A test concert',
            'venue': venue.id,
            'date': (timezone.now() + timedelta(days=30)).date(),
            'time': '19:30',
            'ticket_price': '25.00',
            'total_tickets': 50,
            'category': 'music',
        })
        self.assertEqual(response.status_code, 302)

        # Step 6: Publish event
        event = Event.objects.get(title='Test Concert')
        response = self.client.post(reverse('events:publish', kwargs={'pk': event.pk}))
        self.assertEqual(response.status_code, 302)

        # Verify event is published
        event.refresh_from_db()
        self.assertEqual(event.status, 'published')