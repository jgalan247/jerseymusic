from django import forms
from django.core.validators import RegexValidator
from orders.models import Order


class CheckoutForm(forms.Form):
    """Form for guest and registered checkout."""
    
    # Customer information
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'required': True
        })
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name',
            'required': True
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name',
            'required': True
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+44 7700 900000',
            'required': True
        })
    )
    
    # Delivery address
    delivery_address_line_1 = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 1',
            'required': True
        })
    )
    delivery_address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 2 (Optional)'
        })
    )
    delivery_parish = forms.ChoiceField(
        choices=[
            ('', '-- Select Parish --'),
            ('st_helier', 'St. Helier'),
            ('st_brelade', 'St. Brelade'),
            ('st_clement', 'St. Clement'),
            ('st_john', 'St. John'),
            ('st_lawrence', 'St. Lawrence'),
            ('st_martin', 'St. Martin'),
            ('st_ouen', 'St. Ouen'),
            ('st_peter', 'St. Peter'),
            ('st_saviour', 'St. Saviour'),
            ('trinity', 'Trinity'),
            ('st_mary', 'St. Mary'),
            ('grouville', 'Grouville'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )
    delivery_postcode = forms.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^JE\d{1,2}\s?\d[A-Z]{2}$',
                message='Enter a valid Jersey postcode (e.g., JE2 3AB)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'JE2 3AB',
            'required': True
        })
    )
    
    # Delivery method
    delivery_method = forms.ChoiceField(
        choices=[
            ('standard', 'Standard Delivery (£5.00)'),
            ('express', 'Express Delivery (£15.00)'),
            ('collection', 'Collection (Free)'),
        ],
        initial='standard',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    # Billing address
    billing_same_as_delivery = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'billing-same'
        })
    )
    
    # Optional billing fields (shown only if different from delivery)
    billing_first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'First Name'
        })
    )
    billing_last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'Last Name'
        })
    )
    billing_address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'Billing Address Line 1'
        })
    )
    billing_address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'Billing Address Line 2'
        })
    )
    billing_parish = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'Parish/City'
        })
    )
    billing_postcode = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control billing-field',
            'placeholder': 'Postcode'
        })
    )
    
    # Additional fields
    customer_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Special instructions for delivery (optional)'
        })
    )
    
    # Marketing consent for guests
    marketing_consent = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I would like to receive updates about new artworks and artists'
    )
    
    # Terms acceptance
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I agree to the Terms & Conditions and Privacy Policy'
    )

    def clean(self):
        cleaned_data = super().clean()
        billing_same = cleaned_data.get('billing_same_as_delivery')
        
        if not billing_same:
            # Validate billing fields if different from delivery
            required_billing = [
                'billing_first_name', 'billing_last_name',
                'billing_address_line_1', 'billing_postcode'
            ]
            for field in required_billing:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required.')
        
        return cleaned_data


class PaymentMethodForm(forms.Form):
    """Form to select payment method before redirecting to SumUp."""
    
    payment_method = forms.ChoiceField(
        choices=[
            ('sumup', 'Pay with Card (via SumUp)'),
        ],
        initial='sumup',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    save_info = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Save my information for faster checkout next time'
    )
