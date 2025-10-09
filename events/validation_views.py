"""
Ticket validation views for event organizers and staff.
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone

from .models import Event, Ticket
from .ticket_validator import TicketValidator, validate_ticket, get_ticket_info, get_event_stats

logger = logging.getLogger(__name__)


@login_required
def event_validation_dashboard(request, event_id):
    """Dashboard for event organizers to validate tickets."""
    event = get_object_or_404(Event, id=event_id)

    # Check if user is the organizer
    if event.organiser != request.user:
        messages.error(request, "You can only validate tickets for your own events.")
        return redirect('events:my_events')

    # Get event statistics
    success, message, stats = get_event_stats(event_id)
    if not success:
        stats = {'error': message}

    context = {
        'event': event,
        'stats': stats,
        'can_validate': event.event_date == timezone.now().date(),
    }

    return render(request, 'events/validation_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def validate_ticket_qr(request):
    """AJAX endpoint to validate a ticket via QR code."""
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data', '').strip()
        event_id = data.get('event_id')

        if not qr_data:
            return JsonResponse({
                'success': False,
                'message': 'No QR code data provided'
            })

        # Verify event access
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
                if event.organiser != request.user:
                    return JsonResponse({
                        'success': False,
                        'message': 'Access denied'
                    })
            except Event.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Event not found'
                })

        # Validate the ticket
        success, message, ticket = validate_ticket(qr_data, validated_by=request.user)

        response_data = {
            'success': success,
            'message': message
        }

        if ticket:
            response_data.update({
                'ticket': {
                    'ticket_number': ticket.ticket_number,
                    'customer_name': ticket.customer.get_full_name() or ticket.customer.username,
                    'customer_email': ticket.customer.email,
                    'event_title': ticket.event.title,
                    'validated_at': ticket.validated_at.isoformat() if ticket.validated_at else None,
                }
            })

        # Log the validation attempt
        logger.info(f"Ticket validation attempt by {request.user.username}: {message}")

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request data'
        })
    except Exception as e:
        logger.error(f"Ticket validation error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Validation system error'
        })


@login_required
@require_http_methods(["POST"])
def get_ticket_preview(request):
    """AJAX endpoint to get ticket information without validating."""
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data', '').strip()

        if not qr_data:
            return JsonResponse({
                'success': False,
                'message': 'No QR code data provided'
            })

        # Get ticket information
        success, message, ticket_info = get_ticket_info(qr_data)

        response_data = {
            'success': success,
            'message': message
        }

        if success and ticket_info:
            response_data['ticket'] = ticket_info

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request data'
        })
    except Exception as e:
        logger.error(f"Ticket preview error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Preview system error'
        })


@login_required
def event_validation_stats(request, event_id):
    """AJAX endpoint to get real-time validation statistics."""
    event = get_object_or_404(Event, id=event_id)

    # Check access
    if event.organiser != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Access denied'
        })

    success, message, stats = get_event_stats(event_id)

    if success:
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    else:
        return JsonResponse({
            'success': False,
            'message': message
        })


@login_required
def validated_tickets_list(request, event_id):
    """Show list of validated tickets for an event."""
    event = get_object_or_404(Event, id=event_id)

    # Check access
    if event.organiser != request.user:
        messages.error(request, "You can only view tickets for your own events.")
        return redirect('events:my_events')

    # Get validated tickets
    validated_tickets = Ticket.objects.filter(
        event=event,
        is_validated=True
    ).select_related('customer', 'validated_by').order_by('-validated_at')

    context = {
        'event': event,
        'validated_tickets': validated_tickets,
        'total_validated': validated_tickets.count()
    }

    return render(request, 'events/validated_tickets_list.html', context)


@method_decorator(login_required, name='dispatch')
class BulkTicketValidationView(View):
    """Handle bulk ticket validation for group entries."""

    def get(self, request, event_id):
        """Show bulk validation form."""
        event = get_object_or_404(Event, id=event_id)

        if event.organiser != request.user:
            messages.error(request, "Access denied.")
            return redirect('events:my_events')

        context = {
            'event': event,
        }

        return render(request, 'events/bulk_validation.html', context)

    def post(self, request, event_id):
        """Process bulk validation."""
        event = get_object_or_404(Event, id=event_id)

        if event.organiser != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Access denied'
            })

        try:
            data = json.loads(request.body)
            qr_data_list = data.get('qr_codes', [])

            if not qr_data_list:
                return JsonResponse({
                    'success': False,
                    'message': 'No QR codes provided'
                })

            # Validate tickets
            validator = TicketValidator()
            results, summary = validator.bulk_validate_tickets(qr_data_list, validated_by=request.user)

            return JsonResponse({
                'success': True,
                'results': results,
                'summary': summary
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data'
            })
        except Exception as e:
            logger.error(f"Bulk validation error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Bulk validation failed'
            })


# Admin/staff views (for site administrators)
@login_required
def admin_validation_overview(request):
    """Overview of validation activity across all events (staff only)."""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('events:home')

    from django.utils import timezone
    from datetime import timedelta

    # Get events happening today or recently
    today = timezone.now().date()
    recent_date = today - timedelta(days=7)

    events_with_validation = Event.objects.filter(
        event_date__gte=recent_date,
        tickets__isnull=False
    ).distinct().prefetch_related('tickets')

    event_stats = []
    for event in events_with_validation:
        tickets = event.tickets.all()
        validated_count = tickets.filter(is_validated=True).count()
        total_count = tickets.count()

        event_stats.append({
            'event': event,
            'total_tickets': total_count,
            'validated_tickets': validated_count,
            'validation_rate': round((validated_count / total_count) * 100, 1) if total_count > 0 else 0
        })

    context = {
        'event_stats': event_stats,
        'today': today
    }

    return render(request, 'events/admin_validation_overview.html', context)