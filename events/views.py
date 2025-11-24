from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from events.models import Event, EventImage, Category
from events.forms import EventCreateForm, ContactForm
from django.conf import settings
from django.db.models import Count
from django.views.generic import DetailView
from .models import Event
from django.views.generic import ListView, DetailView
from decimal import Decimal
from orders.models import Order, OrderItem
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
import csv
import logging

logger = logging.getLogger(__name__)

@login_required
def create_event(request):
    # Check if user is an artist
    if request.user.user_type != 'artist':
        messages.error(request, "Only organisers can create events")
        return redirect('/')

    # Check if artist has connected SumUp account (CRITICAL for receiving payments)
    try:
        artist_profile = request.user.artistprofile
        if not artist_profile.is_sumup_connected:
            messages.warning(
                request,
                'Please connect your SumUp account before creating events. '
                'This is where customers\' ticket payments will be sent directly to you.'
            )
            # Store the current URL to redirect back after SumUp OAuth
            from django.urls import reverse
            next_url = reverse('events:create_event')
            return redirect(f"{reverse('accounts:sumup_connect')}?next={next_url}")
    except:
        messages.error(request, "Artist profile not found. Please complete your profile first.")
        return redirect('accounts:profile')

    # Platform uses pay-per-event pricing with listing fees (no subscription required)
    # Artists pay a listing fee when creating each event

    if request.method == 'POST':
        form = EventCreateForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organiser = request.user
            event.status = 'draft'  # Will be published after listing fee payment
            event.save()

            # Create listing fee
            from .models import ListingFee, ListingFeeConfig
            listing_fee, created = ListingFee.objects.get_or_create(
                event=event,
                defaults={
                    'organizer': request.user,
                    'amount': ListingFeeConfig.get_config().standard_fee
                }
            )

            # Save main image
            if 'main_image' in request.FILES:
                EventImage.objects.create(
                    event=event,
                    image=request.FILES['main_image'],
                    is_primary=True,
                    order=1
                )

            messages.success(
                request,
                f'"{event.title}" created successfully! Your event has been saved as a draft. '
                f'Pay the £{listing_fee.amount} listing fee to publish it and make it visible to customers.'
            )
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventCreateForm()
    
    return render(request, 'events/upload.html', {'form': form})

from django.utils import timezone
from django.db.models import Sum, Count, Q

@login_required
def my_events(request):
    """Organiser's event management page"""

    if request.user.user_type != 'artist':
        messages.error(request, 'Only event organisers can access this page.')
        return redirect('events:events_list')

    # Get all events for this organiser
    events = Event.objects.filter(organiser=request.user).order_by('-created_at')

    # Add calculated fields to each event
    for event in events:
        # Calculate tickets sold
        tickets_sold = OrderItem.objects.filter(
            event=event,
            order__status='completed'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        event.tickets_sold = tickets_sold

        # Calculate revenue
        revenue = 0
        completed_items = OrderItem.objects.filter(
            event=event,
            order__status='completed'
        )

        for item in completed_items:
            revenue += item.price * item.quantity
        event.revenue = revenue

    # Filter events by status
    published_events = events.filter(status='published')
    draft_events = events.filter(status='draft')
    upcoming_events = events.filter(
        event_date__gte=timezone.now().date(),
        status='published'
    )

    context = {
        'events': events,
        'published_events': published_events,
        'draft_events': draft_events,
        'upcoming_events': upcoming_events,
        'total_events': events.count(),
        'published_count': published_events.count(),
        'drafts_count': draft_events.count(),
        'upcoming_count': upcoming_events.count(),
    }

    return render(request, 'events/my_events.html', context)

def events_list(request):
    events = Event.objects.filter(status='published')
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        events = events.filter(category__slug=category)
    
    # Filter by artist
    artist_id = request.GET.get('artist')
    if artist_id:
        events = events.filter(organiser_id=artist_id)
    
    # Sort events
    sort = request.GET.get('sort')
    if sort == 'price_low':
        events = events.order_by('ticket_price')
    elif sort == 'price_high':
        events = events.order_by('-ticket_price')
    elif sort == 'date':
        events = events.order_by('event_date', 'event_time')
    else:
        events = events.order_by('-created_at')
    
    return render(request, 'events/gallery.html', {'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.status != 'published' and event.organiser != request.user:
        messages.error(request, "This event is not available")
        return redirect('events:gallery')
    return render(request, 'events/detail.html', {'event': event})

# Add this updated home view to events/views.py

@csrf_exempt
@never_cache
def health_check(request):
    """
    Health check endpoint for Railway deployment monitoring.

    This endpoint must:
    - Respond quickly (no database queries)
    - Be exempt from CSRF protection
    - Never be cached
    - Work without authentication
    """
    logger.info(f"Health check request from {request.META.get('REMOTE_ADDR', 'unknown')}, Host: {request.META.get('HTTP_HOST', 'unknown')}")

    return JsonResponse({
        'status': 'healthy',
        'service': 'Jersey Music Events'
    }, status=200)

def home(request):
    """Homepage view with featured events and artists."""
    from accounts.models import User
    
    # Get featured events (active, available, and featured or recent)
    featured_events = Event.objects.filter(
        status='published'
    ).select_related('organiser', 'category').order_by('-featured', '-created_at')[:8]
    
    # If no featured events, just get the latest ones
    if not featured_events:
        featured_events = Event.objects.filter(
            status='published'
        ).select_related('organiser', 'category').order_by('-created_at')[:8]
    
    # Get featured artists (those with active events)
    featured_artists = User.objects.filter(
        user_type='artist',
        is_active=True,
        events__status='active'
    ).distinct().annotate(
        event_count=Count('events')
    ).order_by('-event_count')[:4]
    
    context = {
        'featured_events': featured_events,
        'featured_artists': featured_artists,
    }
    
    return render(request, 'events/home.html', context)

# Add these at the end of events/views.py

def about(request):
    """About Us page."""
    return render(request, 'events/about.html')

def contact(request):
    """Contact page with form handling."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Try to send email
            if form.send_email():
                messages.success(
                    request,
                    "Thank you for your message! We'll get back to you within 24 hours."
                )
                # Redirect to clear the form after successful submission
                return redirect('events:contact')
            else:
                messages.error(
                    request,
                    "Sorry, there was an error sending your message. Please try again or contact us directly at events_contact@coderra.je"
                )
        else:
            messages.error(
                request,
                "Please correct the errors below and try again."
            )
    else:
        form = ContactForm()

    context = {
        'form': form,
        'contact_email': 'events_contact@coderra.je',
        'contact_phone': '+44 1534 123456',
        'contact_address': 'Jersey, Channel Islands'
    }

    return render(request, 'events/contact.html', context)

def organisers_list(request):
    """List all artists."""
    from accounts.models import User
    artists = User.objects.filter(user_type='artist', is_active=True)
    return render(request, 'events/artists.html', {'artists': artists})

def privacy(request):
    """Privacy policy page."""
    return render(request, 'events/privacy.html')

def terms(request):
    """Terms and conditions page."""
    return render(request, 'events/terms.html')


# Add this function to your existing views.py
def pricing(request):
    """Pricing page showing all tiers"""
    
    # Get pricing from settings
    pricing_tiers = []
    if hasattr(settings, 'PRICING_CONFIG'):
        tiers_data = settings.PRICING_CONFIG.get('pay_per_event', {}).get('tiers', [])
        pricing_tiers = tiers_data
    else:
        # Fallback hardcoded values
        pricing_tiers = [
            {'capacity': 100, 'price': Decimal('15.00'), 'name': 'Up to 100 tickets'},
            {'capacity': 200, 'price': Decimal('25.00'), 'name': 'Up to 200 tickets'},
            {'capacity': 300, 'price': Decimal('40.00'), 'name': 'Up to 300 tickets'},
            {'capacity': 400, 'price': Decimal('55.00'), 'name': 'Up to 400 tickets'},
            {'capacity': 500, 'price': Decimal('70.00'), 'name': 'Up to 500 tickets'},
        ]
    
    context = {
        'pricing_tiers': pricing_tiers,
        'sumup_rate': 2.50,
        'contact_email': getattr(settings, 'LARGE_EVENT_CONTACT_EMAIL', 'admin@coderra.je'),
    }
    
    return render(request, 'pricing.html', context)

class EventListView(ListView):
    model = Event
    template_name = "events/home.html"
    context_object_name = "events"
    paginate_by = 12

class EventDetailView(DetailView):
    model = Event
    template_name = "events/detail.html"
    context_object_name = "event"


# Event Summary Report Views
@login_required
def event_summary_report(request, event_id):
    """Generate simple event summary report for organisers"""
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta

    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    # Get all completed orders for this event
    completed_items = OrderItem.objects.filter(
        event=event,
        order__status='completed'
    ).select_related('order', 'order__user')

    # Calculate basic stats
    total_tickets_sold = completed_items.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    total_orders = completed_items.values('order').distinct().count()

    # Calculate total revenue
    total_revenue = Decimal('0.00')
    for item in completed_items:
        total_revenue += item.price * item.quantity

    # Calculate fees based on capacity
    if event.capacity <= 50:
        platform_fee = Decimal('15.00')
    elif event.capacity <= 100:
        platform_fee = Decimal('30.00')
    elif event.capacity <= 250:
        platform_fee = Decimal('50.00')
    elif event.capacity <= 400:
        platform_fee = Decimal('60.00')
    else:
        platform_fee = Decimal('70.00')

    processing_fee = total_revenue * Decimal('0.025')  # 2.5%
    net_revenue = total_revenue - platform_fee - processing_fee

    # Sales timeline (by week)
    timeline = []
    if completed_items.exists():
        first_sale = completed_items.order_by('order__created_at').first().order.created_at
        weeks_since_first = (timezone.now() - first_sale).days // 7 + 1

        for week_num in range(1, min(weeks_since_first + 1, 5)):  # Max 4 weeks
            week_start = first_sale + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(weeks=1)

            week_sales = completed_items.filter(
                order__created_at__gte=week_start,
                order__created_at__lt=week_end
            ).aggregate(total=Sum('quantity'))['total'] or 0

            if week_sales > 0:
                timeline.append({
                    'week': f'Week {week_num}',
                    'sales': week_sales
                })

    # Top customers (by quantity)
    top_customers = []
    customer_sales = {}

    for item in completed_items:
        user = item.order.user
        customer_name = user.get_full_name() or user.email
        customer_sales[customer_name] = customer_sales.get(customer_name, 0) + item.quantity

    # Sort and get top 5
    sorted_customers = sorted(customer_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    top_customers = [{'name': name, 'tickets': qty} for name, qty in sorted_customers]

    context = {
        'event': event,
        'total_tickets_sold': total_tickets_sold,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'platform_fee': platform_fee,
        'processing_fee': processing_fee,
        'net_revenue': net_revenue,
        'timeline': timeline,
        'top_customers': top_customers,
        'capacity': event.capacity,
        'percentage_sold': round((total_tickets_sold / event.capacity * 100), 1) if event.capacity > 0 else 0,
        'now': timezone.now(),
    }

    return render(request, 'events/event_summary_report.html', context)


@login_required
def export_guest_list(request, event_id):
    """Export guest list as CSV"""
    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    # Create response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{event.slug}_guest_list.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer Name', 'Email', 'Quantity', 'Order Date', 'Total Paid'])

    # Get all completed orders
    completed_items = OrderItem.objects.filter(
        event=event,
        order__status='completed'
    ).select_related('order', 'order__user').order_by('order__created_at')

    for item in completed_items:
        order = item.order
        user = order.user
        writer.writerow([
            order.order_number,
            user.get_full_name() or 'N/A',
            user.email,
            item.quantity,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            f'£{item.price * item.quantity:.2f}'
        ])

    return response

