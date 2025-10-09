"""
Ticket Validation System for Jersey Events

Provides QR code scanning and validation functionality for event entry.
Includes anti-fraud measures and validation tracking.
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction

from .models import Event, Ticket

logger = logging.getLogger(__name__)


class TicketValidator:
    """Professional ticket validation system with anti-fraud measures."""

    def __init__(self):
        self.validation_timeout = 30  # seconds for validation session

    def parse_qr_data(self, qr_data_string):
        """Parse QR code data and extract ticket information."""
        try:
            # Expected format: "JERSEY_EVENTS|ticket_number|event_id|customer_email|validation_hash"
            parts = qr_data_string.strip().split('|')

            if len(parts) != 5:
                return None, "Invalid QR code format"

            platform, ticket_number, event_id, customer_email, validation_hash = parts

            if platform != "JERSEY_EVENTS":
                return None, "Invalid QR code platform"

            return {
                'ticket_number': ticket_number,
                'event_id': int(event_id),
                'customer_email': customer_email,
                'validation_hash': validation_hash
            }, None

        except Exception as e:
            logger.error(f"Failed to parse QR data: {e}")
            return None, "Invalid QR code format"

    def verify_ticket_hash(self, ticket, provided_hash):
        """Verify the validation hash matches the ticket."""
        try:
            from .ticket_generator import TicketGenerator
            generator = TicketGenerator()
            expected_hash = generator.generate_ticket_validation_hash(ticket)
            return expected_hash == provided_hash
        except Exception as e:
            logger.error(f"Failed to verify ticket hash: {e}")
            return False

    def validate_ticket_qr(self, qr_data_string, validated_by=None):
        """
        Validate a ticket using QR code data.

        Returns:
            (success: bool, message: str, ticket: Ticket|None)
        """
        try:
            # Parse QR data
            qr_data, error = self.parse_qr_data(qr_data_string)
            if error:
                logger.warning(f"QR parse error: {error}")
                return False, error, None

            # Find the ticket
            try:
                ticket = Ticket.objects.select_related('event', 'customer').get(
                    ticket_number=qr_data['ticket_number'],
                    event_id=qr_data['event_id']
                )
            except Ticket.DoesNotExist:
                logger.warning(f"Ticket not found: {qr_data['ticket_number']}")
                return False, "Ticket not found", None

            # Verify customer email matches
            if ticket.customer.email.lower() != qr_data['customer_email'].lower():
                logger.warning(f"Customer email mismatch for ticket {ticket.ticket_number}")
                return False, "Invalid ticket data", None

            # Verify validation hash
            if not self.verify_ticket_hash(ticket, qr_data['validation_hash']):
                logger.warning(f"Invalid validation hash for ticket {ticket.ticket_number}")
                return False, "Invalid ticket signature", None

            # Check if ticket is already validated
            if ticket.is_validated:
                return False, f"Ticket already used on {ticket.validated_at.strftime('%Y-%m-%d at %H:%M')}", ticket

            # Check ticket status
            if ticket.status != 'valid':
                return False, f"Ticket is {ticket.status} and cannot be used", ticket

            # Check event date (allow entry on event day)
            try:
                event_date = ticket.event.event_date
                today = timezone.now().date()

                if event_date < today:
                    return False, "Event has already passed", ticket
                elif event_date > today:
                    return False, f"Event is not today (scheduled for {event_date.strftime('%Y-%m-%d')})", ticket
            except AttributeError:
                logger.error(f"Invalid event date for ticket {ticket.ticket_number}")
                return False, "Invalid ticket event data", ticket

            # Validate the ticket
            with transaction.atomic():
                success, message = ticket.validate_ticket(validated_by)

            if success:
                logger.info(f"Ticket {ticket.ticket_number} validated successfully for {ticket.event.title}")
                return True, "Ticket validated successfully", ticket
            else:
                logger.warning(f"Ticket validation failed: {message}")
                return False, message, ticket

        except Exception as e:
            logger.error(f"Ticket validation error: {e}")
            return False, "Validation system error", None

    def get_ticket_info(self, qr_data_string):
        """
        Get ticket information without validating (for preview).

        Returns:
            (success: bool, message: str, ticket_info: dict|None)
        """
        try:
            # Parse QR data
            qr_data, error = self.parse_qr_data(qr_data_string)
            if error:
                return False, error, None

            # Find the ticket
            try:
                ticket = Ticket.objects.select_related('event', 'customer').get(
                    ticket_number=qr_data['ticket_number'],
                    event_id=qr_data['event_id']
                )
            except Ticket.DoesNotExist:
                return False, "Ticket not found", None

            # Return ticket information
            ticket_info = {
                'ticket_number': ticket.ticket_number,
                'event_title': ticket.event.title,
                'event_date': ticket.event.event_date.strftime('%Y-%m-%d'),
                'event_time': ticket.event.event_time.strftime('%H:%M'),
                'venue': ticket.event.venue_name,
                'customer_name': ticket.customer.get_full_name() or ticket.customer.username,
                'customer_email': ticket.customer.email,
                'status': ticket.status,
                'is_validated': ticket.is_validated,
                'validated_at': ticket.validated_at.strftime('%Y-%m-%d %H:%M') if ticket.validated_at else None,
                'is_valid_for_entry': ticket.is_valid_for_entry
            }

            return True, "Ticket information retrieved", ticket_info

        except Exception as e:
            logger.error(f"Failed to get ticket info: {e}")
            return False, "Failed to retrieve ticket information", None

    def get_event_validation_stats(self, event_id):
        """Get validation statistics for an event."""
        try:
            event = Event.objects.get(id=event_id)
            tickets = Ticket.objects.filter(event=event)

            stats = {
                'event_title': event.title,
                'event_date': event.event_date.strftime('%Y-%m-%d'),
                'total_tickets': tickets.count(),
                'validated_tickets': tickets.filter(is_validated=True).count(),
                'remaining_tickets': tickets.filter(is_validated=False, status='valid').count(),
                'cancelled_tickets': tickets.filter(status__in=['cancelled', 'refunded']).count(),
                'validation_rate': 0
            }

            if stats['total_tickets'] > 0:
                stats['validation_rate'] = round(
                    (stats['validated_tickets'] / stats['total_tickets']) * 100, 1
                )

            return True, "Statistics retrieved", stats

        except Event.DoesNotExist:
            return False, "Event not found", None
        except Exception as e:
            logger.error(f"Failed to get event stats: {e}")
            return False, "Failed to retrieve statistics", None

    def bulk_validate_tickets(self, qr_data_list, validated_by=None):
        """Validate multiple tickets at once (for group entries)."""
        results = []

        for qr_data in qr_data_list:
            success, message, ticket = self.validate_ticket_qr(qr_data, validated_by)
            results.append({
                'qr_data': qr_data,
                'success': success,
                'message': message,
                'ticket_number': ticket.ticket_number if ticket else None
            })

        successful_validations = sum(1 for r in results if r['success'])
        total_tickets = len(results)

        logger.info(f"Bulk validation completed: {successful_validations}/{total_tickets} successful")

        return results, f"{successful_validations}/{total_tickets} tickets validated successfully"

    def check_duplicate_entry_attempts(self, ticket_number, time_window_minutes=5):
        """Check for potential duplicate entry attempts."""
        try:
            cutoff_time = timezone.now() - timedelta(minutes=time_window_minutes)

            # This would require a validation log model to track attempts
            # For now, we just check if the ticket was recently validated
            ticket = Ticket.objects.get(ticket_number=ticket_number)

            if ticket.is_validated and ticket.validated_at and ticket.validated_at > cutoff_time:
                return True, f"Ticket was recently validated at {ticket.validated_at.strftime('%H:%M')}"

            return False, "No recent validation attempts"

        except Ticket.DoesNotExist:
            return False, "Ticket not found"
        except Exception as e:
            logger.error(f"Failed to check duplicate attempts: {e}")
            return False, "Check failed"


# Utility functions for easy access
def validate_ticket(qr_data_string, validated_by=None):
    """Validate a single ticket using QR code data."""
    validator = TicketValidator()
    return validator.validate_ticket_qr(qr_data_string, validated_by)


def get_ticket_info(qr_data_string):
    """Get ticket information without validating."""
    validator = TicketValidator()
    return validator.get_ticket_info(qr_data_string)


def get_event_stats(event_id):
    """Get validation statistics for an event."""
    validator = TicketValidator()
    return validator.get_event_validation_stats(event_id)