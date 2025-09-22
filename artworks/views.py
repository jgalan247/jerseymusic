from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from artworks.models import Artwork, ArtworkImage, Category
from artworks.forms import ArtworkUploadForm
from django.conf import settings
from django.db.models import Count
from django.views.generic import DetailView
from .models import Artwork
from django.views.generic import ListView, DetailView
from .models import Artwork

@login_required
def artwork_upload(request):
    # Check if user is an artist
    if request.user.user_type != 'artist':
        messages.error(request, "Only artists can upload artwork")
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
        form = ArtworkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = form.save(commit=False)
            artwork.artist = request.user
            artwork.status = 'draft'  # Needs admin approval
            artwork.save()
            
            # Save main image
            if 'main_image' in request.FILES:
                ArtworkImage.objects.create(
                    artwork=artwork,
                    image=request.FILES['main_image'],
                    is_primary=True,
                    order=1
                )
            
            messages.success(request, f'"{artwork.title}" uploaded! Pending admin approval.')
            return redirect('artworks:my_artworks')
    else:
        form = ArtworkUploadForm()
    
    return render(request, 'artworks/upload.html', {'form': form})

@login_required
def my_artworks(request):
    if request.user.user_type != 'artist':
        messages.error(request, "Only artists can view this page")
        return redirect('/')
    
    artworks = Artwork.objects.filter(artist=request.user).order_by('-created_at')
    return render(request, 'artworks/my_artworks.html', {'artworks': artworks})

def gallery(request):
    artworks = Artwork.objects.filter(status='active', is_available=True)
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        artworks = artworks.filter(category__slug=category)
    
    # Filter by artist
    artist_id = request.GET.get('artist')
    if artist_id:
        artworks = artworks.filter(artist_id=artist_id)
    
    # Sort by price
    sort = request.GET.get('sort')
    if sort == 'price_low':
        artworks = artworks.order_by('price')
    elif sort == 'price_high':
        artworks = artworks.order_by('-price')
    else:
        artworks = artworks.order_by('-created_at')
    
    return render(request, 'artworks/gallery.html', {'artworks': artworks})

def artwork_detail(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    if artwork.status != 'active' and artwork.artist != request.user:
        messages.error(request, "This artwork is not available")
        return redirect('artworks:gallery')
    return render(request, 'artworks/detail.html', {'artwork': artwork})

# Add this updated home view to artworks/views.py

def home(request):
    """Homepage view with featured artworks and artists."""
    from accounts.models import User
    
    # Get featured artworks (active, available, and featured or recent)
    featured_artworks = Artwork.objects.filter(
        status='active',
        is_available=True
    ).select_related('artist', 'category').order_by('-featured', '-created_at')[:8]
    
    # If no featured artworks, just get the latest ones
    if not featured_artworks:
        featured_artworks = Artwork.objects.filter(
            status='active',
            is_available=True
        ).select_related('artist', 'category').order_by('-created_at')[:8]
    
    # Get featured artists (those with active artworks)
    featured_artists = User.objects.filter(
        user_type='artist',
        is_active=True,
        artworks__status='active'
    ).distinct().annotate(
        artwork_count=Count('artworks')
    ).order_by('-artwork_count')[:4]
    
    context = {
        'featured_artworks': featured_artworks,
        'featured_artists': featured_artists,
    }
    
    return render(request, 'artworks/home.html', context)

# Add these at the end of artworks/views.py

def about(request):
    """About Us page."""
    return render(request, 'artworks/about.html')

def contact(request):
    """Contact page."""
    return render(request, 'artworks/contact.html')

def artists_list(request):
    """List all artists."""
    from accounts.models import User
    artists = User.objects.filter(user_type='artist', is_active=True)
    return render(request, 'artworks/artists.html', {'artists': artists})

def privacy(request):
    """Privacy policy page."""
    return render(request, 'artworks/privacy.html')

def terms(request):
    """Terms and conditions page."""
    return render(request, 'artworks/terms.html')

class ArtworkListView(ListView):
    model = Artwork
    template_name = "artworks/home.html"
    context_object_name = "artworks"
    paginate_by = 12

class ArtworkDetailView(DetailView):
    model = Artwork
    template_name = "artworks/detail.html"
    context_object_name = "artwork"
