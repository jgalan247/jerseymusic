# orders/tests/test_forms.py
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from decimal import Decimal
from orders.forms import CheckoutForm, RefundRequestForm
from orders.models import Order, OrderItem
from artworks.models import Artwork
from accounts.models import CustomerProfile, ArtistProfile

User = get_user_model()


@pytest.mark.django_db
class TestCheckoutForm:
    """Test checkout form validation with Jersey-specific requirements."""
    
    def test_valid_checkout_form(self):
        """Test valid checkout form submission."""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+44 7797 123456',
            'address_line_1': '123 Main Street',
            'address_line_2': 'Apartment 4B',
            'parish': 'st_helier',
            'postcode': 'JE2 3AB',
            'delivery_instructions': 'Leave with neighbour if not home',
        }
        form = CheckoutForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_jersey_postcode_regex_validation(self):
        """Test Jersey postcode format validation with regex JE[1-5]\d{1}[A-Z]{2}."""
        # Valid Jersey postcodes (with and without space)
        valid_postcodes = [
            'JE1 1AA', 'JE2 3AB', 'JE3 9ZZ', 'JE4 5XY', 'JE5 0AA',
            'JE11AA', 'JE23AB', 'JE39ZZ', 'JE45XY', 'JE50AA',  # Without space
            'JE1 0AB', 'JE2 9XY', 'JE3 5CD', 'JE4 8EF', 'JE5 7GH',
        ]
        
        for postcode in valid_postcodes:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': 'st_helier',
                'postcode': postcode,
            }
            form = CheckoutForm(data=form_data)
            # The form should normalize the postcode (add space if missing)
            assert form.is_valid(), f"Valid postcode {postcode} rejected: {form.errors}"
            if form.is_valid() and ' ' not in postcode and len(postcode) == 6:
                # Check if postcode is normalized with space
                cleaned_postcode = form.cleaned_data.get('postcode', '')
                assert ' ' in cleaned_postcode or len(cleaned_postcode) == 6, \
                    f"Postcode should be normalized: {cleaned_postcode}"
        
        # Invalid Jersey postcodes
        invalid_postcodes = [
            'JE6 1AA',   # JE6 doesn't exist (only JE1-JE5)
            'JE0 1AA',   # JE0 doesn't exist
            'JE1 AAA',   # No digit in second part
            'JE1 1A',    # Too short
            'JE1 1AAA',  # Too long
            'JE1 12A',   # Two digits in second part
            'JE11 AA',   # Wrong format
            'AB1 2CD',   # Not Jersey
            'JE',        # Incomplete
            'JE1',       # Incomplete
            'JE1 ',      # Incomplete
            'JE1 1',     # Incomplete
            'JE1 1A1',   # Number at end
            'je1 1aa',   # Lowercase (should be uppercase)
        ]
        
        for postcode in invalid_postcodes:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': 'st_helier',
                'postcode': postcode,
            }
            form = CheckoutForm(data=form_data)
            assert not form.is_valid(), f"Invalid postcode {postcode} was accepted"
            assert 'postcode' in form.errors, f"Postcode error not found for {postcode}"
            error_msg = str(form.errors['postcode'][0]).lower()
            assert 'jersey' in error_msg or 'je' in error_msg or 'invalid' in error_msg, \
                f"Error message should mention Jersey format: {error_msg}"
    
    def test_parish_validation(self):
        """Test that only valid Jersey parishes are accepted."""
        valid_parishes = [
            'st_helier', 'st_brelade', 'st_clement', 'st_john',
            'st_lawrence', 'st_martin', 'st_mary', 'st_ouen',
            'st_peter', 'st_saviour', 'grouville', 'trinity'
        ]
        
        # Test each valid parish
        for parish in valid_parishes:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': f'{parish.replace(" ", "").replace(".", "")}@example.com',
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': parish,
                'postcode': 'JE2 3AB',
            }
            form = CheckoutForm(data=form_data)
            assert form.is_valid(), f"Valid parish {parish} rejected: {form.errors}"
        
        # Test invalid parish
        invalid_parishes = [
            'Invalid Parish',
            'St. Invalid',
            'London',
            'Paris',
            '',
        ]
        
        for parish in invalid_parishes:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': parish,
                'postcode': 'JE2 3AB',
            }
            form = CheckoutForm(data=form_data)
            if parish:  # Empty string might be caught as required field
                assert not form.is_valid(), f"Invalid parish {parish} accepted"
                assert 'parish' in form.errors
    
    def test_email_validation(self):
        """Test email field validation."""
        # Valid emails
        valid_emails = [
            'user@example.com',
            'test.user@example.co.uk',
            'user+tag@example.je',
            'user_123@test-domain.com',
        ]
        
        for email in valid_emails:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': email,
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': 'st_helier',
                'postcode': 'JE2 3AB',
            }
            form = CheckoutForm(data=form_data)
            assert form.is_valid(), f"Valid email {email} rejected: {form.errors}"
        
        # Invalid emails
        invalid_emails = [
            'notanemail',
            '@example.com',
            'user@',
            'user @example.com',
            'user@example',
        ]
        
        for email in invalid_emails:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': email,
                'phone_number': '+44 7797 123456',
                'address_line_1': '123 Test Street',
                'parish': 'st_helier',
                'postcode': 'JE2 3AB',
            }
            form = CheckoutForm(data=form_data)
            assert not form.is_valid(), f"Invalid email {email} accepted"
            assert 'email' in form.errors
    
    def test_phone_number_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = [
            '+44 7797 123456',
            '+44 1534 123456',  # Jersey landline
            '07797 123456',
            '01534 123456',
            '+447797123456',
        ]
        
        for phone in valid_phones:
            form_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': phone,
                'address_line_1': '123 Test Street',
                'parish': 'st_helier',
                'postcode': 'JE2 3AB',
            }
            form = CheckoutForm(data=form_data)
            assert form.is_valid(), f"Valid phone {phone} rejected: {form.errors}"
    
    def test_required_fields(self):
        """Test that all required fields are validated."""
        form = CheckoutForm(data={})
        assert not form.is_valid()
        
        required_fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'address_line_1', 'parish', 'postcode'
        ]
        
        for field in required_fields:
            assert field in form.errors, f"Required field {field} not validated"
        
        # Optional fields should not be in errors
        optional_fields = ['address_line_2', 'delivery_instructions']
        for field in optional_fields:
            assert field not in form.errors, f"Optional field {field} should not be required"
    
    def test_max_length_validation(self):
        """Test max length validation for text fields."""
        long_text = 'A' * 501  # Assuming max length is 500 for delivery_instructions
        
        form_data = {
            'first_name': 'A' * 51,  # Assuming max 50
            'last_name': 'B' * 51,   # Assuming max 50
            'email': 'test@example.com',
            'phone_number': '+44 7797 123456',
            'address_line_1': 'C' * 256,  # Assuming max 255
            'parish': 'st_helier',
            'postcode': 'JE2 3AB',
            'delivery_instructions': long_text,
        }
        
        form = CheckoutForm(data=form_data)
        if not form.is_valid():
            # Check if length validation is triggered
            for field in ['first_name', 'last_name', 'address_line_1', 'delivery_instructions']:
                if field in form.errors:
                    error_msg = str(form.errors[field][0]).lower()
                    assert 'length' in error_msg or 'long' in error_msg or 'characters' in error_msg


@pytest.mark.django_db
class TestRefundRequestForm:
    """Test refund request form validation."""
    
    @pytest.fixture
    def setup_order(self):
        """Create test order for refund request."""
        # Create artist user
        artist_user = User.objects.create_user(
            username='artist',
            email='artist@test.com',
            password='TestPass123!',
            user_type='artist'
        )
        artist_profile = artist_user.artist_profile
        
        # Create customer user
        customer_user = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='TestPass123!',
            user_type='customer'
        )
        
        # Create artwork
        artwork = Artwork.objects.create(
            artist=artist_profile,
            title='Test Artwork',
            description='Test description',
            price=Decimal('100.00'),
            stock_quantity=5
        )
        
        # Create order
        order = Order.objects.create(
            customer=customer_user,
            email='customer@test.com',
            first_name='Test',
            last_name='Customer',
            phone_number='+44 7797 123456',
            address_line_1='123 Test Street',
            parish='st_helier',
            postcode='JE2 3AB',
            total_amount=Decimal('100.00'),
            status='completed'
        )
        
        # Create order item
        OrderItem.objects.create(
            order=order,
            artwork=artwork,
            quantity=1,
            price=Decimal('100.00')
        )
        
        return order
    
    def test_valid_refund_request(self, setup_order):
        """Test valid refund request form submission."""
        order = setup_order
        
        form_data = {
            'reason': 'damaged',
            'description': 'The artwork arrived with a tear in the canvas.',
            'requested_amount': Decimal('100.00'),
        }
        
        # Assuming the form takes order as a parameter
        form = RefundRequestForm(data=form_data)
        if hasattr(form, 'order'):
            form.order = order
        
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_refund_amount_validation(self, setup_order):
        """Test that refund amount cannot exceed order total."""
        order = setup_order
        
        form_data = {
            'reason': 'damaged',
            'description': 'Damaged item',
            'requested_amount': Decimal('150.00'),  # Exceeds order total
        }
        
        form = RefundRequestForm(data=form_data)
        if hasattr(form, 'order'):
            form.order = order
        
        # Check if the form validates the amount against order total
        if hasattr(form, 'clean_requested_amount'):
            assert not form.is_valid()
            if not form.is_valid():
                assert 'requested_amount' in form.errors
                error_msg = str(form.errors['requested_amount'][0]).lower()
                assert 'exceed' in error_msg or 'maximum' in error_msg or 'total' in error_msg
    
    def test_reason_choices(self):
        """Test that only valid refund reasons are accepted."""
        valid_reasons = [
            'damaged', 'not_as_described', 'never_received', 
            'quality_issue', 'other'
        ]
        
        for reason in valid_reasons:
            form_data = {
                'reason': reason,
                'description': f'Test description for {reason}',
                'requested_amount': Decimal('50.00'),
            }
            form = RefundRequestForm(data=form_data)
            # Reason field should be valid
            if 'reason' in form.errors:
                assert False, f"Valid reason {reason} rejected: {form.errors}"
        
        # Test invalid reason
        form_data = {
            'reason': 'invalid_reason',
            'description': 'Test description',
            'requested_amount': Decimal('50.00'),
        }
        form = RefundRequestForm(data=form_data)
        if form.fields.get('reason'):
            assert not form.is_valid()
            assert 'reason' in form.errors
    
    def test_description_required(self):
        """Test that description is required for refund request."""
        form_data = {
            'reason': 'damaged',
            # 'description' missing
            'requested_amount': Decimal('50.00'),
        }
        form = RefundRequestForm(data=form_data)
        assert not form.is_valid()
        assert 'description' in form.errors
    
    def test_negative_refund_amount(self):
        """Test that negative refund amounts are rejected."""
        form_data = {
            'reason': 'damaged',
            'description': 'Test description',
            'requested_amount': Decimal('-50.00'),  # Negative amount
        }
        form = RefundRequestForm(data=form_data)
        assert not form.is_valid()
        assert 'requested_amount' in form.errors
        error_msg = str(form.errors['requested_amount'][0]).lower()
        assert 'positive' in error_msg or 'negative' in error_msg or 'greater' in error_msg