from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from orders.models import Order
from decimal import Decimal

User = get_user_model()

class CustomerOrderViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='pass123',
            user_type='customer'
        )
        
    def test_customer_cannot_see_pending_orders(self):
        """Test customers don't see pending orders in list"""
        # Create orders with different statuses
        Order.objects.create(
            user=self.customer,
            status='pending',
            email='test@test.com',
            phone='123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='St',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('100'),
            shipping_cost=Decimal('5'),
            total=Decimal('105')
        )
        
        confirmed_order = Order.objects.create(
            user=self.customer,
            status='confirmed',
            email='test@test.com',
            phone='123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='St',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('100'),
            shipping_cost=Decimal('5'),
            total=Decimal('105')
        )
        
        self.client.login(username='customer@test.com', password='pass123')
        response = self.client.get(reverse('orders:my_orders'))
        
        # Should only see confirmed order, not pending
        self.assertContains(response, confirmed_order.order_number)
        self.assertEqual(len(response.context['orders']), 1)
