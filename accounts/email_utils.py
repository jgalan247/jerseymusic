from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from .models import EmailVerificationToken
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user, request):
    """Send email verification to user."""
    try:
        # Create verification token
        token = EmailVerificationToken.create_for_user(user)

        # Build verification URL
        if request:
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
        else:
            # Fallback for when no request is available
            try:
                site = Site.objects.get_current()
                domain = site.domain
                protocol = 'https' if settings.DEBUG else 'https'
            except:
                domain = 'localhost:8000'
                protocol = 'http'

        verification_url = f"{protocol}://{domain}{reverse('accounts:verify_email', kwargs={'token': token.token})}"

        # Email context
        context = {
            'user': user,
            'verification_url': verification_url,
            'token': token,
            'site_name': 'Jersey Events',
        }

        # Render email templates
        subject = f"Verify Your Email - Jersey Events"
        html_content = render_to_string('accounts/emails/verify_email.html', context)
        text_content = render_to_string('accounts/emails/verify_email.txt', context)

        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send(fail_silently=False)

        logger.info(f"Verification email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def send_welcome_email(user, request):
    """Send welcome email after successful verification."""
    try:
        # Build URLs
        if request:
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
        else:
            try:
                site = Site.objects.get_current()
                domain = site.domain
                protocol = 'https' if not settings.DEBUG else 'http'
            except:
                domain = 'localhost:8000'
                protocol = 'http'

        if user.user_type == 'artist':
            dashboard_url = f"{protocol}://{domain}{reverse('accounts:organiser_dashboard')}"
        else:
            dashboard_url = f"{protocol}://{domain}{reverse('accounts:profile')}"

        browse_events_url = f"{protocol}://{domain}{reverse('events:events_list')}"

        # Email context
        context = {
            'user': user,
            'dashboard_url': dashboard_url,
            'browse_events_url': browse_events_url,
            'site_name': 'Jersey Events',
        }

        # Render email templates
        subject = f"Welcome to Jersey Events - Let's Get Started!"
        html_content = render_to_string('accounts/emails/welcome.html', context)
        text_content = render_to_string('accounts/emails/welcome.txt', context)

        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send(fail_silently=False)

        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")
        return False


def resend_verification_email(user, request):
    """Resend verification email with rate limiting."""
    from django.utils import timezone
    from datetime import timedelta

    # Check if user recently requested verification (rate limiting)
    recent_tokens = EmailVerificationToken.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(minutes=5)
    )

    if recent_tokens.exists():
        logger.warning(f"Rate limited verification email request for {user.email}")
        return False, "Please wait 5 minutes before requesting another verification email."

    # Send new verification email
    if send_verification_email(user, request):
        return True, "Verification email has been sent to your email address."
    else:
        return False, "There was an error sending the verification email. Please try again later."