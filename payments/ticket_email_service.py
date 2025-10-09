"""
Email service for sending tickets with QR codes after successful payment.
"""

import qrcode
import hashlib
import logging
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import uuid

logger = logging.getLogger('payment_debug')


class TicketEmailService:
    """Service to handle ticket email generation and sending."""

    def send_ticket_confirmation(self, order):
        """
        Send ticket confirmation email with QR codes.

        Args:
            order: Order object containing tickets and customer info

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"📧 Preparing ticket email for order {order.order_number}")

            # Generate context for email template
            context = {
                'order': order,
                'site_url': settings.SITE_URL,
            }

            # Render HTML email
            html_content = render_to_string('emails/ticket_confirmation.html', context)

            # Create plain text version
            text_content = self._create_plain_text_email(order)

            # Create email message
            subject = f'Your Jersey Events Tickets - Order {order.order_number}'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [order.email]

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email
            )

            # Attach HTML version
            email.attach_alternative(html_content, "text/html")

            # Generate and attach QR codes for each ticket
            qr_images = self._generate_qr_codes_for_order(order)

            for idx, qr_data in enumerate(qr_images, 1):
                # Attach QR code as inline image
                qr_image = MIMEImage(qr_data['image'])
                qr_image.add_header('Content-ID', f'<{qr_data["cid"]}>')
                qr_image.add_header('Content-Disposition', 'inline', filename=f'ticket_{idx}.png')
                email.attach(qr_image)

            # Send email
            email.send(fail_silently=False)

            logger.info(f"✅ Ticket email sent successfully to {order.email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send ticket email: {e}")
            return False

    def _generate_qr_codes_for_order(self, order):
        """
        Generate QR codes for all tickets in an order.

        Args:
            order: Order object

        Returns:
            list: List of dictionaries containing QR code images and CIDs
        """
        qr_images = []

        for item_idx, item in enumerate(order.items.all(), 1):
            for ticket_idx in range(1, item.quantity + 1):
                # Generate unique ticket ID
                ticket_id = f"{order.order_number}-{item_idx}{ticket_idx}"

                # Create QR code data
                qr_data = self._create_qr_data(order, item, ticket_id)

                # Generate QR code image
                qr_image = self._generate_qr_code(qr_data)

                # Add to list with Content-ID for email embedding
                qr_images.append({
                    'image': qr_image,
                    'cid': f'qr_{item_idx}_{ticket_idx}',
                    'ticket_id': ticket_id
                })

                logger.info(f"   Generated QR code for ticket {ticket_id}")

        return qr_images

    def _create_qr_data(self, order, item, ticket_id):
        """
        Create data to encode in QR code.

        Args:
            order: Order object
            item: OrderItem object
            ticket_id: Unique ticket identifier

        Returns:
            str: Data to encode in QR code
        """
        # Create validation hash
        validation_string = f"{order.order_number}-{item.event.id}-{ticket_id}-{settings.SECRET_KEY}"
        validation_hash = hashlib.md5(validation_string.encode()).hexdigest()[:8]

        # Create QR data structure
        qr_data = {
            'ticket_id': ticket_id,
            'order': order.order_number,
            'event': item.event.title,
            'date': str(item.event.event_date),
            'time': str(item.event.event_time),
            'venue': item.event.venue_name,
            'validation': validation_hash
        }

        # Convert to string format
        qr_string = f"TICKET:{ticket_id}|ORDER:{order.order_number}|EVENT:{item.event.id}|VALID:{validation_hash}"

        return qr_string

    def _generate_qr_code(self, data):
        """
        Generate QR code image from data.

        Args:
            data: String data to encode

        Returns:
            bytes: PNG image data
        """
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        # Add data
        qr.add_data(data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')

        return buffer.getvalue()

    def _create_plain_text_email(self, order):
        """
        Create plain text version of email.

        Args:
            order: Order object

        Returns:
            str: Plain text email content
        """
        text = f"""
Your Jersey Events Tickets - Order {order.order_number}
========================================================

Hi {order.delivery_first_name},

Thank you for your purchase! Your payment has been confirmed.

ORDER DETAILS:
--------------
Order Number: {order.order_number}
Total Paid: £{order.total}
Customer: {order.delivery_first_name} {order.delivery_last_name}
Email: {order.email}

EVENT DETAILS:
--------------
"""

        for item in order.items.all():
            text += f"""
Event: {item.event.title}
Date: {item.event.event_date}
Time: {item.event.event_time}
Venue: {item.event.venue_name}
Address: {item.event.venue_address}
Tickets: {item.quantity}

"""

        text += """
IMPORTANT INFORMATION:
---------------------
- Present this email or the QR code at the venue entrance
- Each ticket is valid for one entry only
- Arrive at least 15 minutes before the event start time
- Keep this email safe - it's your proof of purchase

Need help? Contact us at support@jerseyevents.co.uk

Thank you for choosing Jersey Events!
"""

        return text


# Singleton instance
ticket_email_service = TicketEmailService()