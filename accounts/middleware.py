# accounts/middleware.py

from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect

class EmailVerificationMiddleware:
    """
    Middleware to check if user's email is verified.
    Shows reminder messages for unverified users.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that don't require email verification
        self.exempt_urls = [
            reverse('accounts:login'),
            reverse('accounts:logout'),
            reverse('accounts:register_customer'),
            reverse('accounts:register_artist'),
            reverse('accounts:resend_verification'),
            '/admin/',
        ]
    
    def __call__(self, request):
        # Check if user is authenticated and email is not verified
        if request.user.is_authenticated and not request.user.email_verified:
            
            # Check if current path is exempt
            path = request.path
            is_exempt = any(path.startswith(url) for url in self.exempt_urls)
            
            # Also exempt verification URLs
            if 'verify' in path:
                is_exempt = True
            
            if not is_exempt:
                # Show reminder message once per session
                if not request.session.get('email_verification_reminder_shown', False):
                    messages.warning(
                        request,
                        'Please verify your email address to access all features. '
                        '<a href="{}">Resend verification email</a>'.format(
                            reverse('accounts:resend_verification')
                        )
                    )
                    request.session['email_verification_reminder_shown'] = True
        
        response = self.get_response(request)
        return response


# To activate this middleware, add to settings.py:
# MIDDLEWARE = [
#     # ... other middleware
#     'accounts.middleware.EmailVerificationMiddleware',
# ]