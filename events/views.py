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

@login_required
def create_event(request):
    # Check if user is an artist
    if request.user.user_type != 'artist':
        messages.error(request, "Only organisers can create events")
        return redirect('/')
    
    # DEVELOPMENT MODE - Skip subscription check
    if settings.DEBUG:
        can_upload = True
    else:
        # Production - check subscription
        can_upload = hasattr(request.user, 'subscription') and request.user.subscription.is_active
    
    if not can_upload:
        messages.error(request, "Active subscription required")
        return redirect('subscriptions:plans')
    
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
                f'"{event.title}" created successfully! Please pay the listing fee to publish your event.'
            )
            return redirect('payments:widget_listing_fee', event_id=event.pk)
    else:
        form = EventCreateForm()
    
    return render(request, 'events/upload.html', {'form': form})

@login_required
def my_events(request):
    if request.user.user_type != 'artist':
        messages.error(request, "Only artists can view this page")
        return redirect('/')
    
    events = Event.objects.filter(organiser=request.user).order_by('-created_at')
    return render(request, 'events/my_events.html', {'events': events})

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

