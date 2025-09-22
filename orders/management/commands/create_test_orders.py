# orders/management/commands/create_test_orders.py
# Create this directory structure: orders/management/commands/

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from artworks.models import Artwork
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test orders with different payment statuses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user to create orders for',
            default='test@example.com'
        )

    def handle(self, *args, **options):
        user_email = options['user_email']
        
        # Get or create test user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stdout.write(f"Creating test user: {user_email}")
            user = User.objects.create_user(
                email=user_email,
                password='testpass123',
                first_name='Test',
                last_name='User'
            )

        # Get some artworks (create dummy ones if none exist)
        artworks = list(Artwork.objects.all()[:3])
        if not artworks:
            self.stdout.write("No artworks found. Please create some artworks first.")
            return

        # Test order scenarios - Note: 'payment_failed' doesn't exist in your model choices
        # Using 'cancelled' instead which is close to a failed payment scenario
        test_orders = [
            {
                'status': 'confirmed',
                'is_paid': True,
                'description': 'Successful payment - confirmed order'
            },
            {
                'status': 'pending',
                'is_paid': False,
                'description': 'Pending payment - should be excluded from customer list'
            },
            {
                'status': 'cancelled',
                'is_paid': False,
                'description': 'Cancelled order (similar to failed payment)'
            },
            {
                'status': 'processing',
                'is_paid': True,
                'description': 'Processing order (paid)'
            },
            {
                'status': 'shipped',
                'is_paid': True,
                'description': 'Shipped order'
            },
            {
                'status': 'delivered',
                'is_paid': True,
                'description': 'Delivered order'
            },
        ]

        created_orders = []

        for i, order_data in enumerate(test_orders):
            # Create order using correct field names from your model
            order = Order.objects.create(
                user=user,
                order_number=f"TEST-{uuid.uuid4().hex[:8].upper()}",
                email=user.email,  # Using 'email' field from your model
                phone="+44 7123 456789",
                delivery_first_name=user.first_name,  # Using correct field name
                delivery_last_name=user.last_name,    # Using correct field name
                delivery_address_line_1="123 Test Street",
                delivery_parish="st_helier",  # Using one of your parish choices
                delivery_postcode="JE1 1AA",
                status=order_data['status'],
                is_paid=order_data['is_paid'],
                subtotal=Decimal('25.00'),
                shipping_cost=Decimal('5.00'),
                tax_amount=Decimal('0.00'),  # Using 'tax_amount' field name
                total=Decimal('30.00'),
                created_at=timezone.now() - timedelta(days=i)  # Spread orders over days
            )

            # Add order items
            for j, artwork in enumerate(artworks[:2]):  # Add 2 items per order
                price = Decimal('15.00') + (j * Decimal('10.00'))
                quantity = 1

                OrderItem.objects.create(
                    order=order,
                    artwork=artwork,
                    quantity=quantity,
                    price=price,
                    total=price * quantity,  # total will be calculated in save() method
                    artwork_title=artwork.title,
                    artwork_artist=artwork.artist.get_full_name() if artwork.artist else 'Unknown Artist',
                    artwork_type=artwork.artwork_type if hasattr(artwork, 'artwork_type') else 'unknown'
                )

            created_orders.append(order)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created order {order.order_number}: {order_data['description']}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCreated {len(created_orders)} test orders for {user.email}"
            )
        )
        
        self.stdout.write("\nOrder Summary:")
        self.stdout.write("- Pending orders should NOT appear in customer list")
        self.stdout.write("- Cancelled orders SHOULD appear in customer list")
        self.stdout.write("- All other paid orders SHOULD appear in customer list")
        
        self.stdout.write(f"\nTest the customer order list at: http://localhost:8000/orders/my-orders/")
        self.stdout.write(f"Login with: {user_email} / testpass123")