from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from orders.models import Order
from decimal import Decimal

User = get_user_model()

class PDFInvoiceTest(TestCase):
    def test_invoice_requires_ownership(self):
        """Test only order owner can download invoice"""
        # Create test data
        customer = User.objects.create_user('customer@test.com', 'customer@test.com', 'pass123')
        other_user = User.objects.create_user('other@test.com', 'other@test.com', 'pass123')
        
        order = Order.objects.create(
            user=customer,
            email='customer@test.com',
            phone='123',
            delivery_first_name='Test',
            delivery_last_name='User',
            delivery_address_line_1='Street',
            delivery_parish='st_helier',
            delivery_postcode='JE1 1AA',
            subtotal=Decimal('100'),
            shipping_cost=Decimal('5'),
            total=Decimal('105')
        )
        
        # Other user shouldn't access
        self.client.login(username='other@test.com', password='pass123')
        response = self.client.get(reverse('orders:download_invoice', args=[order.order_number]))
        self.assertEqual(response.status_code, 404)
        
        # Owner should access
        self.client.login(username='customer@test.com', password='pass123')
        response = self.client.get(reverse('orders:download_invoice', args=[order.order_number]))
        self.assertEqual(response.status_code, 200)
