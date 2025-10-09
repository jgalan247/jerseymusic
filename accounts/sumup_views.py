"""SumUp OAuth integration views for artists."""

import uuid
import logging
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
        """Start SumUp OAuth flow."""
        # Generate state parameter for security
        state = f"{request.user.id}:{uuid.uuid4()}"
        request.session['sumup_oauth_state'] = state

        # Redirect to SumUp OAuth authorization
        auth_url = sumup_api.oauth_authorize_url(state)
        return redirect(auth_url)


@method_decorator(login_required, name='dispatch')
class SumUpCallbackView(View):
    """Handle SumUp OAuth callback."""

    def get(self, request):
        """Process OAuth callback from SumUp."""
        # Verify state parameter
        state_sent = request.session.get('sumup_oauth_state')
        state_received = request.GET.get('state')

        if not state_sent or state_sent != state_received:
            messages.error(request, "Invalid OAuth state. Please try connecting again.")
            return redirect('accounts:dashboard')

        # Get authorization code
        code = request.GET.get('code')
        error = request.GET.get('error')

        if error:
            messages.error(request, f"SumUp authorization failed: {error}")
            return redirect('accounts:dashboard')

        if not code:
            messages.error(request, "No authorization code received from SumUp.")
            return redirect('accounts:dashboard')

        try:
            # Extract user ID from state
            user_id = int(state_received.split(':')[0])
            if user_id != request.user.id:
                messages.error(request, "User ID mismatch in OAuth state.")
                return redirect('accounts:dashboard')

            # Get artist profile
            artist_profile = get_object_or_404(ArtistProfile, user=request.user)

            # Exchange code for tokens
            token_data = sumup_api.exchange_code_for_tokens(code)

            # Get merchant information
            merchant_info = sumup_api.get_merchant_info(token_data['access_token'])

            # Update artist profile with OAuth tokens
            artist_profile.update_sumup_connection(token_data)
            artist_profile.sumup_merchant_code = merchant_info.get('merchant_code', '')
            artist_profile.save()

            # Clear session state
            if 'sumup_oauth_state' in request.session:
                del request.session['sumup_oauth_state']

            messages.success(
                request,
                f"Successfully connected to SumUp! Merchant: {merchant_info.get('business_name', 'Your Business')}"
            )

            logger.info(f"Artist {request.user.id} successfully connected to SumUp")
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