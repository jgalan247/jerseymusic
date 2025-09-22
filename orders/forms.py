# orders/forms.py

from django import forms
from django.core.validators import RegexValidator
from .models import Order, OrderItem, RefundRequest

# Jersey parishes for address selection
JERSEY_PARISHES = [
    ('', 'Select Parish'),
    ('ST_HELIER', 'St. Helier'),
    ('ST_SAVIOUR', 'St. Saviour'),
    ('ST_BRELADE', 'St. Brelade'),
    ('ST_CLEMENT', 'St. Clement'),
    ('ST_LAWRENCE', 'St. Lawrence'),
    ('ST_PETER', 'St. Peter'),
    ('ST_OUEN', 'St. Ouen'),
    ('GROUVILLE', 'Grouville'),
    ('ST_JOHN', 'St. John'),
    ('ST_MARTIN', 'St. Martin'),
    ('ST_MARY', 'St. Mary'),
    ('TRINITY', 'Trinity'),
]

# Jersey postcode validator
jersey_postcode_validator = RegexValidator(
    regex=r'^JE[1-5](\s)?\d[A-Z]{2}$',
    message='Please enter a valid Jersey postcode (e.g., JE2 4UH)'
)


class CheckoutForm(forms.ModelForm):
    """Form for customer checkout with Jersey-specific fields"""
    
    # Customer Information
    customer_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'required': True
        })
    )
    customer_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name',
            'required': True
        })
    )
    customer_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number',
            'required': True
        })
    )
    
    # Shipping Address
    shipping_address_line_1 = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 1',
            'required': True
        })
    )
    shipping_address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 2 (Optional)'
        })
    )
    shipping_parish = forms.ChoiceField(
        choices=JERSEY_PARISHES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )
    shipping_postcode = forms.CharField(
        max_length=8,
        validators=[jersey_postcode_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'JE1 1AA',
            'required': True
        })
    )
    
    # Billing Address (optional - same as shipping by default)
    billing_same_as_shipping = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'checked': True
        })
    )
    billing_address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Billing Address Line 1'
        })
    )
    billing_address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Billing Address Line 2 (Optional)'
        })
    )
    billing_parish = forms.ChoiceField(
        choices=JERSEY_PARISHES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    billing_postcode = forms.CharField(
        max_length=8,
        required=False,
        validators=[jersey_postcode_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'JE1 1AA'
        })
    )
    
    # Additional Information
    order_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Special delivery instructions or notes (Optional)',
            'rows': 3
        })
    )
    
    class Meta:
        model = Order
        fields = [
            'customer_email', 'customer_name', 'customer_phone',
            'shipping_address_line_1', 'shipping_address_line_2',
            'shipping_parish', 'shipping_postcode',
            'billing_same_as_shipping',
            'billing_address_line_1', 'billing_address_line_2',
            'billing_parish', 'billing_postcode',
            'order_notes'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        billing_same = cleaned_data.get('billing_same_as_shipping')
        
        if not billing_same:
            # If billing address is different, make fields required
            if not cleaned_data.get('billing_address_line_1'):
                self.add_error('billing_address_line_1', 'Billing address is required')
            if not cleaned_data.get('billing_parish'):
                self.add_error('billing_parish', 'Billing parish is required')
            if not cleaned_data.get('billing_postcode'):
                self.add_error('billing_postcode', 'Billing postcode is required')
        else:
            # Copy shipping to billing
            cleaned_data['billing_address_line_1'] = cleaned_data.get('shipping_address_line_1')
            cleaned_data['billing_address_line_2'] = cleaned_data.get('shipping_address_line_2')
            cleaned_data['billing_parish'] = cleaned_data.get('shipping_parish')
            cleaned_data['billing_postcode'] = cleaned_data.get('shipping_postcode')
        
        return cleaned_data


class PaymentMethodForm(forms.Form):
    """Form for selecting payment method"""
    PAYMENT_CHOICES = [
        ('sumup_card', 'Card Payment (via SumUp)'),
        ('sumup_paypal', 'PayPal (via SumUp)'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    save_payment_method = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Save this payment method for future purchases'
    )


class OrderStatusForm(forms.Form):
    """Form for artists to update order status"""
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('ready_for_shipping', 'Ready for Shipping'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    tracking_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tracking number (if applicable)'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Additional notes about this status update',
            'rows': 3
        })
    )
    
    notify_customer = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Send email notification to customer'
    )


class RefundRequestForm(forms.ModelForm):
    """Form for customers to request refunds"""
    REASON_CHOICES = [
        ('damaged', 'Item arrived damaged'),
        ('not_as_described', 'Item not as described'),
        ('wrong_item', 'Wrong item received'),
        ('quality_issue', 'Quality not satisfactory'),
        ('changed_mind', 'Changed my mind'),
        ('other', 'Other reason'),
    ]
    
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Please describe the issue in detail...',
            'rows': 4,
            'required': True
        })
    )
    
    class Meta:
        model = RefundRequest
        fields = ['reason', 'description']
    
    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.order:
            instance.order = self.order
            instance.customer = self.order.user
            # Get artist from first order item
            first_item = self.order.items.first()
            if first_item and first_item.artwork:
                instance.artist = first_item.artwork.artist
        if commit:
            instance.save()
        return instance


class GuestOrderLookupForm(forms.Form):
    """Form for guests to look up their orders"""
    order_number = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your order number'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter the email used for the order'
        })
    )