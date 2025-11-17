
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
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from functools import wraps

# Import models
from .forms import (
    CustomerRegistrationForm, ArtistRegistrationForm, ResendVerificationForm,
    CustomUserCreationForm, LoginForm, CustomerProfileForm,
    ArtistProfileForm, UserUpdateForm
)
from .models import User, CustomerProfile, ArtistProfile, EmailVerificationToken
from .email_utils import send_verification_email, send_welcome_email, resend_verification_email

# Import from other apps
from orders.models import Order, OrderItem, RefundRequest
from events.models import Event  # ← ADD THIS LINE

# ← ADD THIS DECORATOR
def user_type_required(user_type):
    """Decorator to check if user has the required user_type"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.user_type != user_type:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('/')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Note: send_verification_email function now imported from email_utils


def register_customer(request):
    """Customer registration view with comprehensive debugging"""
    import logging
    logger = logging.getLogger(__name__)

    print(f"🔍 REGISTRATION DEBUG: Customer registration view called")
    print(f"🔍 Request method: {request.method}")
    print(f"🔍 User authenticated: {request.user.is_authenticated}")

    if request.user.is_authenticated:
        print(f"🔍 User already authenticated, redirecting")
        return redirect('/')

    if request.method == 'POST':
        print(f"🔍 POST request received")
        print(f"🔍 POST data keys: {list(request.POST.keys())}")
        print(f"🔍 POST data: {dict(request.POST)}")

        form = CustomerRegistrationForm(request.POST)
        print(f"🔍 Form created: {form.__class__.__name__}")

        try:
            is_valid = form.is_valid()
            print(f"🔍 Form validation result: {is_valid}")

            if not is_valid:
                print(f"❌ FORM VALIDATION FAILED!")
                print(f"❌ Form errors: {form.errors}")
                print(f"❌ Form non-field errors: {form.non_field_errors()}")
                for field_name, field_errors in form.errors.items():
                    print(f"❌ Field '{field_name}' errors: {field_errors}")
            else:
                print(f"✅ Form validation successful!")

                try:
                    print(f"🔍 Attempting to save form...")
                    user = form.save()
                    print(f"✅ User created successfully!")
                    print(f"✅ User ID: {user.id}")
                    print(f"✅ User email: {user.email}")
                    print(f"✅ User type: {user.user_type}")

                    # Send verification email
                    print(f"🔍 Attempting to send verification email...")
                    email_sent = send_verification_email(user, request)
                    if email_sent:
                        print(f"✅ Verification email sent successfully!")
                    else:
                        print(f"❌ Verification email failed to send (check logs above)")
                        logger.error(f"Verification email failed for {user.email}")

                    messages.success(
                        request,
                        'Registration successful! Please check your email to verify your account.'
                    )
                    print(f"✅ Success message added")
                    print(f"🔍 Redirecting to login...")
                    return redirect('accounts:login')

                except Exception as e:
                    print(f"❌ USER CREATION FAILED: {e}")
                    logger.error(f"User creation failed: {e}")
                    messages.error(request, f'Registration failed: {str(e)}')

        except Exception as e:
            print(f"❌ FORM VALIDATION ERROR: {e}")
            logger.error(f"Form validation error: {e}")
            messages.error(request, f'Form validation error: {str(e)}')
    else:
        print(f"🔍 GET request - creating empty form")
        form = CustomerRegistrationForm()
        print(f"🔍 Empty form created: {form.__class__.__name__}")

    print(f"🔍 Rendering template with form")
    return render(request, 'accounts/register_customer.html', {'form': form})


def register_organiser(request):
    """Event organiser registration view with comprehensive debugging"""
    import logging
    logger = logging.getLogger(__name__)

    print(f"🔍 REGISTRATION DEBUG: Organiser registration view called")
    print(f"🔍 Request method: {request.method}")
    print(f"🔍 User authenticated: {request.user.is_authenticated}")

    if request.user.is_authenticated:
        print(f"🔍 User already authenticated, redirecting")
        return redirect('/')

    if request.method == 'POST':
        print(f"🔍 POST request received")
        print(f"🔍 POST data keys: {list(request.POST.keys())}")
        print(f"🔍 POST data: {dict(request.POST)}")

        form = ArtistRegistrationForm(request.POST)
        print(f"🔍 Form created: {form.__class__.__name__}")

        try:
            is_valid = form.is_valid()
            print(f"🔍 Form validation result: {is_valid}")

            if not is_valid:
                print(f"❌ FORM VALIDATION FAILED!")
                print(f"❌ Form errors: {form.errors}")
                print(f"❌ Form non-field errors: {form.non_field_errors()}")
                for field_name, field_errors in form.errors.items():
                    print(f"❌ Field '{field_name}' errors: {field_errors}")
            else:
                print(f"✅ Form validation successful!")

                try:
                    print(f"🔍 Attempting to save form...")
                    user = form.save()
                    print(f"✅ User created successfully!")
                    print(f"✅ User ID: {user.id}")
                    print(f"✅ User email: {user.email}")
                    print(f"✅ User type: {user.user_type}")

                    # Send verification email
                    print(f"🔍 Attempting to send verification email...")
                    email_sent = send_verification_email(user, request)
                    if email_sent:
                        print(f"✅ Verification email sent successfully!")
                    else:
                        print(f"❌ Verification email failed to send (check logs above)")
                        logger.error(f"Verification email failed for {user.email}")

                    messages.success(
                        request,
                        'Registration successful! Please check your email to verify your account. '
                        'After verification, you can start creating events right away!'
                    )
                    print(f"✅ Success message added")
                    print(f"🔍 Redirecting to login...")
                    return redirect('accounts:login')

                except Exception as e:
                    print(f"❌ USER CREATION FAILED: {e}")
                    logger.error(f"User creation failed: {e}")
                    messages.error(request, f'Registration failed: {str(e)}')

        except Exception as e:
            print(f"❌ FORM VALIDATION ERROR: {e}")
            logger.error(f"Form validation error: {e}")
            messages.error(request, f'Form validation error: {str(e)}')
    else:
        print(f"🔍 GET request - creating empty form")
        form = ArtistRegistrationForm()
        print(f"🔍 Empty form created: {form.__class__.__name__}")

    print(f"🔍 Rendering template with form")
    return render(request, 'accounts/register_organiser.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('events:home')
    
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
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            
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
            # Redirect to organiser dashboard
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



#from django.utils import timezone
#from django.db.models import Sum, Count, Q

@login_required
@user_type_required('artist')
def organiser_dashboard(request):
    """Organiser dashboard view with stats and quick actions"""

    # Get artist profile and check SumUp connection
    try:
        artist_profile = request.user.artistprofile
    except ArtistProfile.DoesNotExist:
        artist_profile = None

    # Get organiser's events
    user_events = Event.objects.filter(organiser=request.user)

    # Calculate stats
    total_events = user_events.count()
    
    # Use event_date instead of date
    upcoming_events = user_events.filter(
        event_date__gte=timezone.now().date(),
        status='published'
    ).count()
    
    # Get recent events (last 5)
    recent_events = user_events.order_by('-created_at')[:5]
    
    # Add tickets_sold and other info to each event
    for event in recent_events:
        # Calculate tickets sold from completed orders
        tickets_sold = OrderItem.objects.filter(
            event=event,
            order__status='completed'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        event.tickets_sold = tickets_sold
        
        # Add status color for badge
        status_colors = {
            'draft': 'secondary',
            'published': 'success',
            'cancelled': 'danger',
            'completed': 'info'
        }
        event.status_color = status_colors.get(event.status, 'secondary')
    
    # Calculate total tickets sold and revenue across ALL events
    total_tickets_sold = 0
    total_revenue = 0
    
    for event in user_events:
        # Get completed order items for this event
        completed_items = OrderItem.objects.filter(
            event=event,
            order__status='completed'
        )

        for item in completed_items:
            total_tickets_sold += item.quantity
            total_revenue += item.price * item.quantity
    
    context = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'recent_events': recent_events,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
        'artist_profile': artist_profile,  # Add artist profile for SumUp connection status
    }

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