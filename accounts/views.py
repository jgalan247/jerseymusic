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
from .models import User, CustomerProfile, ArtistProfile, EmailVerificationToken
from .email_utils import send_verification_email, send_welcome_email, resend_verification_email

from django.conf import settings


# Note: send_verification_email function now imported from email_utils


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


def register_organiser(request):
    """Event organiser registration view"""
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
                'After verification, you can choose a subscription plan to start creating events.'
            )
            return redirect('accounts:login')
    else:
        form = ArtistRegistrationForm()

    return render(request, 'accounts/register_organiser.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('events:gallery')
    
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
                return redirect('events:my_events')
            return redirect('events:events_list')
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


def verify_email(request, token):
    """Verify email address using token from email link"""
    try:
        # Get the token object
        verification_token = EmailVerificationToken.objects.get(token=token)

        if not verification_token.is_valid:
            if verification_token.is_expired:
                messages.error(
                    request,
                    'Verification link has expired. Please request a new one.'
                )
            else:
                messages.error(
                    request,
                    'This verification link has already been used.'
                )
            return redirect('accounts:resend_verification')

        # Token is valid, verify the email
        user = verification_token.user
        user.email_verified = True
        user.save()

        # Mark token as used
        verification_token.mark_as_used()

        # Send welcome email
        send_welcome_email(user, request)

        messages.success(
            request,
            'Your email has been verified successfully! Welcome to Jersey Events.'
        )

        # Log the user in automatically
        login(request, user)

        # Redirect based on user type
        if user.user_type == 'artist':
            # Check if organiser has subscription
            if not hasattr(user, 'subscription') or not user.subscription.is_active:
                return redirect('subscriptions:plans')
            return redirect('accounts:organiser_dashboard')
        else:
            return redirect('events:events_list')

    except EmailVerificationToken.DoesNotExist:
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
            try:
                user = User.objects.get(email=email)

                if user.email_verified:
                    messages.info(
                        request,
                        'This email address is already verified. You can log in normally.'
                    )
                    return redirect('accounts:login')

                # Use new resend function with rate limiting
                success, message = resend_verification_email(user, request)

                if success:
                    messages.success(request, message)
                    return redirect('accounts:login')
                else:
                    messages.error(request, message)

            except User.DoesNotExist:
                # Don't reveal if email exists or not
                messages.error(
                    request,
                    'If an account with this email exists, a verification email has been sent.'
                )
    else:
        form = ResendVerificationForm()

    return render(request, 'accounts/resend_verification.html', {'form': form})



@login_required
def organiser_dashboard(request):
    """Event organiser dashboard with subscription info."""
    if request.user.user_type != 'artist':
        messages.error(request, 'Access denied. Event organisers only.')
        return redirect('/')

    # Check subscription status
    subscription = getattr(request.user, 'subscription', None)

    context = {
        'user': request.user,
        'subscription': subscription,
        'subscription_price': settings.SUBSCRIPTION_CONFIG['MONTHLY_PRICE'],
        'can_create_events': subscription and subscription.can_upload_artwork if subscription else False,
        'event_count': request.user.events.filter(status='published').count(),
        'max_events': settings.SUBSCRIPTION_CONFIG['FEATURES']['MAX_ARTWORKS'],
        'recent_orders': Order.objects.filter(
            items__event__organiser=request.user
        ).distinct().order_by('-created_at')[:10]
    }

    # No commission calculation needed - subscription model

    return render(request, 'accounts/organiser_dashboard.html', context)

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