from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from orders.models import Order

User = get_user_model()


class OrderModelTest(TestCase):
    
    def test_order_creation(self):
        """Test basic order creation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        order = Order.objects.create(
            user=user,
            email='test@example.com',
            phone='123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='123 Test St',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('105.00')
        )
        
        self.assertIsNotNone(order.order_number)
        self.assertEqual(order.total, Decimal('105.00'))

    def test_order_number_unique(self):
        """Test that order numbers are unique"""
        user = User.objects.create_user(username='test2', email='test2@example.com')
        
        order1 = Order.objects.create(
            user=user,
            email='test@example.com',
            phone='123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='Street',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('50.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('55.00')
        )
        
        order2 = Order.objects.create(
            user=user,
            email='test@example.com',
            phone='123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='Street',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('50.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('55.00')
        )
        
        self.assertNotEqual(order1.order_number, order2.order_number)
        
    def test_can_cancel_property(self):
        """Test can_cancel for different statuses"""
        user = User.objects.create_user(username='test3', email='test3@example.com')
        order = Order.objects.create(
            user=user,
            email='test@example.com',
            phone='123',
            delivery_first_name='T',
            delivery_last_name='U',
            delivery_address_line_1='St',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('105.00')
        )
        
        # Should be cancellable when pending
        order.status = 'pending'
        self.assertTrue(order.can_cancel)
        
        # Should not be cancellable when delivered
        order.status = 'delivered'
        self.assertFalse(order.can_cancel)
