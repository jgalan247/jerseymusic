# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User, CustomerProfile, ArtistProfile
import re

# Jersey parishes choices matching your model
JERSEY_PARISHES = [
    ('st_helier', 'St. Helier'),
    ('st_brelade', 'St. Brelade'),
    ('st_clement', 'St. Clement'),
    ('st_john', 'St. John'),
    ('st_lawrence', 'St. Lawrence'),
    ('st_martin', 'St. Martin'),
    ('st_mary', 'St. Mary'),
    ('st_ouen', 'St. Ouen'),
    ('st_peter', 'St. Peter'),
    ('st_saviour', 'St. Saviour'),
    ('grouville', 'Grouville'),
    ('trinity', 'Trinity'),
]


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with user type selection."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES, required=True)
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = self.cleaned_data['user_type']
        if commit:
            user.save()
            # Create corresponding profile
            if user.user_type == 'customer':
                CustomerProfile.objects.create(user=user)
            elif user.user_type == 'artist':
                ArtistProfile.objects.create(user=user, display_name=user.get_full_name())
        return user


class CustomerRegistrationForm(UserCreationForm):
    """Registration form for customers with Jersey-specific fields."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number (optional)'
        })
    )
    address_line_1 = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 1'
        })
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 2 (optional)'
        })
    )
    parish = forms.ChoiceField(
        choices=JERSEY_PARISHES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    postcode = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'JE2 3AB'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use email as username if not provided
        self.fields['username'].required = False
        self.fields['username'].widget.attrs['placeholder'] = 'Username (optional - email will be used)'
    
    def clean_email(self):
        """Validate that the email is not already registered."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email
    
    def clean_postcode(self):
        """Validate Jersey postcode format (JE[1-5] + digit + 2 letters)."""
        postcode = self.cleaned_data.get('postcode', '').upper().strip()
        
        # Remove any spaces for validation
        postcode_no_space = postcode.replace(' ', '')
        
        # Jersey postcode pattern: JE[1-5] followed by a digit and two letters
        pattern = r'^JE[1-5]\d[A-Z]{2}$'
        
        if not re.match(pattern, postcode_no_space):
            raise ValidationError(
                'Enter a valid Jersey postcode (e.g., JE2 3AB). '
                'Format: JE[1-5] followed by a digit and two letters.'
            )
        
        # Normalize the postcode with a space after JE + digit
        if len(postcode_no_space) == 6:
            normalized = postcode_no_space[:3] + ' ' + postcode_no_space[3:]
        else:
            normalized = postcode
            
        return normalized
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Use email as username if username not provided
        if not self.cleaned_data.get('username'):
            user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = 'customer'
        user.email_verified = False
        
        if commit:
            user.save()
            # Create customer profile
            CustomerProfile.objects.create(
                user=user,
                address_line_1=self.cleaned_data.get('address_line_1', ''),
                parish=self.cleaned_data.get('parish', ''),
                postcode=self.cleaned_data.get('postcode', '')
            )
        return user


class ArtistRegistrationForm(CustomerRegistrationForm):
    """Registration form for artists with additional artist-specific fields."""
    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Tell us about yourself and your art...',
            'rows': 4
        }),
        required=False,
        max_length=500
    )
    artist_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your artist or studio name'
        })
    )
    business_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Business name (optional)'
        })
    )
    portfolio_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://your-portfolio.com'
        })
    )
    
    def clean_portfolio_website(self):
        """Validate portfolio website URL."""
        url = self.cleaned_data.get('portfolio_website', '')
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def save(self, commit=True):
        user = super(CustomerRegistrationForm, self).save(commit=False)
        # Use email as username if not provided
        if not self.cleaned_data.get('username'):
            user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = 'artist'
        user.email_verified = False
        
        if commit:
            user.save()
            # Create artist profile
            ArtistProfile.objects.create(
                user=user,
                display_name=self.cleaned_data.get('artist_name', user.get_full_name()),
                bio=self.cleaned_data.get('bio', ''),
                business_name=self.cleaned_data.get('business_name', ''),
                website=self.cleaned_data.get('portfolio_website', ''),
                phone_number=self.cleaned_data.get('phone_number', '')
            )
        return user


class LoginForm(forms.Form):
    """Custom login form."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email or Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            self.user = authenticate(username=username, password=password)
            if not self.user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    self.user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if not self.user:
                raise forms.ValidationError('Invalid username/email or password.')
            if not self.user.is_active:
                raise forms.ValidationError('This account is disabled.')
        return self.cleaned_data


class UserUpdateForm(forms.ModelForm):
    """Form for updating basic user information."""
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control'
            })
    
    def clean_email(self):
        """Validate email uniqueness, excluding current user."""
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('This email address is already in use.')
        return email


class CustomerProfileForm(forms.ModelForm):
    """Form for updating customer profile."""
    class Meta:
        model = CustomerProfile
        fields = ['date_of_birth', 'address_line_1', 'parish', 'postcode', 'marketing_consent']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'marketing_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parish'].widget.attrs.update({'class': 'form-control'})
    
    def clean_postcode(self):
        """Validate Jersey postcode format."""
        postcode = self.cleaned_data.get('postcode', '').upper().strip()
        if postcode:  # Only validate if provided
            postcode_no_space = postcode.replace(' ', '')
            pattern = r'^JE[1-5]\d[A-Z]{2}$'
            
            if not re.match(pattern, postcode_no_space):
                raise ValidationError('Enter a valid Jersey postcode (e.g., JE2 3AB).')
            
            if len(postcode_no_space) == 6:
                postcode = postcode_no_space[:3] + ' ' + postcode_no_space[3:]
        
        return postcode


class CustomerProfileUpdateForm(forms.ModelForm):
    """Form for updating customer profile information."""
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = CustomerProfile
        fields = ['address_line_1', 'parish', 'postcode']
        widgets = {
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parish'].widget.attrs.update({'class': 'form-control'})
        # Add phone_number from User model if available
        if self.instance and self.instance.user:
            self.fields['phone_number'].initial = self.instance.user.phone
    
    def clean_postcode(self):
        """Validate Jersey postcode format."""
        postcode = self.cleaned_data.get('postcode', '').upper().strip()
        if postcode:
            postcode_no_space = postcode.replace(' ', '')
            pattern = r'^JE[1-5]\d[A-Z]{2}$'
            
            if not re.match(pattern, postcode_no_space):
                raise ValidationError('Enter a valid Jersey postcode (e.g., JE2 3AB).')
            
            if len(postcode_no_space) == 6:
                postcode = postcode_no_space[:3] + ' ' + postcode_no_space[3:]
        
        return postcode
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Save phone_number to User model
        if 'phone_number' in self.cleaned_data and instance.user:
            instance.user.phone = self.cleaned_data['phone_number']
            instance.user.save()
        if commit:
            instance.save()
        return instance


class ArtistProfileForm(forms.ModelForm):
    """Form for updating artist profile."""
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'bio', 'website', 'instagram_handle', 'studio_address']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_handle': forms.TextInput(attrs={'class': 'form-control'}),
            'studio_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ArtistProfileUpdateForm(forms.ModelForm):
    """Form for updating artist profile information."""
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    parish = forms.ChoiceField(
        choices=JERSEY_PARISHES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    postcode = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    artist_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    portfolio_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    commission_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        disabled=True,  # Read-only - only admin can change
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text='Commission rate can only be changed by administrators'
    )
    
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'bio', 'business_name', 'website', 
                  'instagram_handle', 'studio_address', 'commission_rate']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_handle': forms.TextInput(attrs={'class': 'form-control'}),
            'studio_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Map artist_name to display_name
        if 'display_name' in self.fields:
            self.fields['artist_name'] = self.fields['display_name']
        # Map portfolio_website to website
        if 'website' in self.fields:
            self.fields['portfolio_website'] = self.fields['website']
    
    def clean_postcode(self):
        """Validate Jersey postcode format if provided."""
        postcode = self.cleaned_data.get('postcode', '').upper().strip()
        if postcode:
            postcode_no_space = postcode.replace(' ', '')
            pattern = r'^JE[1-5]\d[A-Z]{2}$'
            
            if not re.match(pattern, postcode_no_space):
                raise ValidationError('Enter a valid Jersey postcode (e.g., JE2 3AB).')
            
            if len(postcode_no_space) == 6:
                postcode = postcode_no_space[:3] + ' ' + postcode_no_space[3:]
        
        return postcode


class ResendVerificationForm(forms.Form):
    """Form to resend verification email."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No user found with this email address.")
        
        user = User.objects.get(email=email)
        if user.email_verified:
            raise ValidationError("This email is already verified.")
        
        return email


class CustomUserChangeForm(UserChangeForm):
    """Custom user change form for admin."""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type')