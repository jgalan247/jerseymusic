import re

with open('orders/tests/test_forms/test_checkout.py', 'r') as f:
    content = f.read()

# Find the setUp method and add artist/artwork creation
old_setup = '''    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='pass123',
            user_type='customer'
        )
        
        self.order = Order.objects.create('''

new_setup = '''    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='pass123',
            user_type='customer'
        )
        
        # Create artist and artwork for order
        self.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='pass123',
            user_type='artist'
        )
        
        self.order = Order.objects.create('''

content = content.replace(old_setup, new_setup)

# Add imports if needed
if 'from artworks.models import Artwork' not in content:
    content = content.replace(
        'from orders.models import Order, RefundRequest',
        'from orders.models import Order, RefundRequest, OrderItem\nfrom artworks.models import Artwork'
    )

# Add artwork and order item creation after order creation
old_order_end = '''            total=Decimal('105.00')
        )'''

new_order_end = '''            total=Decimal('105.00')
        )
        
        # Create artwork and order item
        artwork = Artwork.objects.create(
            title='Test Artwork',
            slug='test-artwork',
            artist=self.artist,
            description='Test',
            price=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=self.order,
            artwork=artwork,
            quantity=1,
            price=artwork.price
        )'''

content = content.replace(old_order_end, new_order_end)

with open('orders/tests/test_forms/test_checkout.py', 'w') as f:
    f.write(content)

print("Updated test with proper artist and order item setup")
