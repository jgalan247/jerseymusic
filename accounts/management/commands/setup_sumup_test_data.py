"""Management command to create comprehensive test data for SumUp payment flows."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from accounts.models import ArtistProfile
from events.models import Event, Ticket
from orders.models import Order, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Create comprehensive test data for SumUp payment flow testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up existing test data first',
        )
        parser.add_argument(
            '--artists',
            type=int,
            default=3,
            help='Number of test artists to create (default: 3)',
        )
        parser.add_argument(
            '--events-per-artist',
            type=int,
            default=2,
            help='Number of events per artist (default: 2)',
        )

    def print_success(self, message):
        self.stdout.write(self.style.SUCCESS(f"✅ {message}"))

    def print_info(self, message):
        self.stdout.write(f"📊 {message}")

    def print_warning(self, message):
        self.stdout.write(self.style.WARNING(f"⚠️ {message}"))

    def cleanup_test_data(self):
        """Clean up existing test data."""
        self.print_info("Cleaning up existing test data...")

        # Delete test users and related data
        test_users = User.objects.filter(username__startswith='test_artist_')
        test_customer_users = User.objects.filter(username__startswith='test_customer_')

        orders_deleted = Order.objects.filter(user__in=test_customer_users).count()
        events_deleted = Event.objects.filter(organiser__in=test_users).count()

        # Delete in correct order (foreign key constraints)
        Order.objects.filter(user__in=test_customer_users).delete()
        Event.objects.filter(organiser__in=test_users).delete()
        test_customer_users.delete()
        test_users.delete()

        self.print_success(f"Cleanup complete:")
        self.stdout.write(f"  - Orders: {orders_deleted}")
        self.stdout.write(f"  - Events: {events_deleted}")
        self.stdout.write(f"  - Artists: {len(test_users)}")
        self.stdout.write(f"  - Customers: {len(test_customer_users)}")

    def get_test_venues(self):
        """Get test venue data (as text, not model objects)."""
        self.print_info("Preparing test venue data...")

        venues = [
            {
                'name': 'Test Venue - The Electric Hall',
                'address': '123 Music Street\nSt. Helier, Jersey JE1 1AA',
                'capacity': 500,
                'description': 'Premier music venue with state-of-the-art sound system'
            },
            {
                'name': 'Test Venue - Jersey Arts Centre',
                'address': '456 Performance Ave\nSt. Brelade, Jersey JE3 8BB',
                'capacity': 200,
                'description': 'Intimate venue perfect for acoustic performances'
            },
            {
                'name': 'Test Venue - Liberation Station',
                'address': '789 Freedom Plaza\nSt. Peter, Jersey JE2 7CC',
                'capacity': 1000,
                'description': 'Large outdoor venue for festivals and concerts'
            }
        ]

        for venue in venues:
            self.print_success(f"Venue data prepared: {venue['name']}")

        return venues

    def create_test_artists(self, num_artists):
        """Create test artists with different SumUp connection statuses."""
        self.print_info(f"Creating {num_artists} test artists...")

        artists = []
        connection_statuses = ['connected', 'not_connected', 'connected']  # Mix of statuses

        for i in range(num_artists):
            # Create user
            username = f'test_artist_{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@testartist.com',
                    'first_name': f'Test Artist {i+1}',
                    'last_name': 'Performer',
                    'user_type': 'artist',
                    'is_active': True,
                }
            )

            if created:
                user.set_password('testpass123')
                user.save()

            # Create artist profile
            status = connection_statuses[i % len(connection_statuses)]
            artist, created = ArtistProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': f'Test Artist {i+1}',
                    'bio': f'Professional test artist #{i+1} specializing in various musical genres',
                    'business_name': f'Test Artist {i+1} Music',
                    'is_approved': True,
                    'sumup_connection_status': status,
                }
            )

            # Set up SumUp connection data for connected artists
            if status == 'connected' and created:
                artist.update_sumup_connection({
                    'access_token': f'test_access_token_{i+1}_{uuid.uuid4().hex[:8]}',
                    'refresh_token': f'test_refresh_token_{i+1}_{uuid.uuid4().hex[:8]}',
                    'expires_in': 3600,
                    'scope': 'payments',
                    'merchant_code': f'TEST_MERCHANT_{i+1:02d}'
                })
                artist.save()

            artists.append(artist)

            if created:
                connection_emoji = "🔗" if status == 'connected' else "❌"
                self.print_success(f"Created artist: {artist.display_name} {connection_emoji}")

        return artists

    def create_test_events(self, artists, venues, events_per_artist):
        """Create test events for artists."""
        self.print_info(f"Creating {events_per_artist} events per artist...")

        events = []
        event_templates = [
            {
                'title': 'Summer Concert Series',
                'description': 'An amazing summer evening of live music featuring local and international artists',
                'base_price': Decimal('25.00')
            },
            {
                'title': 'Acoustic Unplugged',
                'description': 'Intimate acoustic performance in a cozy venue setting',
                'base_price': Decimal('15.00')
            },
            {
                'title': 'Electronic Dance Night',
                'description': 'High-energy electronic music event with top DJs',
                'base_price': Decimal('35.00')
            },
            {
                'title': 'Jazz & Blues Evening',
                'description': 'Smooth jazz and soulful blues performed by talented musicians',
                'base_price': Decimal('30.00')
            }
        ]

        for artist in artists:
            for event_num in range(events_per_artist):
                template = event_templates[event_num % len(event_templates)]
                venue = venues[event_num % len(venues)]

                # Create event dates in the future
                event_date = timezone.now().date() + timedelta(days=30 + event_num * 14)
                event_time = timezone.now().time().replace(hour=19, minute=30)  # 7:30 PM

                event_title = f"{template['title']} - {artist.display_name}"
                event_slug = f"test-{slugify(event_title)}-{event_num}"

                event, created = Event.objects.get_or_create(
                    title=event_title,
                    slug=event_slug,
                    defaults={
                        'organiser': artist.user,  # Use the User object, not ArtistProfile
                        'description': template['description'],
                        'venue_name': venue['name'],
                        'venue_address': venue['address'],
                        'event_date': event_date,
                        'event_time': event_time,
                        'capacity': venue['capacity'] // 2,  # Half venue capacity
                        'ticket_price': template['base_price'],
                        'status': 'published',
                        'featured': event_num == 0,  # First event is featured
                        'is_local_organiser': True,
                        'jersey_heritage': event_num % 2 == 0,  # Alternate heritage status
                    }
                )

                events.append(event)

                if created:
                    connection_status = "🔗" if artist.is_sumup_connected else "❌"
                    self.print_success(f"Created event: {event_title} {connection_status}")

        return events

    def create_test_customers(self):
        """Create test customer accounts."""
        self.print_info("Creating test customer accounts...")

        customers = []
        for i in range(5):
            username = f'test_customer_{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@testcustomer.com',
                    'first_name': f'Customer {i+1}',
                    'last_name': 'Tester',
                    'user_type': 'customer',
                    'is_active': True,
                }
            )

            if created:
                user.set_password('testpass123')
                user.save()

            customers.append(user)

            if created:
                self.print_success(f"Created customer: {user.get_full_name()}")

        return customers

    def create_sample_orders(self, events, customers):
        """Create sample test orders (without payment processing)."""
        self.print_info("Creating sample test orders...")

        orders = []
        order_statuses = ['pending', 'confirmed', 'cancelled']

        for i, event in enumerate(events[:3]):  # Create orders for first 3 events
            customer = customers[i % len(customers)]
            status = order_statuses[i % len(order_statuses)]
            quantity = 2
            item_price = event.ticket_price
            subtotal = item_price * quantity
            shipping_cost = Decimal('0.00')  # Digital tickets
            total = subtotal + shipping_cost

            order = Order.objects.create(
                user=customer,
                order_number=f'TEST-{uuid.uuid4().hex[:8].upper()}',
                email=customer.email,
                phone='+44 1534 123 456',
                # Delivery info (required but not used for digital tickets)
                delivery_first_name=customer.first_name,
                delivery_last_name=customer.last_name,
                delivery_address_line_1='Digital Ticket Delivery',
                delivery_parish='st_helier',
                delivery_postcode='JE1 1AA',
                # Order totals
                status=status,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                total=total,
                # Payment info
                payment_method='test_payment' if status == 'confirmed' else '',
                is_paid=status == 'confirmed',
                paid_at=timezone.now() - timedelta(days=i) if status == 'confirmed' else None,
            )

            # Add order items
            OrderItem.objects.create(
                order=order,
                event=event,
                event_title=event.title,
                event_organiser=event.organiser.get_full_name(),
                event_date=event.event_date,
                venue_name=event.venue_name,
                quantity=quantity,
                price=item_price
            )

            orders.append(order)
            self.print_success(f"Created test order: {order.order_number} ({status})")

        return orders

    def generate_summary_report(self, artists, events, customers, venues):
        """Generate a comprehensive summary report."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO("🎯 TEST DATA SETUP COMPLETE"))
        self.stdout.write("="*60)

        # Artist summary
        connected_artists = [a for a in artists if a.is_sumup_connected]
        not_connected_artists = [a for a in artists if not a.is_sumup_connected]

        self.print_info("Test Artists Created:")
        self.stdout.write(f"  📊 Total Artists: {len(artists)}")
        self.stdout.write(f"  🔗 Connected to SumUp: {len(connected_artists)}")
        self.stdout.write(f"  ❌ Not Connected: {len(not_connected_artists)}")

        for artist in artists:
            connection_status = "🔗 Connected" if artist.is_sumup_connected else "❌ Not Connected"
            merchant_code = f" (Merchant: {artist.sumup_merchant_code})" if artist.sumup_merchant_code else ""
            self.stdout.write(f"    - {artist.display_name}: {connection_status}{merchant_code}")

        # Event summary
        self.print_info("Test Events Created:")
        self.stdout.write(f"  📊 Total Events: {len(events)}")

        # Get artist profiles for event organisers
        connected_events = []
        not_connected_events = []

        for event in events:
            try:
                artist_profile = ArtistProfile.objects.get(user=event.organiser)
                if artist_profile.is_sumup_connected:
                    connected_events.append(event)
                else:
                    not_connected_events.append(event)
            except ArtistProfile.DoesNotExist:
                not_connected_events.append(event)

        self.stdout.write(f"  🔗 Events with Connected Artists: {len(connected_events)}")
        self.stdout.write(f"  ❌ Events with Non-Connected Artists: {len(not_connected_events)}")

        # Customer summary
        self.print_info("Test Customers Created:")
        self.stdout.write(f"  📊 Total Customers: {len(customers)}")

        # Venue summary
        self.print_info("Test Venues Created:")
        self.stdout.write(f"  📊 Total Venues: {len(venues)}")

        # Testing instructions
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO("🧪 TESTING INSTRUCTIONS"))
        self.stdout.write("="*60)

        self.print_info("Login Credentials:")
        for i, artist in enumerate(artists[:3]):
            self.stdout.write(f"  Artist {i+1}: test_artist_{i+1} / testpass123")
        for i in range(3):
            self.stdout.write(f"  Customer {i+1}: test_customer_{i+1} / testpass123")

        self.print_info("Test Scenarios:")
        self.stdout.write("  1. 🔗 Purchase tickets from connected artist (direct SumUp payment)")
        self.stdout.write("  2. ❌ Purchase tickets from non-connected artist (platform payment)")
        self.stdout.write("  3. 💰 Verify listing fee collection for connected artists")
        self.stdout.write("  4. 📧 Test ticket generation and email delivery")
        self.stdout.write("  5. 🔄 Test webhook handling and transaction logging")

        self.print_info("Next Steps:")
        self.stdout.write("  1. Run: python manage.py setup_sumup_sandbox")
        self.stdout.write("  2. Configure SumUp sandbox credentials in .env")
        self.stdout.write("  3. Start test server: python manage.py runserver")
        self.stdout.write("  4. Navigate to /accounts/dashboard/ and test payment flows")

        self.stdout.write("="*60)

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(self.style.HTTP_INFO("🧪 Setting up comprehensive SumUp payment test data"))
        self.stdout.write(f"Timestamp: {timezone.now()}")

        # Cleanup if requested
        if options['cleanup']:
            self.cleanup_test_data()

        # Create test data
        venues = self.get_test_venues()
        artists = self.create_test_artists(options['artists'])
        events = self.create_test_events(artists, venues, options['events_per_artist'])
        customers = self.create_test_customers()
        orders = self.create_sample_orders(events, customers)

        # Generate summary
        self.generate_summary_report(artists, events, customers, venues)

        self.print_success("Test data setup completed successfully!")
        return f"Created {len(artists)} artists, {len(events)} events, {len(customers)} customers"