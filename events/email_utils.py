"""
Email utility functions with error handling and retry mechanisms
"""

import logging
import time
from typing import List, Dict, Any, Optional
from django.core.mail import send_mail, send_mass_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Enhanced email service with retry logic and error handling"""

    def __init__(self, max_retries=3, retry_delay=1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def send_email_with_retry(
        self,
        subject: str,
        message: str,
        from_email: str = None,
        recipient_list: List[str] = None,
        html_message: str = None,
        fail_silently: bool = False
    ) -> bool:
        """Send email with retry logic"""
        from_email = from_email or settings.DEFAULT_FROM_EMAIL

        if not recipient_list:
            logger.warning("No recipients provided for email")
            return False

        for attempt in range(self.max_retries + 1):
            try:
                result = send_mail(
                    subject=f"{settings.EMAIL_SUBJECT_PREFIX}{subject}",
                    message=message,
                    from_email=from_email,
                    recipient_list=recipient_list,
                    html_message=html_message,
                    fail_silently=fail_silently
                )

                if result:
                    logger.info(f"Email sent successfully to {recipient_list} (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Email send returned 0 - no emails sent (attempt {attempt + 1})")

            except Exception as e:
                logger.error(f"Email send attempt {attempt + 1} failed: {str(e)}")

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    if not fail_silently:
                        raise
                    return False

        return False

    def send_template_email(
        self,
        template_name: str,
        context: Dict[str, Any],
        subject: str,
        recipient_list: List[str],
        from_email: str = None
    ) -> bool:
        """Send email using Django templates"""
        try:
            # Render HTML version
            html_message = render_to_string(f'emails/{template_name}.html', context)

            # Try to render text version, fallback to stripped HTML
            try:
                text_message = render_to_string(f'emails/{template_name}.txt', context)
            except:
                text_message = strip_tags(html_message)

            return self.send_email_with_retry(
                subject=subject,
                message=text_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message
            )

        except Exception as e:
            logger.error(f"Template email failed for {template_name}: {str(e)}")
            return False

    def send_email_with_attachments(
        self,
        subject: str,
        message: str,
        recipient_list: List[str],
        html_message: str = None,
        attachments: List[Dict] = None,
        from_email: str = None
    ) -> bool:
        """Send email with file attachments."""
        from_email = from_email or settings.DEFAULT_FROM_EMAIL

        if not recipient_list:
            logger.warning("No recipients provided for email with attachments")
            return False

        for attempt in range(self.max_retries + 1):
            try:
                # Create EmailMessage for attachments
                email = EmailMessage(
                    subject=f"{settings.EMAIL_SUBJECT_PREFIX}{subject}",
                    body=html_message or message,
                    from_email=from_email,
                    to=recipient_list
                )

                # Set content type for HTML
                if html_message:
                    email.content_subtype = 'html'

                # Add attachments
                if attachments:
                    for attachment in attachments:
                        try:
                            if 'content' in attachment and 'filename' in attachment and attachment['content']:
                                email.attach(
                                    attachment['filename'],
                                    attachment['content'],
                                    attachment.get('mimetype', 'application/octet-stream')
                                )
                            elif 'file_path' in attachment and 'filename' in attachment:
                                email.attach_file(attachment['file_path'])
                        except Exception as e:
                            logger.warning(f"Failed to attach file {attachment.get('filename', 'unknown')}: {e}")
                            continue

                # Send email
                result = email.send()

                if result:
                    logger.info(f"Email with attachments sent successfully to {recipient_list} (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Email with attachments send returned 0 (attempt {attempt + 1})")

            except Exception as e:
                logger.error(f"Email with attachments send attempt {attempt + 1} failed: {str(e)}")

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return False

        return False

    def send_order_confirmation(self, order) -> bool:
        """Send order confirmation email with ticket attachments."""
        try:
            # Get tickets for this order
            tickets = getattr(order, 'tickets', [])
            if hasattr(order, 'tickets'):
                tickets = order.tickets.all()
            else:
                # Fallback to finding tickets by order
                from events.models import Ticket
                tickets = Ticket.objects.filter(order=order)

            context = {
                'order': order,
                'customer_name': f"{order.delivery_first_name} {order.delivery_last_name}",
                'site_name': 'Jersey Events',
                'support_email': 'support@coderra.je',
                'tickets': tickets,
                'ticket_count': tickets.count() if hasattr(tickets, 'count') else len(tickets)
            }

            # Render email content
            html_message = render_to_string('emails/order_confirmation.html', context)
            text_message = render_to_string('emails/order_confirmation.txt', context)

            # Prepare ticket attachments
            attachments = []
            for ticket in tickets:
                if ticket.pdf_file:
                    try:
                        # Read PDF content
                        ticket.pdf_file.open()
                        pdf_content = ticket.pdf_file.read()
                        ticket.pdf_file.close()

                        attachments.append({
                            'filename': f'ticket_{ticket.ticket_number}.pdf',
                            'content': pdf_content,
                            'mimetype': 'application/pdf'
                        })
                        logger.info(f"Added PDF attachment for ticket {ticket.ticket_number}")

                    except Exception as e:
                        logger.error(f"Failed to attach PDF for ticket {ticket.ticket_number}: {e}")

            # Send email with attachments
            if attachments:
                return self.send_email_with_attachments(
                    subject=f'Order Confirmation #{order.order_number} - Your Tickets',
                    message=text_message,
                    html_message=html_message,
                    recipient_list=[order.email],
                    attachments=attachments
                )
            else:
                # Fallback to regular email if no attachments
                return self.send_email_with_retry(
                    subject=f'Order Confirmation #{order.order_number}',
                    message=text_message,
                    html_message=html_message,
                    recipient_list=[order.email]
                )

        except Exception as e:
            logger.error(f"Failed to send order confirmation with attachments: {e}")
            # Fallback to basic confirmation
            return self.send_template_email(
                template_name='order_confirmation',
                context={
                    'order': order,
                    'customer_name': f"{order.delivery_first_name} {order.delivery_last_name}",
                    'site_name': 'Jersey Events',
                    'support_email': 'support@coderra.je'
                },
                subject=f'Order Confirmation #{order.order_number}',
                recipient_list=[order.email]
            )

    def send_artist_notification(self, order, artist) -> bool:
        """Send new order notification to artist"""
        context = {
            'order': order,
            'artist': artist,
            'site_name': 'Jersey Events',
            'dashboard_url': '/dashboard/'  # Update with actual artist dashboard URL
        }

        return self.send_template_email(
            template_name='artist_order_notification',
            context=context,
            subject=f'New Order Received - #{order.id}',
            recipient_list=[artist.user.email]
        )

    def send_email_verification(self, user, verification_url) -> bool:
        """Send email verification link"""
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'Jersey Events',
            'expiry_hours': 48
        }

        return self.send_template_email(
            template_name='email_verification',
            context=context,
            subject='Verify your email address',
            recipient_list=[user.email]
        )

    def test_email_configuration(self) -> Dict[str, Any]:
        """Test email configuration"""
        test_results = {
            'backend': settings.EMAIL_BACKEND,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'configured': True,
            'test_sent': False,
            'error': None
        }

        try:
            # Send a test email
            result = self.send_email_with_retry(
                subject='Email Configuration Test',
                message='This is a test email to verify email configuration.',
                recipient_list=['test@example.com'],
                fail_silently=True
            )

            test_results['test_sent'] = result

        except Exception as e:
            test_results['error'] = str(e)
            test_results['configured'] = False

        return test_results


# Global email service instance
email_service = EmailService()


def send_email_safe(subject, message, recipient_list, **kwargs):
    """Wrapper function for backwards compatibility"""
    return email_service.send_email_with_retry(
        subject=subject,
        message=message,
        recipient_list=recipient_list,
        **kwargs
    )