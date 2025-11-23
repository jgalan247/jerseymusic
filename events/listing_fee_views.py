"""
Views for handling listing fee payments.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.db import transaction

from .models import Event, ListingFee, ListingFeeConfig
from payments import sumup as sumup_api
from payments.models import SumUpCheckout

import logging
import json

logger = logging.getLogger(__name__)


@login_required
def pay_listing_fee(request, event_id):
    """Handle listing fee payment for an event."""
    # Get the event
    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    # Check if user is the organizer
    if event.organiser != request.user:
        messages.error(request, "You can only pay listing fees for your own events.")
        return redirect('events:event_detail', pk=event.id)

    # Get or create listing fee
    listing_fee, created = ListingFee.objects.get_or_create(
        event=event,
        defaults={
            'organizer': request.user,
            'amount': ListingFeeConfig.get_config().standard_fee
        }
    )

    # If already paid, redirect to event
    if listing_fee.is_paid:
        messages.info(request, "Listing fee has already been paid for this event.")
        return redirect('events:event_detail', pk=event.id)

    if request.method == 'POST':
        try:
            # Create SumUp checkout for listing fee
            with transaction.atomic():
                checkout_ref = f"listing_fee_{listing_fee.payment_reference}"
                description = f"Jersey Events - Listing fee for '{event.title}'"

                # Create hosted checkout using platform credentials
                checkout_data = sumup_api.create_checkout_simple(
                    amount=float(listing_fee.amount),
                    currency=listing_fee.currency,
                    reference=checkout_ref,
                    description=description,
                    return_url=request.build_absolute_uri(
                        reverse('events:listing_fee_success', kwargs={'event_id': event.id})
                    ),
                    redirect_url=request.build_absolute_uri(
                        reverse('events:listing_fee_success', kwargs={'event_id': event.id})
                    ),
                    enable_hosted_checkout=True
                )

                # Store SumUp checkout ID
                listing_fee.sumup_checkout_id = checkout_data.get('id', '')
                listing_fee.payment_data = checkout_data
                listing_fee.save()

                # Create SumUpCheckout record for tracking
                sumup_checkout = SumUpCheckout.objects.create(
                    order=None,  # This is for listing fees, not orders
                    customer=request.user,
                    amount=listing_fee.amount,
                    currency=listing_fee.currency,
                    description=description,
                    merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
                    checkout_reference=checkout_ref,
                    sumup_checkout_id=checkout_data.get('id', ''),
                    return_url=request.build_absolute_uri(
                        reverse('events:listing_fee_success', kwargs={'event_id': event.id})
                    ),
                    status='created',
                    sumup_response=checkout_data
                )

                # Redirect to SumUp hosted checkout
                hosted_url = checkout_data.get('hosted_checkout_url')
                if not hosted_url:
                    # Fallback URL construction
                    checkout_id = checkout_data.get('id')
                    if checkout_id:
                        hosted_url = f"https://checkout.sumup.com/pay/{checkout_id}"

                if hosted_url:
                    logger.info(f"Redirecting to hosted checkout: {hosted_url}")
                    return redirect(hosted_url)
                else:
                    # Fallback to widget checkout page
                    return redirect('events:listing_fee_checkout', event_id=event.id)

        except Exception as e:
            logger.error(f"Failed to create listing fee checkout for event {event.id}: {e}")
            messages.error(request, "Failed to create payment. Please try again.")

    # Show payment confirmation page
    config = ListingFeeConfig.get_config()
    context = {
        'event': event,
        'listing_fee': listing_fee,
        'config': config,
    }
    return render(request, 'events/listing_fee_payment.html', context)


@login_required
def listing_fee_success(request, event_id):
    """Handle successful listing fee payment (both API and widget flows)."""
    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    # Get checkout_id from widget callback
    checkout_id = request.GET.get('checkout_id')

    try:
        listing_fee = event.listing_fee

        # If we have a checkout_id from widget, use the widget service to handle success
        if checkout_id:
            from payments.widget_service import SumUpWidgetService
            widget_service = SumUpWidgetService()
            result = widget_service.handle_widget_success(checkout_id, request)

            if result['success'] and result['type'] == 'listing_fee':
                messages.success(
                    request,
                    "Listing fee paid successfully! Your event is now published."
                )
            else:
                messages.error(
                    request,
                    f"Payment confirmation failed: {result.get('error', 'Unknown error')}"
                )
        else:
            # Legacy API flow - check payment status via SumUp API
            if listing_fee.sumup_checkout_id:
                try:
                    checkout_status = sumup_api.get_checkout_status(listing_fee.sumup_checkout_id)

                    if checkout_status.get('status') == 'PAID':
                        # Update listing fee status
                        listing_fee.payment_status = 'paid'
                        listing_fee.paid_at = timezone.now()
                        listing_fee.payment_data.update(checkout_status)
                        listing_fee.save()

                        # Update event status to published if it was draft
                        if event.status == 'draft':
                            event.status = 'published'
                            event.save()

                        messages.success(
                            request,
                            "Listing fee paid successfully! Your event is now published."
                        )
                    else:
                        messages.warning(
                            request,
                            "Payment is still processing. We'll update your event status once confirmed."
                        )
                except Exception as e:
                    logger.error(f"Failed to check listing fee payment status: {e}")
                    messages.info(
                        request,
                        "Payment submitted. We'll confirm your event publication once payment is processed."
                    )

    except ListingFee.DoesNotExist:
        messages.error(request, "Listing fee record not found.")

    return redirect('events:event_detail', pk=event.id)


@login_required
def listing_fee_cancel(request, event_id):
    """Handle cancelled listing fee payment."""
    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    messages.info(request, "Listing fee payment was cancelled. Your event remains unpublished.")
    return redirect('events:event_detail', pk=event.id)


@csrf_exempt
def listing_fee_webhook(request):
    """Handle SumUp webhook for listing fee payments."""
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        checkout_id = data.get('id') or data.get('checkout_id')
        status = data.get('status')

        logger.info(f"Listing fee webhook received: checkout_id={checkout_id}, status={status}")

        if not checkout_id:
            return HttpResponse('OK')

        # Find the listing fee by checkout ID
        try:
            listing_fee = ListingFee.objects.get(sumup_checkout_id=checkout_id)
        except ListingFee.DoesNotExist:
            # Might be a regular order payment, not a listing fee
            return HttpResponse('OK')

        # Update listing fee status based on webhook
        if status == 'PAID':
            listing_fee.payment_status = 'paid'
            listing_fee.paid_at = timezone.now()
            listing_fee.payment_data.update(data)
            listing_fee.save()

            # Publish the event
            event = listing_fee.event
            if event.status == 'draft':
                event.status = 'published'
                event.save()

            logger.info(f"Listing fee paid for event {event.id}, event published")

        elif status == 'FAILED':
            listing_fee.payment_status = 'failed'
            listing_fee.payment_data.update(data)
            listing_fee.save()

            logger.info(f"Listing fee payment failed for event {listing_fee.event.id}")

        return HttpResponse('OK')

    except Exception as e:
        logger.error(f"Listing fee webhook error: {e}")
        return HttpResponse('Error', status=500)


@login_required
def listing_fee_status(request, event_id):
    """Check listing fee payment status."""
    event = get_object_or_404(Event, id=event_id, organiser=request.user)

    try:
        listing_fee = event.listing_fee

        if listing_fee.sumup_checkout_id:
            # Check status with SumUp
            checkout_status = sumup_api.get_checkout_status(listing_fee.sumup_checkout_id)

            return JsonResponse({
                'status': 'success',
                'payment_status': listing_fee.payment_status,
                'sumup_status': checkout_status.get('status'),
                'is_paid': listing_fee.is_paid,
                'event_published': event.status == 'published'
            })
        else:
            return JsonResponse({
                'status': 'success',
                'payment_status': listing_fee.payment_status,
                'is_paid': listing_fee.is_paid,
                'event_published': event.status == 'published'
            })

    except ListingFee.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Listing fee not found'
        })
    except Exception as e:
        logger.error(f"Failed to check listing fee status: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to check payment status'
        })