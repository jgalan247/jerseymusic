"""
Custom email backend for Resend API integration.
"""
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
import logging

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Custom Django email backend for Resend API.

    Configuration:
        Set EMAIL_BACKEND = 'events.email_backend.ResendEmailBackend'
        Set RESEND_API_KEY in environment variables
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        api_key = getattr(settings, 'RESEND_API_KEY', None)
        if not api_key:
            if not fail_silently:
                raise ValueError("RESEND_API_KEY is not configured in settings")
            logger.error("RESEND_API_KEY is not configured")
        else:
            resend.api_key = api_key

    def send_messages(self, email_messages):
        """
        Send multiple email messages using Resend API.

        Args:
            email_messages: List of EmailMessage objects

        Returns:
            Number of successfully sent emails
        """
        if not email_messages:
            return 0

        sent_count = 0

        for message in email_messages:
            try:
                sent = self._send_message(message)
                if sent:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to {message.to}: {e}")
                if not self.fail_silently:
                    raise

        return sent_count

    def _send_message(self, message):
        """
        Send a single email message using Resend API.

        Args:
            message: EmailMessage object

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Extract email details
            from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
            to_emails = message.to
            subject = message.subject

            # Handle HTML emails (EmailMultiAlternatives)
            if isinstance(message, EmailMultiAlternatives) and message.alternatives:
                # Get HTML content from alternatives
                html_content = None
                for content, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        html_content = content
                        break

                # Prepare Resend email data
                email_data = {
                    'from': from_email,
                    'to': to_emails,
                    'subject': subject,
                    'html': html_content or message.body,
                }

                # Add text version if no HTML found
                if not html_content:
                    email_data['text'] = message.body

            else:
                # Plain text email
                email_data = {
                    'from': from_email,
                    'to': to_emails,
                    'subject': subject,
                    'text': message.body,
                }

            # Add CC if present
            if message.cc:
                email_data['cc'] = message.cc

            # Add BCC if present
            if message.bcc:
                email_data['bcc'] = message.bcc

            # Add reply-to if present
            if message.reply_to:
                email_data['reply_to'] = message.reply_to

            # Send via Resend API
            logger.info(f"Sending email via Resend to {to_emails}")
            response = resend.Emails.send(email_data)

            logger.info(f"Email sent successfully via Resend. ID: {response.get('id', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Resend API error: {e}")
            if not self.fail_silently:
                raise
            return False
