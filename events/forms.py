# events/forms.py
from django import forms
from django.core.mail import EmailMessage
from django.conf import settings
from events.models import Event

class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'venue_name', 'venue_address', 'event_date', 'event_time', 'capacity', 'ticket_price', 'main_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'main_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


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