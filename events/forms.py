# events/forms.py
from django import forms
from django.core.mail import EmailMessage
from django.core.exceptions import ValidationError
from django.conf import settings
from events.models import Event
from events.validators import (
    validate_event_capacity,
    validate_ticket_price,
    EventCapacityValidator,
    TicketPriceValidator
)

class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'venue_name', 'venue_address', 'event_date', 'event_time', 'capacity', 'ticket_price', 'main_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'main_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': str(settings.MAX_AUTO_CAPACITY),
                'help_text': f'Maximum capacity: {settings.MAX_AUTO_CAPACITY} tickets. For larger events, contact {settings.CUSTOM_PRICING_EMAIL}.'
            })
        }

    def clean_capacity(self):
        """Validate capacity using custom validator."""
        capacity = self.cleaned_data.get('capacity')
        if capacity:
            validate_event_capacity(capacity)
        return capacity

    def clean_ticket_price(self):
        """Validate ticket price using custom validator."""
        ticket_price = self.cleaned_data.get('ticket_price')
        if ticket_price:
            validate_ticket_price(ticket_price)
        return ticket_price

    def clean(self):
        """Additional form-level validation."""
        cleaned_data = super().clean()
        capacity = cleaned_data.get('capacity')
        ticket_price = cleaned_data.get('ticket_price')

        # Show pricing tier information
        if capacity and ticket_price:
            from events.settings import get_pricing_tier
            tier = get_pricing_tier(capacity)

            if tier:
                # Calculate platform fee for this tier
                platform_fee = tier['fee']
                # Add helpful message to user
                self.tier_info = {
                    'tier': tier['name'],
                    'platform_fee': platform_fee,
                    'capacity': capacity
                }

        return cleaned_data


class ContactForm(forms.Form):
    """Contact form for Jersey Events."""
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name',
            'required': True
        }),
        label='Full Name'
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com',
            'required': True
        }),
        label='Email Address'
    )

    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject (optional)'
        }),
        label='Subject'
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Your message...',
            'rows': 6,
            'required': True
        }),
        label='Message'
    )

    def clean_message(self):
        """Validate message length."""
        message = self.cleaned_data.get('message')
        if message and len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message

    def send_email(self):
        """Send the contact form email."""
        if not self.is_valid():
            return False

        # Get cleaned data
        full_name = self.cleaned_data['full_name']
        email = self.cleaned_data['email']
        subject = self.cleaned_data.get('subject', '')
        message = self.cleaned_data['message']

        # Format subject line
        if subject:
            email_subject = f"Contact Form: {subject}"
        else:
            email_subject = "Contact Form Submission - Jersey Events"

        # Format email body
        email_body = f"""
New contact form submission from Jersey Events website:

Name: {full_name}
Email: {email}
Subject: {subject if subject else 'No subject provided'}

Message:
{message}

---
This email was sent from the Jersey Events contact form.
Reply directly to this email to respond to the sender.
        """.strip()

        try:
            # Create email message
            email_message = EmailMessage(
                subject=email_subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['events_contact@coderra.je'],
                reply_to=[email]
            )

            # Send email
            email_message.send(fail_silently=False)
            return True

        except Exception as e:
            # Log error in production
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Contact form email failed: {e}")
            return False