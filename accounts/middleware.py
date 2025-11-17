from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class EmailVerificationMiddleware:
    """Enhanced middleware to enforce email verification for protected actions."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get current path first for early exemptions
        path = request.path

        # Skip middleware for health check endpoint (Railway monitoring)
        if path == '/health/':
            return self.get_response(request)

        # Skip middleware for non-authenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip middleware for already verified users
        if request.user.email_verified:
            return self.get_response(request)

        # Skip middleware for superusers
        if request.user.is_superuser:
            return self.get_response(request)

        # Views that require strict email verification
        protected_paths = [
            '/events/create-event/',
            '/events/my-events/',
            '/payments/checkout/',
            '/orders/my-orders/',
            '/accounts/organiser-dashboard/',
            '/subscriptions/',
        ]

        # Views that should be accessible to unverified users
        allowed_paths = [
            '/accounts/verify/',
            '/accounts/resend-verification/',
            '/accounts/logout/',
            '/accounts/login/',
            '/accounts/register/',
            '/accounts/password-reset/',
            '/events/',
            '/cart/',
            '/admin/',
            '/',  # Homepage
        ]

        # Check if current path requires verification
        is_protected = any(path.startswith(protected_path) for protected_path in protected_paths)
        is_allowed = any(path.startswith(allowed_path) for allowed_path in allowed_paths)

        if is_protected:
            # Block access to protected views
            messages.warning(
                request,
                'Please verify your email address to access this feature. '
                f'<a href="{reverse("accounts:resend_verification")}">Resend verification email</a>',
                extra_tags='safe'
            )
            return redirect('accounts:resend_verification')

        elif not is_allowed and not path.startswith('/static/') and not path.startswith('/media/'):
            # Show gentle reminder for other views (once per session)
            warning_key = 'email_verification_warning_shown'
            if not request.session.get(warning_key, False):
                messages.info(
                    request,
                    'Don\'t forget to verify your email address to access all features. '
                    f'<a href="{reverse("accounts:resend_verification")}">Verify now</a>',
                    extra_tags='safe'
                )
                request.session[warning_key] = True

        return self.get_response(request)