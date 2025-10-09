"""
PDF Ticket Generation System for Jersey Events

Generates professional PDF tickets with QR codes, event details,
customer information, and proper branding.
"""

import os
import qrcode
import hashlib
import logging
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr

logger = logging.getLogger(__name__)


class TicketGenerator:
    """Professional PDF ticket generator with QR codes."""

    # Jersey Events brand colors
    BRAND_COLORS = {
        'primary': HexColor('#667eea'),      # Purple blue
        'secondary': HexColor('#764ba2'),     # Deep purple
        'accent': HexColor('#f093fb'),       # Light pink
        'dark': HexColor('#2d3748'),         # Dark gray
        'light': HexColor('#f7fafc'),        # Light gray
        'success': HexColor('#48bb78'),      # Green
        'text': HexColor('#2d3748'),         # Dark text
    }

    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 0.75 * inch
        self.content_width = self.page_width - (2 * self.margin)

    def generate_ticket_validation_hash(self, ticket):
        """Generate a secure validation hash for the ticket."""
        # Create hash from ticket data
        hash_data = f"{ticket.ticket_number}:{ticket.event.id}:{ticket.customer.email}:{ticket.purchase_date.isoformat()}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]

    def generate_qr_code_data(self, ticket):
        """Generate QR code data with validation information."""
        validation_hash = self.generate_ticket_validation_hash(ticket)

        qr_data = {
            'ticket_id': ticket.ticket_number,
            'event_id': ticket.event.id,
            'customer_email': ticket.customer.email,
            'purchase_date': ticket.purchase_date.isoformat(),
            'validation_hash': validation_hash,
            'event_date': ticket.event.event_date.isoformat(),
            'venue': ticket.event.venue_name
        }

        # Convert to string format for QR code
        return f"JERSEY_EVENTS|{ticket.ticket_number}|{ticket.event.id}|{ticket.customer.email}|{validation_hash}"

    def create_qr_code_image(self, ticket):
        """Create QR code image for the ticket."""
        qr_data = self.generate_qr_code_data(ticket)

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Create image
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to BytesIO for ReportLab
        img_buffer = BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return img_buffer

    def create_ticket_header(self, story, ticket):
        """Create the ticket header with branding."""
        # Jersey Events Logo/Brand Section
        header_table = Table([
            ['JERSEY EVENTS', f'TICKET #{ticket.ticket_number}']
        ], colWidths=[self.content_width * 0.6, self.content_width * 0.4])

        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 24),
            ('TEXTCOLOR', (0, 0), (0, 0), self.BRAND_COLORS['primary']),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 14),
            ('TEXTCOLOR', (1, 0), (1, 0), self.BRAND_COLORS['dark']),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        story.append(header_table)
        story.append(Spacer(1, 20))

    def create_event_info_section(self, story, ticket):
        """Create the main event information section."""
        event = ticket.event

        # Event title
        title_style = ParagraphStyle(
            'EventTitle',
            parent=getSampleStyleSheet()['Heading1'],
            fontSize=20,
            spaceAfter=10,
            textColor=self.BRAND_COLORS['dark'],
            alignment=TA_CENTER
        )

        story.append(Paragraph(event.title, title_style))
        story.append(Spacer(1, 15))

        # Event details table
        event_details = [
            ['Date & Time:', f"{event.event_date.strftime('%A, %B %d, %Y')} at {event.event_time.strftime('%I:%M %p')}"],
            ['Venue:', event.venue_name],
            ['Address:', event.venue_address],
            ['Ticket Price:', f"£{ticket.event.ticket_price}"],
            ['Order Number:', getattr(ticket, 'order_number', 'N/A')]
        ]

        details_table = Table(event_details, colWidths=[self.content_width * 0.3, self.content_width * 0.7])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.BRAND_COLORS['text']),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [white, self.BRAND_COLORS['light']]),
            ('GRID', (0, 0), (-1, -1), 0.5, self.BRAND_COLORS['light']),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        story.append(details_table)
        story.append(Spacer(1, 20))

    def create_customer_qr_section(self, story, ticket):
        """Create customer info and QR code section."""
        # Create QR code
        qr_buffer = self.create_qr_code_image(ticket)
        qr_image = Image(qr_buffer, width=120, height=120)

        # Customer information
        customer_info = [
            ['Customer Name:', ticket.customer.get_full_name() or ticket.customer.username],
            ['Email:', ticket.customer.email],
            ['Purchase Date:', ticket.purchase_date.strftime('%B %d, %Y at %I:%M %p')],
            ['Ticket Status:', ticket.status.title()]
        ]

        customer_table = Table(customer_info, colWidths=[100, 200])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.BRAND_COLORS['text']),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        # Combine customer info and QR code
        main_table = Table([
            [customer_table, qr_image]
        ], colWidths=[self.content_width * 0.6, self.content_width * 0.4])

        main_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(main_table)
        story.append(Spacer(1, 15))

        # QR code instructions
        qr_instructions = ParagraphStyle(
            'QRInstructions',
            parent=getSampleStyleSheet()['Normal'],
            fontSize=9,
            textColor=self.BRAND_COLORS['text'],
            alignment=TA_CENTER,
            spaceAfter=10
        )

        story.append(Paragraph(
            "Present this QR code at the venue for entry. Keep this ticket safe and bring a digital or printed copy to the event.",
            qr_instructions
        ))

    def create_footer_section(self, story, ticket):
        """Create footer with terms and organizer info."""
        story.append(Spacer(1, 20))

        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=self.BRAND_COLORS['light']))
        story.append(Spacer(1, 10))

        # Organizer information
        organizer_info = f"Event organized by: {ticket.event.organiser.get_full_name() or ticket.event.organiser.username}"
        if ticket.event.organiser.email:
            organizer_info += f" | Contact: {ticket.event.organiser.email}"

        organizer_style = ParagraphStyle(
            'OrganizerInfo',
            parent=getSampleStyleSheet()['Normal'],
            fontSize=9,
            textColor=self.BRAND_COLORS['text'],
            alignment=TA_CENTER,
            spaceAfter=8
        )

        story.append(Paragraph(organizer_info, organizer_style))

        # Terms and conditions
        terms_text = """
        <b>TERMS & CONDITIONS:</b> This ticket is non-transferable and non-refundable unless the event is cancelled.
        Entry may be refused if this ticket has been resold or transferred. Please arrive at least 15 minutes before
        the event start time. Jersey Events and the event organizer reserve the right to refuse entry or remove
        attendees who violate venue policies. For support, contact: support@jerseyevents.je
        """

        terms_style = ParagraphStyle(
            'Terms',
            parent=getSampleStyleSheet()['Normal'],
            fontSize=8,
            textColor=self.BRAND_COLORS['text'],
            alignment=TA_LEFT,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=10
        )

        story.append(Paragraph(terms_text, terms_style))

        # Jersey Events footer
        footer_text = "Jersey Events | Professional Event Ticketing | www.jerseyevents.je"
        footer_style = ParagraphStyle(
            'Footer',
            parent=getSampleStyleSheet()['Normal'],
            fontSize=8,
            textColor=self.BRAND_COLORS['primary'],
            alignment=TA_CENTER
        )

        story.append(Paragraph(footer_text, footer_style))

    def generate_ticket_pdf(self, ticket):
        """Generate a complete PDF ticket."""
        try:
            logger.info(f"Generating PDF ticket for {ticket.ticket_number}")

            # Create PDF buffer
            buffer = BytesIO()

            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=self.margin,
                bottomMargin=self.margin,
                leftMargin=self.margin,
                rightMargin=self.margin,
                title=f"Jersey Events Ticket - {ticket.ticket_number}",
                author="Jersey Events",
                subject=f"Ticket for {ticket.event.title}",
                creator="Jersey Events Ticketing System"
            )

            # Build the ticket content
            story = []

            # Add all sections
            self.create_ticket_header(story, ticket)
            self.create_event_info_section(story, ticket)
            self.create_customer_qr_section(story, ticket)
            self.create_footer_section(story, ticket)

            # Build PDF
            doc.build(story)

            # Get PDF data
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            buffer.close()

            logger.info(f"Successfully generated PDF ticket for {ticket.ticket_number} ({len(pdf_data)} bytes)")
            return pdf_data

        except Exception as e:
            logger.error(f"Failed to generate PDF ticket for {ticket.ticket_number}: {e}")
            raise

    def save_ticket_pdf(self, ticket, pdf_data):
        """Save the PDF data to the ticket model."""
        try:
            filename = f"ticket_{ticket.ticket_number}.pdf"

            # Save PDF to ticket model (assuming there's a pdf_file field)
            if hasattr(ticket, 'pdf_file'):
                ticket.pdf_file.save(
                    filename,
                    ContentFile(pdf_data),
                    save=True
                )
                logger.info(f"Saved PDF file for ticket {ticket.ticket_number}")

            return filename

        except Exception as e:
            logger.error(f"Failed to save PDF for ticket {ticket.ticket_number}: {e}")
            raise

    def generate_multiple_tickets_pdf(self, tickets):
        """Generate a combined PDF for multiple tickets."""
        try:
            if not tickets:
                raise ValueError("No tickets provided")

            logger.info(f"Generating combined PDF for {len(tickets)} tickets")

            # Create PDF buffer
            buffer = BytesIO()

            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=self.margin,
                bottomMargin=self.margin,
                leftMargin=self.margin,
                rightMargin=self.margin,
                title=f"Jersey Events Tickets - Order",
                author="Jersey Events",
                subject=f"Tickets for order",
                creator="Jersey Events Ticketing System"
            )

            story = []

            # Add each ticket with page breaks
            for i, ticket in enumerate(tickets):
                if i > 0:
                    # Add page break between tickets
                    from reportlab.platypus import PageBreak
                    story.append(PageBreak())

                # Add ticket content
                self.create_ticket_header(story, ticket)
                self.create_event_info_section(story, ticket)
                self.create_customer_qr_section(story, ticket)
                self.create_footer_section(story, ticket)

            # Build PDF
            doc.build(story)

            # Get PDF data
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            buffer.close()

            logger.info(f"Successfully generated combined PDF for {len(tickets)} tickets ({len(pdf_data)} bytes)")
            return pdf_data

        except Exception as e:
            logger.error(f"Failed to generate combined PDF for tickets: {e}")
            raise


# Utility functions
def generate_ticket_pdf(ticket):
    """Generate PDF for a single ticket."""
    generator = TicketGenerator()
    return generator.generate_ticket_pdf(ticket)


def generate_tickets_pdf(tickets):
    """Generate combined PDF for multiple tickets."""
    generator = TicketGenerator()
    return generator.generate_multiple_tickets_pdf(tickets)


def get_ticket_validation_data(ticket):
    """Get validation data for a ticket."""
    generator = TicketGenerator()
    return {
        'validation_hash': generator.generate_ticket_validation_hash(ticket),
        'qr_data': generator.generate_qr_code_data(ticket)
    }