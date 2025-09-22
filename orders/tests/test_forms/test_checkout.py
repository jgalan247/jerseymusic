"""
Form validation tests for Orders app - Jersey-specific validation
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from orders.forms import (
    CheckoutForm, 
    PaymentMethodForm, 
    OrderStatusForm, 
    RefundRequestForm
)
from orders.models import Order, RefundRequest, OrderItem
from artworks.models import Artwork

User = get_user_model()


class CheckoutFormTest(TestCase):
    """Test checkout form with Jersey-specific validation"""
    
    def test_valid_checkout_form(self):
        """Test valid checkout form with Jersey address"""
        form_data = {
            'customer_email': 'customer@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '+44 7700 900000',
            'shipping_address_line_1': '123 King Street',
            'shipping_address_line_2': 'Flat 2B',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': True,
            'order_notes': 'Please leave with neighbor if not home'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_jersey_postcode_validation(self):
        """Test Jersey postcode format validation (JE[1-5] pattern)"""
        # Valid Jersey postcodes
        valid_postcodes = [
            'JE1 1AA', 'JE2 4UH', 'JE3 9ZZ', 'JE4 5AB', 'JE5 0XX',
            'JE11AA',  # Without space should also work
            'JE2 3WR', 'JE3 6AS'
        ]
        
        for postcode in valid_postcodes:
            form_data = {
                'customer_email': 'test@example.com',
                'customer_name': 'Test User',
                'customer_phone': '07700900000',
                'shipping_address_line_1': 'Test Street',
                'shipping_parish': 'ST_HELIER',
                'shipping_postcode': postcode,
                'billing_same_as_shipping': True
            }
            form = CheckoutForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Postcode {postcode} should be valid")
    
    def test_invalid_jersey_postcodes_rejected(self):
        """Test invalid Jersey postcodes are rejected"""
        invalid_postcodes = [
            'JE6 1AA',  # JE6 doesn't exist (only JE1-5)
            'JE0 1AA',  # JE0 doesn't exist
            'GY1 1AA',  # Guernsey postcode
            'JE2 4U',   # Too short
            'JE2 4UHH', # Too long
            'JE 4UH',   # Missing district number
            # 'JE24UH' removed - now valid without space
            'XX2 4UH',  # Wrong prefix
            '12345',    # US ZIP code
            'INVALID'   # Random text
        ]
        
        for postcode in invalid_postcodes:
            form_data = {
                'customer_email': 'test@example.com',
                'customer_name': 'Test User',
                'customer_phone': '07700900000',
                'shipping_address_line_1': 'Test Street',
                'shipping_parish': 'ST_HELIER',
                'shipping_postcode': postcode,
                'billing_same_as_shipping': True
            }
            form = CheckoutForm(data=form_data)
            self.assertFalse(form.is_valid(), f"Postcode {postcode} should be invalid")
            self.assertIn('shipping_postcode', form.errors)
    
    def test_jersey_parish_choices(self):
        """Test all Jersey parishes are valid choices"""
        valid_parishes = [
            'ST_HELIER', 'ST_SAVIOUR', 'ST_BRELADE', 'ST_CLEMENT',
            'ST_LAWRENCE', 'ST_PETER', 'ST_OUEN', 'GROUVILLE',
            'ST_JOHN', 'ST_MARTIN', 'ST_MARY', 'TRINITY'
        ]
        
        for parish in valid_parishes:
            form_data = {
                'customer_email': 'test@example.com',
                'customer_name': 'Test User',
                'customer_phone': '07700900000',
                'shipping_address_line_1': 'Test Street',
                'shipping_parish': parish,
                'shipping_postcode': 'JE2 4UH',
                'billing_same_as_shipping': True
            }
            form = CheckoutForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Parish {parish} should be valid")
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        form = CheckoutForm(data={})
        self.assertFalse(form.is_valid())
        
        required_fields = [
            'customer_email', 'customer_name', 'customer_phone',
            'shipping_address_line_1', 'shipping_parish', 'shipping_postcode'
        ]
        
        for field in required_fields:
            self.assertIn(field, form.errors, f"{field} should be required")
    
    def test_different_billing_address(self):
        """Test form with different billing address"""
        form_data = {
            'customer_email': 'customer@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '+44 7700 900000',
            'shipping_address_line_1': '123 King Street',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': False,
            'billing_address_line_1': '456 Queen Street',
            'billing_parish': 'ST_BRELADE',
            'billing_postcode': 'JE3 8AB'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_billing_required_when_different(self):
        """Test billing fields required when not same as shipping"""
        form_data = {
            'customer_email': 'customer@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '+44 7700 900000',
            'shipping_address_line_1': '123 King Street',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': False
            # Missing billing address fields
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('billing_address_line_1', form.errors)
        self.assertIn('billing_parish', form.errors)
        self.assertIn('billing_postcode', form.errors)
    
    def test_email_validation(self):
        """Test email field validation"""
        form_data = {
            'customer_email': 'invalid-email',  # Invalid email
            'customer_name': 'John Doe',
            'customer_phone': '07700900000',
            'shipping_address_line_1': 'Test Street',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': True
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('customer_email', form.errors)
    
    def test_clean_copies_shipping_to_billing(self):
        """Test that clean method copies shipping to billing when same"""
        form_data = {
            'customer_email': 'customer@example.com',
            'customer_name': 'John Doe',
            'customer_phone': '07700900000',
            'shipping_address_line_1': '123 King Street',
            'shipping_address_line_2': 'Apt 5',
            'shipping_parish': 'ST_HELIER',
            'shipping_postcode': 'JE2 4UH',
            'billing_same_as_shipping': True
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cleaned = form.cleaned_data
        self.assertEqual(cleaned['billing_address_line_1'], '123 King Street')
        self.assertEqual(cleaned['billing_address_line_2'], 'Apt 5')
        self.assertEqual(cleaned['billing_parish'], 'ST_HELIER')
        self.assertEqual(cleaned['billing_postcode'], 'JE2 4UH')


class PaymentMethodFormTest(TestCase):
    """Test payment method selection form"""
    
    def test_valid_payment_methods(self):
        """Test valid payment method choices"""
        valid_methods = ['sumup_card', 'sumup_paypal']
        
        for method in valid_methods:
            form_data = {
                'payment_method': method,
                'save_payment_method': False
            }
            form = PaymentMethodForm(data=form_data)
            self.assertTrue(form.is_valid())
    
    def test_payment_method_required(self):
        """Test that payment method is required"""
        form = PaymentMethodForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)
    
    def test_save_payment_method_optional(self):
        """Test that save_payment_method is optional"""
        form_data = {
            'payment_method': 'sumup_card'
            # save_payment_method not provided
        }
        form = PaymentMethodForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data['save_payment_method'])


class OrderStatusFormTest(TestCase):
    """Test order status update form for artists"""
    
    def test_valid_status_update(self):
        """Test valid status update form"""
        form_data = {
            'status': 'processing',
            'tracking_number': 'JE123456789',
            'notes': 'Order has been processed and will ship tomorrow',
            'notify_customer': True
        }
        form = OrderStatusForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_status_required(self):
        """Test that status is required"""
        form_data = {
            'notes': 'Some notes'
        }
        form = OrderStatusForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)
    
    def test_valid_status_choices(self):
        """Test all valid status choices"""
        valid_statuses = [
            'processing', 'ready_for_shipping', 'shipped', 
            'delivered', 'cancelled'
        ]
        
        for status in valid_statuses:
            form_data = {'status': status}
            form = OrderStatusForm(data=form_data)
            self.assertTrue(form.is_valid())
    
    def test_optional_fields(self):
        """Test that tracking_number and notes are optional"""
        form_data = {
            'status': 'processing'
            # No tracking_number or notes
        }
        form = OrderStatusForm(data=form_data)
        self.assertTrue(form.is_valid())


class RefundRequestFormTest(TestCase):
    """Test refund request form"""
    
    def setUp(self):
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
        
        self.order = Order.objects.create(
            user=self.customer,
            email='customer@test.com',
            phone='123456',
            delivery_first_name='John',
            delivery_last_name='Doe',
            delivery_address_line_1='Test Street',
            delivery_parish='st_helier',
            delivery_postcode='JE2 4UH',
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('5.00'),
            total=Decimal('105.00')
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
        )
    
    def test_valid_refund_request(self):
        """Test valid refund request form"""
        form_data = {
            'reason': 'damaged',
            'description': 'The artwork arrived with a tear in the canvas'
        }
        form = RefundRequestForm(data=form_data, order=self.order)
        self.assertTrue(form.is_valid())
    
    def test_reason_required(self):
        """Test that reason is required"""
        form_data = {
            'description': 'Some description'
        }
        form = RefundRequestForm(data=form_data, order=self.order)
        self.assertFalse(form.is_valid())
        self.assertIn('reason', form.errors)
    
    def test_description_required(self):
        """Test that description is required"""
        form_data = {
            'reason': 'damaged'
            # No description
        }
        form = RefundRequestForm(data=form_data, order=self.order)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
    
    def test_valid_reason_choices(self):
        """Test all valid refund reason choices"""
        valid_reasons = [
            'damaged', 'not_as_described', 'wrong_item',
            'quality_issue', 'changed_mind', 'other'
        ]
        
        for reason in valid_reasons:
            form_data = {
                'reason': reason,
                'description': 'Test description'
            }
            form = RefundRequestForm(data=form_data, order=self.order)
            self.assertTrue(form.is_valid())
    
    def test_save_creates_refund_request(self):
        """Test that save creates a RefundRequest with order"""
        form_data = {
            'reason': 'damaged',
            'description': 'Artwork was damaged during shipping'
        }
        form = RefundRequestForm(data=form_data, order=self.order)
        self.assertTrue(form.is_valid())
        
        # Note: save() implementation depends on your form
        # This test assumes the form properly implements save()
        refund_request = form.save()
        self.assertEqual(refund_request.order, self.order)
        self.assertEqual(refund_request.customer, self.order.user)
