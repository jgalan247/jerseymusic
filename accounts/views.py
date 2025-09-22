from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.views import View
from django.http import HttpResponse
from orders.models import Order 
from orders.models import RefundRequest
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper

from .forms import (
    CustomerRegistrationForm, ArtistRegistrationForm, ResendVerificationForm,
    CustomUserCreationForm, LoginForm, CustomerProfileForm, 
    ArtistProfileForm, UserUpdateForm
)
from .models import User, CustomerProfile, ArtistProfile
from .tokens import email_verification_token

from django.conf import settings


def send_verification_email(request, user):
    """Helper function to send verification email"""
    current_site = get_current_site(request)
    subject = 'Verify your email - Jersey Artwork'
    
    # Generate token and uid
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create verification link
    verification_link = f"http://{current_site.domain}{reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})}"
    
    # Render email content
    message = render_to_string('accounts/email/verification_email.html', {
        'user': user,
        'domain': current_site.domain,
        'verification_link': verification_link,
    })
    
    # Send email
    send_mail(
        subject,
        message,
        'noreply@jerseyartwork.je',
        [user.email],
        html_message=message,
        fail_silently=False,
    )


def register_customer(request):
    """Customer registration view"""
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send verification email
            send_verification_email(request, user)
            
            messages.success(
                request, 
                'Registration successful! Please check your email to verify your account.'
            )
            return redirect('accounts:login')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'accounts/register_customer.html', {'form': form})


def register_artist(request):
    """Artist registration view"""
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        form = ArtistRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send verification email
            send_verification_email(request, user)
            
            messages.success(
                request, 
                'Registration successful! Please check your email to verify your account. '
                'After verification, you can choose a subscription plan to start selling.'
            )
            return redirect('accounts:login')
    else:
        form = ArtistRegistrationForm()
    
    return render(request, 'accounts/register_artist.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('artworks:gallery')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Authenticate using email (username field)
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if not user.email_verified:
                messages.warning(
                    request,
                    'Please verify your email before logging in. '
                    f'<a href="{reverse("accounts:resend_verification")}">Resend verification email</a>',
                    extra_tags='safe'  # Allows HTML in message
                )
                return render(request, 'accounts/login.html')
            
            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect to next or default
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Redirect based on user type
            if user.user_type == 'artist':
                return redirect('artworks:my_artworks')
            return redirect('artworks:gallery')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/')


@login_required
def profile_view(request):
    """User profile view with forms for editing"""
    user_form = UserUpdateForm(instance=request.user)
    profile_form = None
    profile = None
    
    # Get or create profile based on user type
    if request.user.user_type == 'customer':
        profile, created = CustomerProfile.objects.get_or_create(user=request.user)
        profile_form = CustomerProfileForm(instance=profile)
    elif request.user.user_type == 'artist':
        profile, created = ArtistProfile.objects.get_or_create(
            user=request.user,
            defaults={'display_name': request.user.get_full_name()}
        )
        profile_form = ArtistProfileForm(instance=profile)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        
        if request.user.user_type == 'customer':
            profile_form = CustomerProfileForm(request.POST, instance=profile)
        elif request.user.user_type == 'artist':
            profile_form = ArtistProfileForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('accounts:profile')
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    
    # Use a generic profile template or user-type specific
    return render(request, 'accounts/profile.html', context)


def verify_email(request, uidb64, token):
    """Verify email address using token from email link"""
    try:
        # Decode the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and email_verification_token.check_token(user, token):
        # Token is valid, verify the email
        user.email_verified = True
        user.save()
        
        messages.success(
            request, 
            'Your email has been verified successfully! You can now log in.'
        )
        
        # Log the user in automatically
        login(request, user)
        
        # Redirect based on user type
        if user.user_type == 'artist':
            # Check if artist has subscription
            if not hasattr(user, 'subscription') or not user.subscription.is_active:
                return redirect('subscriptions:plans')
            return redirect('accounts:artist_dashboard')
        else:
            return redirect('/')
    else:
        messages.error(
            request, 
            'Invalid verification link. The link may have expired or been used already.'
        )
        return redirect('accounts:resend_verification')


def resend_verification(request):
    """Resend verification email"""
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Send new verification email
            send_verification_email(request, user)
            
            messages.success(
                request,
                f'Verification email sent to {email}. Please check your inbox.'
            )
            return redirect('accounts:login')
    else:
        form = ResendVerificationForm()
    
    return render(request, 'accounts/resend_verification.html', {'form': form})



@login_required
def artist_dashboard(request):
    """Artist dashboard with subscription info."""
    if request.user.user_type != 'artist':
        messages.error(request, 'Access denied. Artists only.')
        return redirect('/')
    
    # Check subscription status
    subscription = getattr(request.user, 'subscription', None)
    
    context = {
        'user': request.user,
        'subscription': subscription,
        'subscription_price': settings.SUBSCRIPTION_CONFIG['MONTHLY_PRICE'],
        'can_upload': subscription and subscription.can_upload_artwork if subscription else False,
        'artwork_count': request.user.artworks.filter(status='active').count(),
        'max_artworks': settings.SUBSCRIPTION_CONFIG['FEATURES']['MAX_ARTWORKS'],
        'recent_orders': Order.objects.filter(
            items__artwork__artist=request.user
        ).distinct().order_by('-created_at')[:10]
    }
    
    # No commission calculation needed - subscription model
    
    return render(request, 'accounts/artist_dashboard.html', context)

class ArtistProfileDetailView(DetailView):
    """Public artist profile view"""
    model = ArtistProfile
    template_name = 'accounts/artist_detail.html'
    context_object_name = 'artist'
    
    def get_queryset(self):
        return ArtistProfile.objects.filter(is_approved=True).select_related('user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add artist's artworks
        context['artworks'] = self.object.artworks.filter(status='active')[:12]
        return context