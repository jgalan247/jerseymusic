from django import forms
from django.core.validators import RegexValidator
from orders.models import Order
from orders.validators import validate_order_email, validate_order_phone, TermsAcceptanceValidator


class CheckoutForm(forms.Form):
    """Form for guest and registered checkout for digital tickets."""

    # Customer information
    email = forms.EmailField(
        label='Email Address',
        validators=[validate_order_email],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'required': True
        }),
        help_text='Your tickets will be sent to this email address'
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
        validators=[validate_order_phone],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+44 7700 900000',
            'required': True
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
        label='I would like to receive updates about new events and artists'
    )

    # Account creation for guests
    create_account = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'create-account'
        }),
        label='Save my details for future purchases (create account)'
    )

    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control account-field',
            'placeholder': 'Choose a password',
            'id': 'password1'
        }),
        label='Password'
    )

    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control account-field',
            'placeholder': 'Confirm password',
            'id': 'password2'
        }),
        label='Confirm Password'
    )

    # Terms acceptance
    accept_terms = forms.BooleanField(
        required=True,
        validators=[TermsAcceptanceValidator()],
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I agree to the Terms & Conditions and Privacy Policy',
        error_messages={
            'required': 'You must accept the Terms & Conditions to complete your purchase.'
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        create_account = cleaned_data.get('create_account')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        # Validate account creation fields
        if create_account:
            if not password1:
                self.add_error('password1', 'Password is required when creating an account.')
            if not password2:
                self.add_error('password2', 'Please confirm your password.')
            if password1 and password2 and password1 != password2:
                self.add_error('password2', 'Passwords do not match.')
            if password1 and len(password1) < 8:
                self.add_error('password1', 'Password must be at least 8 characters long.')

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
