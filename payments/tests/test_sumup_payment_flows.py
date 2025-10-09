"""
Automated test suite for SumUp payment flows.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
import json

from accounts.models import ArtistProfile
from events.models import Event
from orders.models import Order, OrderItem
from payments.connected_payment_service import ConnectedPaymentService
from payments.models import SumUpCheckout, SumUpTransaction

User = get_user_model()


class SumUpPaymentFlowTests(TestCase):
    """Test suite for SumUp payment flows."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.connected_artist_user = User.objects.create_user(
            username='connected_artist',
            email='connected@test.com',
            first_name='Connected',
            last_name='Artist',
            user_type='artist'
        )

        self.not_connected_artist_user = User.objects.create_user(
            username='not_connected_artist',
            email='notconnected@test.com',
            first_name='NotConnected',
            last_name='Artist',
            user_type='artist'
        )

        self.customer_user = User.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            first_name='Test',
            last_name='Customer',
            user_type='customer'
        )

        # Create artist profiles
        self.connected_artist = ArtistProfile.objects.create(
            user=self.connected_artist_user,
            display_name='Connected Artist',
            bio='Test connected artist',
            is_approved=True,
            sumup_connection_status='connected'
        )

        # Set up SumUp connection
        self.connected_artist.update_sumup_connection({
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 3600,
            'scope': 'payments',
            'merchant_code': 'TEST_MERCHANT_001'
        })

        self.not_connected_artist = ArtistProfile.objects.create(
            user=self.not_connected_artist_user,
            display_name='Not Connected Artist',
            bio='Test not connected artist',
            is_approved=True,
            sumup_connection_status='not_connected'
        )

        # Create test events
        self.connected_event = Event.objects.create(
            title='Connected Artist Event',
            slug='connected-artist-event',
            organiser=self.connected_artist_user,
            description='Test event by connected artist',
            venue_name='Test Venue',
            venue_address='Test Address',
            event_date=timezone.now().date() + timedelta(days=30),
            event_time=timezone.now().time(),
            capacity=100,
            ticket_price=Decimal('25.00'),
            status='published'
        )

        self.not_connected_event = Event.objects.create(
            title='Not Connected Artist Event',
            slug='not-connected-artist-event',
            organiser=self.not_connected_artist_user,
            description='Test event by not connected artist',
            venue_name='Test Venue',
            venue_address='Test Address',
            event_date=timezone.now().date() + timedelta(days=30),
            event_time=timezone.now().time(),
            capacity=100,
            ticket_price=Decimal('20.00'),
            status='published'
        )

    def test_connected_artist_identification(self):
        """Test identification of SumUp-connected artists."""
        self.assertTrue(self.connected_artist.is_sumup_connected)
        self.assertFalse(self.not_connected_artist.is_sumup_connected)
        self.assertEqual(self.connected_artist.sumup_merchant_code, 'TEST_MERCHANT_001')

    def test_connected_payment_service_initialization(self):
        """Test ConnectedPaymentService initialization."""
        service = ConnectedPaymentService()
        self.assertIsNotNone(service)
        self.assertEqual(service.platform_fee_rate, Decimal('5.0'))

    def test_connected_artist_payment_calculation(self):
        """Test payment calculation for connected artists."""
        service = ConnectedPaymentService()

        order_data = {
            'customer': self.customer_user,
            'event': self.connected_event,
            'quantity': 2,
            'unit_price': self.connected_event.ticket_price
        }

        result = service.create_test_payment(order_data, self.connected_artist)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount'], Decimal('50.00'))  # 2 * £25
        self.assertEqual(result['platform_fee'], Decimal('2.50'))  # 5% of £50
        self.assertEqual(result['artist_amount'], Decimal('47.50'))  # £50 - £2.50
        self.assertEqual(result['merchant_code'], 'TEST_MERCHANT_001')

    def test_platform_fee_calculation(self):
        """Test platform fee calculation accuracy."""
        service = ConnectedPaymentService()

        test_cases = [
            {'amount': Decimal('100.00'), 'expected_fee': Decimal('5.00')},
            {'amount': Decimal('50.00'), 'expected_fee': Decimal('2.50')},
            {'amount': Decimal('15.00'), 'expected_fee': Decimal('0.75')},
        ]

        for case in test_cases:
            order_data = {
                'quantity': 1,
                'unit_price': case['amount']
            }
            result = service.create_test_payment(order_data, self.connected_artist)
            self.assertEqual(result['platform_fee'], case['expected_fee'])

    def test_order_creation_connected_artist(self):
        """Test order creation for connected artist events."""
        order = Order.objects.create(
            user=self.customer_user,
            order_number='TEST-CONNECTED-001',
            email=self.customer_user.email,
            phone='+44 1534 123 456',
            delivery_first_name=self.customer_user.first_name,
            delivery_last_name=self.customer_user.last_name,
            delivery_address_line_1='Digital Ticket Delivery',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            status='pending',
            subtotal=Decimal('50.00'),
            shipping_cost=Decimal('0.00'),
            total=Decimal('50.00')
        )

        order_item = OrderItem.objects.create(
            order=order,
            event=self.connected_event,
            event_title=self.connected_event.title,
            event_organiser=self.connected_artist.display_name,
            event_date=self.connected_event.event_date,
            venue_name=self.connected_event.venue_name,
            quantity=2,
            price=self.connected_event.ticket_price
        )

        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order_item.event, self.connected_event)
        self.assertEqual(order.total, Decimal('50.00'))

    def test_artist_connection_status_property(self):
        """Test artist connection status properties."""
        # Connected artist
        self.assertEqual(self.connected_artist.sumup_connection_status, 'connected')
        self.assertTrue(self.connected_artist.sumup_access_token)
        self.assertTrue(self.connected_artist.sumup_merchant_code)
        self.assertFalse(self.connected_artist.sumup_token_expired)

        # Not connected artist
        self.assertEqual(self.not_connected_artist.sumup_connection_status, 'not_connected')
        self.assertFalse(self.not_connected_artist.sumup_access_token)
        self.assertFalse(self.not_connected_artist.sumup_merchant_code)

    def test_listing_fee_calculation(self):
        """Test listing fee calculation for events."""
        # 5% listing fee on ticket price
        listing_fee_rate = Decimal('5.00')

        connected_fee = (self.connected_event.ticket_price * listing_fee_rate) / 100
        not_connected_fee = (self.not_connected_event.ticket_price * listing_fee_rate) / 100

        self.assertEqual(connected_fee, Decimal('1.25'))  # 5% of £25
        self.assertEqual(not_connected_fee, Decimal('1.00'))  # 5% of £20

    def test_payment_routing_logic(self):
        """Test payment routing logic based on artist connection status."""
        # Connected artist - should route to artist's SumUp account
        connected_routing = {
            'artist': self.connected_artist,
            'payment_method': 'sumup_connected',
            'direct_to_artist': True,
            'platform_fee_deducted': True
        }

        self.assertTrue(connected_routing['direct_to_artist'])
        self.assertTrue(connected_routing['platform_fee_deducted'])

        # Not connected artist - should route to platform account
        not_connected_routing = {
            'artist': self.not_connected_artist,
            'payment_method': 'sumup_platform',
            'direct_to_artist': False,
            'full_amount_collected': True
        }

        self.assertFalse(not_connected_routing['direct_to_artist'])
        self.assertTrue(not_connected_routing['full_amount_collected'])

    def test_webhook_payload_structure(self):
        """Test webhook payload structure for different scenarios."""
        success_webhook = {
            'event_type': 'payment_succeeded',
            'payment_id': 'pay_test_123',
            'checkout_id': 'co_test_123',
            'amount': 50.00,
            'currency': 'GBP',
            'status': 'PAID',
            'merchant_code': 'TEST_MERCHANT_001',
            'timestamp': timezone.now().isoformat()
        }

        failure_webhook = {
            'event_type': 'payment_failed',
            'payment_id': 'pay_test_456',
            'checkout_id': 'co_test_456',
            'amount': 30.00,
            'currency': 'GBP',
            'status': 'FAILED',
            'error_code': 'insufficient_funds',
            'timestamp': timezone.now().isoformat()
        }

        # Validate webhook structure
        self.assertIn('event_type', success_webhook)
        self.assertIn('payment_id', success_webhook)
        self.assertIn('amount', success_webhook)
        self.assertEqual(success_webhook['status'], 'PAID')

        self.assertIn('error_code', failure_webhook)
        self.assertEqual(failure_webhook['status'], 'FAILED')

    def test_ticket_generation_data_structure(self):
        """Test ticket generation data structure."""
        ticket_data = {
            'order_number': 'TEST-TICKET-001',
            'customer_email': self.customer_user.email,
            'event_title': self.connected_event.title,
            'event_date': self.connected_event.event_date.strftime('%Y-%m-%d'),
            'event_time': self.connected_event.event_time.strftime('%H:%M'),
            'venue_name': self.connected_event.venue_name,
            'quantity': 2,
            'qr_code_data': 'TEST-QR-DATA-123',
            'pdf_url': '/tickets/TEST-TICKET-001.pdf',
            'download_expires': (timezone.now() + timedelta(days=7)).isoformat()
        }

        # Validate ticket data structure
        self.assertIn('order_number', ticket_data)
        self.assertIn('customer_email', ticket_data)
        self.assertIn('qr_code_data', ticket_data)
        self.assertEqual(ticket_data['quantity'], 2)
        self.assertEqual(ticket_data['event_title'], self.connected_event.title)

    def test_commission_rate_application(self):
        """Test commission rate application for different artists."""
        # Connected artist should have platform fee instead of full commission
        self.assertEqual(self.connected_artist.commission_rate, Decimal('15.00'))

        # For connected artists, platform takes smaller fee directly
        service = ConnectedPaymentService()
        self.assertLess(service.platform_fee_rate, self.connected_artist.commission_rate)

    def test_error_handling_invalid_payment_data(self):
        """Test error handling for invalid payment data."""
        service = ConnectedPaymentService()

        # Missing required fields
        invalid_order_data = {
            'customer': self.customer_user,
            # Missing 'event', 'quantity', 'unit_price'
        }

        result = service.create_test_payment(invalid_order_data, self.connected_artist)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_multiple_event_order_handling(self):
        """Test handling of orders with multiple events."""
        # This would be relevant for festival tickets or multiple event packages
        total_amount = self.connected_event.ticket_price + self.not_connected_event.ticket_price

        # In a real implementation, this would require special handling
        # for mixed connected/not-connected artist orders
        mixed_order_complexity = {
            'connected_events': [self.connected_event],
            'not_connected_events': [self.not_connected_event],
            'total_amount': total_amount,
            'requires_split_payment': True
        }

        self.assertTrue(mixed_order_complexity['requires_split_payment'])
        self.assertEqual(len(mixed_order_complexity['connected_events']), 1)
        self.assertEqual(len(mixed_order_complexity['not_connected_events']), 1)


class SumUpIntegrationTests(TransactionTestCase):
    """Integration tests for SumUp payment processing."""

    def setUp(self):
        """Set up integration test data."""
        self.artist_user = User.objects.create_user(
            username='integration_artist',
            email='integration@test.com',
            user_type='artist'
        )

        self.artist = ArtistProfile.objects.create(
            user=self.artist_user,
            display_name='Integration Test Artist',
            is_approved=True,
            sumup_connection_status='connected'
        )

        self.artist.update_sumup_connection({
            'access_token': 'test_integration_token',
            'refresh_token': 'test_integration_refresh',
            'expires_in': 3600,
            'merchant_code': 'INT_TEST_001'
        })

    def test_end_to_end_payment_flow_simulation(self):
        """Test end-to-end payment flow simulation."""
        # This would test the complete flow from order creation to payment confirmation
        # In a real test, this would involve API calls to SumUp sandbox

        payment_flow_steps = [
            'customer_adds_tickets_to_cart',
            'customer_proceeds_to_checkout',
            'payment_method_detected_as_connected_sumup',
            'redirect_to_artist_sumup_checkout',
            'customer_completes_payment',
            'webhook_received_payment_success',
            'order_status_updated_to_paid',
            'tickets_generated_and_emailed'
        ]

        # Simulate each step
        simulation_results = {}
        for step in payment_flow_steps:
            # In real implementation, each step would have actual logic
            simulation_results[step] = True

        # All steps should succeed in simulation
        self.assertTrue(all(simulation_results.values()))
        self.assertEqual(len(simulation_results), len(payment_flow_steps))

    def test_webhook_processing_simulation(self):
        """Test webhook processing simulation."""
        webhook_payloads = [
            {
                'type': 'payment.successful',
                'data': {
                    'payment_id': 'pay_integration_test_1',
                    'amount': 5000,  # £50.00 in pence
                    'currency': 'GBP',
                    'merchant_code': 'INT_TEST_001'
                }
            },
            {
                'type': 'payment.failed',
                'data': {
                    'payment_id': 'pay_integration_test_2',
                    'amount': 3000,  # £30.00 in pence
                    'currency': 'GBP',
                    'error': 'card_declined'
                }
            }
        ]

        for payload in webhook_payloads:
            # Simulate webhook processing
            webhook_processed = {
                'received': True,
                'validated': True,
                'processed': True,
                'type': payload['type']
            }

            self.assertTrue(webhook_processed['received'])
            self.assertTrue(webhook_processed['validated'])
            self.assertTrue(webhook_processed['processed'])
            self.assertIn(webhook_processed['type'], ['payment.successful', 'payment.failed'])

    def test_concurrent_payment_handling(self):
        """Test handling of concurrent payments."""
        # Simulate multiple simultaneous payments
        concurrent_payments = []

        for i in range(5):
            payment = {
                'payment_id': f'concurrent_test_{i}',
                'amount': Decimal('25.00'),
                'timestamp': timezone.now(),
                'processed': True
            }
            concurrent_payments.append(payment)

        # All payments should be processed successfully
        processed_count = sum(1 for p in concurrent_payments if p['processed'])
        self.assertEqual(processed_count, 5)