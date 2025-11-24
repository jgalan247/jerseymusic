"""SumUp OAuth integration views for artists."""

import uuid
import logging
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from .models import ArtistProfile
from payments import sumup as sumup_api

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class SumUpConnectView(View):
    """Initiate SumUp OAuth connection for artist."""

    def dispatch(self, request, *args, **kwargs):
        # Ensure user is an artist
        if request.user.user_type != 'artist':
            messages.error(request, "Only artists can connect to SumUp.")
            return redirect('accounts:profile')

        # Get or create artist profile
        try:
            self.artist_profile = request.user.artistprofile
        except ArtistProfile.DoesNotExist:
            messages.error(request, "Artist profile not found. Please complete your profile first.")
            return redirect('accounts:profile')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Show SumUp connection page or initiate OAuth flow."""
        # Check if user confirmed they want to connect (clicked the button)
        confirm = request.GET.get('confirm')

        if not confirm:
            # Show the informational page with explanation and connect button
            # Store the 'next' URL parameter so it's preserved through the flow
            next_url = request.GET.get('next', '')
            context = {
                'next_url': next_url
            }
            return render(request, 'accounts/sumup_connect.html', context)

        # User confirmed - proceed with OAuth flow
        # Validate redirect URI is configured (will auto-configure from SITE_URL if not set)
        if not settings.SUMUP_REDIRECT_URI:
            logger.error("SUMUP_REDIRECT_URI not configured in environment variables")
            messages.error(
                request,
                "SumUp integration is not properly configured. Please contact support."
            )
            return redirect('accounts:dashboard')

        # Log the OAuth initiation
        logger.info(f"User {request.user.id} initiating SumUp OAuth flow")
        logger.info(f"Configured redirect URI: {settings.SUMUP_REDIRECT_URI}")

        try:
            # Store the 'next' URL parameter for post-OAuth redirect
            next_url = request.GET.get('next', '')
            if next_url:
                request.session['sumup_oauth_next'] = next_url
                logger.info(f"Stored next URL for post-OAuth redirect: {next_url}")

            # Generate state parameter for security
            state = f"{request.user.id}:{uuid.uuid4()}"
            request.session['sumup_oauth_state'] = state

            # Redirect to SumUp OAuth authorization
            auth_url = sumup_api.oauth_authorize_url(state)

            # Validate URL was generated successfully
            if not auth_url:
                logger.error(f"SumUp OAuth URL generation failed for user {request.user.id}")
                messages.error(request, "Failed to generate SumUp authorization URL. Please check configuration.")
                return redirect('accounts:dashboard')

            logger.info(f"Redirecting user {request.user.id} to SumUp OAuth: {auth_url[:100]}...")
            return redirect(auth_url)

        except Exception as e:
            logger.error(f"Error starting SumUp OAuth for user {request.user.id}: {e}")
            messages.error(request, "Failed to start SumUp connection. Please try again or contact support.")
            return redirect('accounts:dashboard')


@method_decorator(login_required, name='dispatch')
class SumUpCallbackView(View):
    """Handle SumUp OAuth callback."""

    def get(self, request):
        """Process OAuth callback from SumUp."""
        # Log all callback parameters for debugging
        logger.info("=" * 80)
        logger.info("SumUp OAuth Callback Received")
        logger.info(f"User: {request.user.id} ({request.user.email})")
        logger.info(f"Query parameters: {dict(request.GET)}")
        logger.info(f"Session state: {request.session.get('sumup_oauth_state', 'NOT SET')}")
        logger.info("=" * 80)

        # Verify state parameter
        state_sent = request.session.get('sumup_oauth_state')
        state_received = request.GET.get('state')

        if not state_sent:
            logger.error("No OAuth state found in session - possible session timeout")
            messages.error(
                request,
                "Session expired. Please try connecting to SumUp again."
            )
            return redirect('accounts:dashboard')

        if state_sent != state_received:
            logger.error(
                f"OAuth state mismatch - Expected: {state_sent}, Received: {state_received}"
            )
            messages.error(request, "Invalid OAuth state. Please try connecting again.")
            return redirect('accounts:dashboard')

        # Get authorization code
        code = request.GET.get('code')
        error = request.GET.get('error')
        error_description = request.GET.get('error_description', '')

        if error:
            logger.error(f"SumUp OAuth error: {error} - {error_description}")
            messages.error(
                request,
                f"SumUp authorization failed: {error_description or error}"
            )
            return redirect('accounts:dashboard')

        if not code:
            logger.error("No authorization code received from SumUp")
            messages.error(request, "No authorization code received from SumUp.")
            return redirect('accounts:dashboard')

        try:
            # Extract user ID from state
            user_id = int(state_received.split(':')[0])
            if user_id != request.user.id:
                logger.error(f"User ID mismatch in OAuth state - Expected: {request.user.id}, Got: {user_id}")
                messages.error(request, "User ID mismatch in OAuth state.")
                return redirect('accounts:dashboard')

            # Get artist profile
            artist_profile = get_object_or_404(ArtistProfile, user=request.user)

            logger.info(f"Exchanging authorization code for user {request.user.id}")

            # Exchange code for tokens
            token_data = sumup_api.exchange_code_for_tokens(code)
            logger.info(f"Successfully received tokens for user {request.user.id}")

            # Get merchant information
            merchant_info = sumup_api.get_merchant_info(token_data['access_token'])
            logger.info(f"Retrieved merchant info for user {request.user.id}: {merchant_info.get('merchant_code', 'N/A')}")

            # Update artist profile with OAuth tokens
            artist_profile.update_sumup_connection(token_data)
            artist_profile.sumup_merchant_code = merchant_info.get('merchant_code', '')
            artist_profile.save()

            # Clear session state
            if 'sumup_oauth_state' in request.session:
                del request.session['sumup_oauth_state']

            # Get the stored 'next' URL for redirect
            next_url = request.session.pop('sumup_oauth_next', None)

            messages.success(
                request,
                f"Successfully connected to SumUp! Merchant: {merchant_info.get('business_name', 'Your Business')}"
            )

            logger.info(f"Artist {request.user.id} successfully connected to SumUp")

            # Redirect to the original destination or dashboard
            if next_url:
                logger.info(f"Redirecting to stored next URL: {next_url}")
                return redirect(next_url)
            return redirect('accounts:dashboard')

        except requests.exceptions.RequestException as e:
            # Network errors when communicating with SumUp API
            logger.error(f"Network error during SumUp OAuth for user {request.user.id}: {e}")
            messages.error(
                request,
                "Network error connecting to SumUp. Please check your internet connection and try again."
            )
            return redirect('accounts:dashboard')
        except Exception as e:
            logger.error(f"SumUp OAuth callback error for user {request.user.id}: {e}")
            messages.error(request, "Failed to connect to SumUp. Please try again.")
            return redirect('accounts:dashboard')


@method_decorator(login_required, name='dispatch')
class SumUpDisconnectView(View):
    """Disconnect SumUp integration for artist."""

    def post(self, request):
        """Disconnect SumUp OAuth connection."""
        if request.user.user_type != 'artist':
            messages.error(request, "Only artists can disconnect SumUp.")
            return redirect('accounts:profile')

        try:
            artist_profile = request.user.artistprofile

            # Store connection info for logging
            was_connected = artist_profile.is_sumup_connected
            merchant_code = artist_profile.sumup_merchant_code

            # Disconnect SumUp
            artist_profile.disconnect_sumup()

            if was_connected:
                messages.success(request, "Successfully disconnected from SumUp.")
                logger.info(f"Artist {request.user.id} disconnected from SumUp (merchant: {merchant_code})")
            else:
                messages.info(request, "SumUp was not connected.")

        except ArtistProfile.DoesNotExist:
            messages.error(request, "Artist profile not found.")
        except Exception as e:
            logger.error(f"SumUp disconnect error for user {request.user.id}: {e}")
            messages.error(request, "Failed to disconnect SumUp. Please try again.")

        return redirect('accounts:dashboard')


@method_decorator(login_required, name='dispatch')
class SumUpStatusView(View):
    """Check and refresh SumUp connection status."""

    def get(self, request):
        """Check SumUp connection status and refresh if needed."""
        if request.user.user_type != 'artist':
            messages.error(request, "Only artists can check SumUp status.")
            return redirect('accounts:profile')

        try:
            artist_profile = request.user.artistprofile

            if not artist_profile.is_sumup_connected:
                messages.info(request, "SumUp is not connected.")
                return redirect('accounts:dashboard')

            # Check if token needs refreshing
            if artist_profile.sumup_token_expired:
                try:
                    # Refresh the token
                    new_token_data = sumup_api.refresh_access_token_direct(
                        artist_profile.sumup_refresh_token
                    )
                    artist_profile.update_sumup_connection(new_token_data)
                    messages.success(request, "SumUp connection refreshed successfully.")

                except Exception as e:
                    logger.error(f"Token refresh failed for artist {request.user.id}: {e}")
                    artist_profile.sumup_connection_status = 'expired'
                    artist_profile.save()
                    messages.warning(
                        request,
                        "SumUp connection has expired. Please reconnect to continue receiving payments."
                    )
            else:
                messages.success(request, "SumUp connection is active and healthy.")

        except ArtistProfile.DoesNotExist:
            messages.error(request, "Artist profile not found.")
        except Exception as e:
            logger.error(f"SumUp status check error for user {request.user.id}: {e}")
            messages.error(request, "Failed to check SumUp status.")

        return redirect('accounts:dashboard')


def sumup_connection_required(view_func):
    """Decorator to ensure artist has active SumUp connection."""
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'artistprofile'):
            messages.error(request, "Artist profile required.")
            return redirect('accounts:profile')

        artist_profile = request.user.artistprofile

        if not artist_profile.is_sumup_connected:
            messages.warning(
                request,
                "Please connect your SumUp account to receive payments."
            )
            return redirect('accounts:sumup_connect')

        if artist_profile.sumup_token_expired:
            messages.warning(
                request,
                "Your SumUp connection has expired. Please reconnect."
            )
            return redirect('accounts:sumup_connect')

        return view_func(request, *args, **kwargs)

    return wrapper
