import json
import uuid
import requests
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from cart.models import Cart
from orders.models import Order, OrderItem
from events.models import Event
from accounts.models import User
from django.contrib.auth import login
#from accounts.models import User
from .models import SumUpCheckout, SumUpTransaction
from .forms import CheckoutForm, PaymentMethodForm

from django.http import HttpResponse
import datetime

from .models import SumUpCheckout, SumUpTransaction, Artist, ArtistSumUpAuth, Payment, Subscription
from . import sumup as sumup_api
from . import citypay as citypay_api
from events.models import Ticket, EventFee
import logging

logger = logging.getLogger(__name__)




class CheckoutView(FormView):
    """Main checkout view for processing orders."""
    template_name = 'payments/checkout.html'
    form_class = CheckoutForm
    
    def dispatch(self, request, *args, **kwargs):
        # Get or create cart
        self.cart = self.get_cart()
        
        # Check if cart is empty
        if not self.cart or self.cart.items.count() == 0:
            messages.warning(request, "Your cart is empty.")
            return redirect('cart:view')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_cart(self):
        """Get current cart for user or session."""
        if self.request.user.is_authenticated:
            return Cart.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            return Cart.objects.filter(
                session_key=session_key,
                is_active=True
            ).first()
    
    def get_initial(self):
        """Pre-fill form for logged-in users."""
        initial = super().get_initial()
        
        if self.request.user.is_authenticated:
            user = self.request.user
            initial.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
            
            # Check for customer profile
            if hasattr(user, 'customerprofile'):
                profile = user.customerprofile
                initial.update({
                    'phone': user.phone,
                    'delivery_address_line_1': profile.address_line_1,
                    'delivery_parish': profile.parish,
                    'delivery_postcode': profile.postcode,
                })
        
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart
        context['cart_items'] = self.cart.items.select_related('event')
        return context
    
    def form_valid(self, form):
        """Process valid checkout form."""
        with transaction.atomic():
            # Handle guest account creation
            if not self.request.user.is_authenticated and form.cleaned_data.get('create_account'):
                user = self.create_guest_account(form.cleaned_data)
                if user:
                    # Log in the new user
                    login(self.request, user)
                    messages.success(
                        self.request,
                        f"Welcome to Jersey Events! Your account has been created and you're now logged in."
                    )

            # Create order
            order = self.create_order(form.cleaned_data)

            # Store order ID in session for payment
            self.request.session['pending_order_id'] = order.id

            # Redirect to payment method selection
            return redirect('payments:select_method')

    def create_guest_account(self, data):
        """Create account for guest user during checkout."""
        try:
            # Check if user already exists
            if User.objects.filter(email=data['email']).exists():
                messages.warning(
                    self.request,
                    "An account with this email already exists. Please log in."
                )
                return None

            # Create new user
            user = User.objects.create_user(
                email=data['email'],
                username=data['email'],  # Use email as username
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password1'],
                user_type='customer',
                phone=data.get('phone', ''),
                is_active=True
            )

            # Merge session cart with user cart if needed
            if self.cart and not self.cart.user:
                self.cart.user = user
                self.cart.session_key = None
                self.cart.save()

            return user

        except Exception as e:
            messages.error(
                self.request,
                f"There was an error creating your account: {str(e)}"
            )
            return None

    def create_order(self, data):
        """Create order from checkout data."""
        # Calculate totals
        shipping_cost = self.calculate_shipping(data['delivery_method'])
        
        order = Order.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            
            # Contact information
            email=data['email'],
            phone=data['phone'],
            
            # Delivery information - REQUIRED FIELDS
            delivery_first_name=data['first_name'],
            delivery_last_name=data['last_name'],
            delivery_address_line_1=data['delivery_address_line_1'],
            delivery_address_line_2=data.get('delivery_address_line_2', ''),
            delivery_parish=data['delivery_parish'],
            delivery_postcode=data['delivery_postcode'],
            delivery_method=data['delivery_method'],
            
            # Billing information
            billing_same_as_delivery=data['billing_same_as_delivery'],
            billing_first_name=data.get('billing_first_name', data['first_name']),
            billing_last_name=data.get('billing_last_name', data['last_name']),
            billing_address_line_1=data.get('billing_address_line_1', ''),
            billing_address_line_2=data.get('billing_address_line_2', ''),
            billing_parish=data.get('billing_parish', ''),
            billing_postcode=data.get('billing_postcode', ''),
            
            # Order details
            subtotal=self.cart.subtotal,
            shipping_cost=shipping_cost,
            total=self.cart.subtotal + shipping_cost,
            # Note: Check if Order model has 'customer_note' field
            # If not, remove this line
            
            status='pending'
        )
    
        # If customer_note exists in the model, set it separately
        if hasattr(order, 'customer_note') and data.get('customer_note'):
            order.customer_note = data['customer_note']
            order.save()
        
        # Create order items
        for cart_item in self.cart.items.all():
            OrderItem.objects.create(
                order=order,
                event=cart_item.event,
                quantity=cart_item.quantity,
                price=cart_item.price_at_time,
                total=cart_item.total_price
            )
        
        return order
            
            
        
    def calculate_shipping(self, method):
        """Calculate shipping cost based on method and cart total."""
        if method == 'collection':
            return Decimal('0.00')
        elif method == 'express':
            return Decimal('15.00')
        else:  # standard
            # Free shipping over £100
            if self.cart.subtotal >= Decimal('100.00'):
                return Decimal('0.00')
            return Decimal('5.00')


class SelectPaymentMethodView(FormView):
    """Select payment method before processing."""
    template_name = 'payments/select_method.html'
    form_class = PaymentMethodForm

    def dispatch(self, request, *args, **kwargs):
        # Check for pending order
        order_id = request.session.get('pending_order_id')
        if not order_id:
            messages.error(request, "No pending order found.")
            return redirect('cart:view')

        self.order = get_object_or_404(Order, id=order_id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        return context
    
    def form_valid(self, form):
        """Process payment method selection."""
        payment_method = form.cleaned_data['payment_method']

        if payment_method == 'sumup':
            return redirect('payments:sumup_checkout', order_id=self.order.id)
        else:
            messages.error(self.request, "Invalid payment method.")
            return redirect('payments:select_method')


class SumUpCheckoutView(View):
    """Process SumUp checkout."""

    def get(self, request, order_id):
        """Initiate SumUp checkout."""
        order = get_object_or_404(Order, id=order_id)

        # Verify order is pending
        if order.status != 'pending':
            messages.error(request, "This order has already been processed.")
            return redirect('orders:detail', pk=order.id)

        try:
            # Create SumUp checkout
            checkout = self.create_sumup_checkout(order, request)

            # Redirect to SumUp payment page
            return redirect(checkout.sumup_response['checkout_url'])

        except Exception as e:
            logger.error(f"SumUp checkout creation failed: {e}")
            messages.error(request, "Payment processing failed. Please try again.")
            return redirect('payments:select_method')

    def create_sumup_checkout(self, order, request):
        """Create SumUp checkout session."""
        # Build return URL for callbacks
        return_url = request.build_absolute_uri(
            reverse('payments:sumup_callback')
        )

        # Build redirect URL for after payment
        redirect_url = request.build_absolute_uri(
            reverse('payments:sumup_success')
        )

        # Get event description
        event_items = []
        for item in order.items.all():
            event_items.append(f"{item.quantity}x {item.event.title}")
        description = f"Jersey Events: {', '.join(event_items[:3])}"
        if len(event_items) > 3:
            description += f" and {len(event_items) - 3} more"

        # Create checkout record
        checkout = SumUpCheckout.objects.create(
            order=order,
            customer=order.user,
            amount=order.total,
            currency='GBP',
            description=description[:255],
            merchant_code=settings.SUMUP_MERCHANT_CODE,
            return_url=return_url,
            redirect_url=redirect_url
        )

        try:
            # Call SumUp API
            response = sumup_api.create_checkout_simple(
                amount=float(order.total),
                currency='GBP',
                reference=checkout.checkout_reference,
                description=description[:255],
                return_url=return_url,
                redirect_url=redirect_url
            )

            # Update checkout with SumUp response
            checkout.sumup_checkout_id = response.get('id', '')
            checkout.sumup_response = response
            checkout.valid_until = timezone.now() + timezone.timedelta(minutes=30)
            checkout.status = 'pending'
            checkout.save()

            return checkout

        except Exception as e:
            checkout.status = 'failed'
            checkout.save()
            raise


class SumUpCallbackView(View):
    """Handle SumUp payment callbacks."""

    def get(self, request):
        """Handle SumUp return URL callback."""
        checkout_id = request.GET.get('id')
        status = request.GET.get('status')

        if not checkout_id:
            messages.error(request, "Invalid payment callback.")
            return redirect('events:home')

        try:
            # Get checkout record
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

            # Update status from SumUp
            sumup_status = sumup_api.get_checkout_status(checkout_id)
            checkout.sumup_response = sumup_status
            checkout.status = self.map_sumup_status(sumup_status['status'])
            checkout.save()

            if checkout.status == 'paid':
                # Process successful payment
                self.process_successful_payment(checkout)
                messages.success(request, "Payment successful! Your tickets have been confirmed.")
                return redirect('orders:confirmation', pk=checkout.order.id)
            else:
                messages.error(request, "Payment was not completed.")
                return redirect('payments:select_method')

        except SumUpCheckout.DoesNotExist:
            messages.error(request, "Payment session not found.")
            return redirect('events:home')
        except Exception as e:
            logger.error(f"Payment callback error: {e}")
            messages.error(request, "Payment verification failed.")
            return redirect('payments:select_method')

    def map_sumup_status(self, sumup_status):
        """Map SumUp status to our status."""
        status_map = {
            'PENDING': 'pending',
            'SUCCESSFUL': 'paid',
            'PAID': 'paid',
            'FAILED': 'failed',
            'EXPIRED': 'expired'
        }
        return status_map.get(sumup_status, 'pending')

    def process_successful_payment(self, checkout):
        """Process successful payment."""
        order = checkout.order

        with transaction.atomic():
            # Update order status
            order.status = 'confirmed'
            order.payment_date = timezone.now()
            order.save()

            # Create transaction record
            if 'transaction_id' in checkout.sumup_response:
                SumUpTransaction.objects.create(
                    checkout=checkout,
                    sumup_transaction_id=checkout.sumup_response['transaction_id'],
                    transaction_code=checkout.sumup_response.get('transaction_code', ''),
                    amount=checkout.amount,
                    currency=checkout.currency,
                    status='successful',
                    timestamp=timezone.now(),
                    sumup_response=checkout.sumup_response
                )

            # Generate tickets for each order item
            for item in order.items.all():
                for _ in range(item.quantity):
                    ticket = Ticket.objects.create(
                        event=item.event,
                        customer=order.user if order.user else None,
                        customer_email=order.email,
                        customer_name=f"{order.delivery_first_name} {order.delivery_last_name}",
                        order=order,
                        price=item.price,
                        status='confirmed'
                    )
                    # Generate QR code
                    ticket.generate_qr_code()

                # Update event tickets sold
                item.event.tickets_sold += item.quantity
                item.event.save()

            # Clear the cart
            if checkout.customer:
                Cart.objects.filter(user=checkout.customer, is_active=True).delete()

            # Remove order from session
            if 'pending_order_id' in self.request.session:
                del self.request.session['pending_order_id']


class SumUpSuccessView(TemplateView):
    """Display success page after payment."""
    template_name = 'payments/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the most recent order for the user
        if self.request.user.is_authenticated:
            order = Order.objects.filter(
                user=self.request.user,
                status='confirmed'
            ).order_by('-created_at').first()
            context['order'] = order
        return context


@method_decorator(csrf_exempt, name='dispatch')
class SumUpWebhookView(View):
    """Handle SumUp webhook notifications."""

    def post(self, request):
        """Process webhook notification."""
        try:
            # Parse webhook data
            payload = json.loads(request.body)
            event_type = payload.get('event_type')
            event_data = payload.get('payload', {})

            logger.info(f"SumUp webhook received: {event_type}")

            # Handle different event types
            if event_type == 'checkout.completed':
                self.handle_checkout_completed(event_data)
            elif event_type == 'checkout.failed':
                self.handle_checkout_failed(event_data)
            elif event_type == 'payment.successful':
                self.handle_payment_successful(event_data)
            elif event_type == 'refund.successful':
                self.handle_refund_successful(event_data)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")

            return JsonResponse({'status': 'success'})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return JsonResponse({'error': 'Invalid payload'}, status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return JsonResponse({'error': 'Processing failed'}, status=500)

    def handle_checkout_completed(self, data):
        """Handle successful checkout completion."""
        checkout_id = data.get('id')
        status = data.get('status')

        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)

            if checkout.status != 'paid':
                checkout.status = 'paid'
                checkout.paid_at = timezone.now()
                checkout.sumup_response = data
                checkout.save()

                # Process the payment
                callback_view = SumUpCallbackView()
                callback_view.process_successful_payment(checkout)

                logger.info(f"Checkout {checkout_id} marked as paid via webhook")

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Checkout {checkout_id} not found for webhook")

    def handle_checkout_failed(self, data):
        """Handle failed checkout."""
        checkout_id = data.get('id')

        try:
            checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
            checkout.status = 'failed'
            checkout.sumup_response = data
            checkout.save()

            # Update order status
            checkout.order.status = 'failed'
            checkout.order.save()

            logger.info(f"Checkout {checkout_id} marked as failed via webhook")

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Checkout {checkout_id} not found for webhook")

    def handle_payment_successful(self, data):
        """Handle successful payment notification."""
        transaction_id = data.get('id')
        checkout_reference = data.get('checkout_reference')

        try:
            # Find checkout by reference
            checkout = SumUpCheckout.objects.get(checkout_reference=checkout_reference)

            # Create or update transaction
            SumUpTransaction.objects.update_or_create(
                sumup_transaction_id=transaction_id,
                defaults={
                    'checkout': checkout,
                    'transaction_code': data.get('transaction_code', ''),
                    'amount': Decimal(str(data.get('amount', 0))),
                    'currency': data.get('currency', 'GBP'),
                    'status': 'successful',
                    'card_last_four': data.get('card', {}).get('last_4_digits', ''),
                    'card_type': data.get('card', {}).get('type', ''),
                    'timestamp': timezone.now(),
                    'sumup_response': data
                }
            )

            logger.info(f"Transaction {transaction_id} processed via webhook")

        except SumUpCheckout.DoesNotExist:
            logger.error(f"Checkout not found for reference {checkout_reference}")

    def handle_refund_successful(self, data):
        """Handle successful refund notification."""
        refund_id = data.get('id')
        transaction_id = data.get('transaction_id')

        try:
            # Find the transaction
            transaction = SumUpTransaction.objects.get(sumup_transaction_id=transaction_id)

            # Update refund record
            from payments.models import SumUpRefund
            refund = SumUpRefund.objects.filter(
                transaction=transaction,
                sumup_refund_id=refund_id
            ).first()

            if refund:
                refund.status = 'successful'
                refund.processed_at = timezone.now()
                refund.sumup_response = data
                refund.save()

                # Update order status
                transaction.checkout.order.status = 'refunded'
                transaction.checkout.order.save()

                logger.info(f"Refund {refund_id} marked as successful via webhook")

        except SumUpTransaction.DoesNotExist:
            logger.error(f"Transaction {transaction_id} not found for refund webhook")


class ProcessSumUpPaymentView(View):
    """Create SumUp checkout and redirect to payment."""
    
    def get(self, request):
        # Get pending order
        order_id = request.session.get('pending_order_id')
        if not order_id:
            messages.error(request, "No pending order found.")
            return redirect('cart:view')
        
        order = get_object_or_404(Order, id=order_id)
        
        # Create SumUp checkout
        checkout = self.create_sumup_checkout(order)
        
        if checkout:
            # Redirect to SumUp payment page
            return redirect(self.get_sumup_payment_url(checkout))
        else:
            messages.error(request, "Payment initialization failed. Please try again.")
            return redirect('payments:select_method')
    
    def create_sumup_checkout(self, order):
        """Create a test checkout for development."""
        # Create local checkout record only (no API call yet)
        checkout = SumUpCheckout.objects.create(
            order=order,
            customer=order.user,
            amount=order.total,
            currency='GBP',
            description=f"Order {order.order_number}",
            merchant_code='TEST_MERCHANT',  # Use test value for now
            return_url=self.request.build_absolute_uri(
                reverse('payments:success')
            ),
            redirect_url=self.request.build_absolute_uri(
                reverse('payments:success')
            ),
            status='pending'
        )
        
        # For testing, generate a fake checkout ID
        checkout.sumup_checkout_id = f"test_{checkout.checkout_reference}"
        checkout.save()
        
        return checkout

    def get_sumup_payment_url(self, checkout):
        """For testing, show the checkout widget template."""
        # This will show your checkout_widget.html template
        return reverse('payments:success') + f"?test_checkout={checkout.checkout_reference}"


@method_decorator(csrf_exempt, name='dispatch')
class SumUpCallbackView(View):
    """Handle SumUp payment callbacks/webhooks."""
    
    def post(self, request):
        """Process SumUp webhook notification."""
        try:
            data = json.loads(request.body)
            
            # Get checkout by reference
            checkout_ref = data.get('checkout_reference')
            if not checkout_ref:
                return HttpResponseBadRequest("Missing checkout reference")
            
            checkout = get_object_or_404(
                SumUpCheckout,
                checkout_reference=checkout_ref
            )
            
            # Update checkout status
            status = data.get('status')
            if status == 'PAID':
                self.handle_successful_payment(checkout, data)
            elif status == 'FAILED':
                self.handle_failed_payment(checkout, data)
            
            return JsonResponse({'status': 'ok'})
            
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        except Exception as e:
            print(f"Callback error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def handle_successful_payment(self, checkout, data):
        """Process successful payment."""
        with transaction.atomic():
            # Update checkout
            checkout.status = 'paid'
            checkout.paid_at = timezone.now()
            checkout.sumup_response = data
            checkout.save()
            
            # Create transaction record
            transaction_data = data.get('transactions', [{}])[0]
            SumUpTransaction.objects.create(
                checkout=checkout,
                sumup_transaction_id=transaction_data.get('id'),
                transaction_code=transaction_data.get('transaction_code'),
                amount=Decimal(str(transaction_data.get('amount', 0))),
                currency=transaction_data.get('currency', 'GBP'),
                status='successful',
                payment_type='ecom',
                timestamp=transaction_data.get('timestamp', timezone.now()),
                sumup_response=transaction_data
            )
            
            # Update order
            order = checkout.order
            order.status = 'processing'
            order.is_paid = True
            order.paid_at = timezone.now()
            order.transaction_id = transaction_data.get('transaction_code')
            order.save()
            
            # Update event ticket availability
            for item in order.items.all():
                # Update tickets sold count
                item.event.tickets_sold += item.quantity
                if item.event.tickets_sold >= item.event.capacity:
                    item.event.status = 'sold_out'
                item.event.save()
            
            # Clear cart
            if order.user:
                Cart.objects.filter(user=order.user, is_active=True).delete()
    
    def handle_failed_payment(self, checkout, data):
        """Process failed payment."""
        checkout.status = 'failed'
        checkout.sumup_response = data
        checkout.save()
        
        # Update order status
        checkout.order.status = 'cancelled'
        checkout.order.save()


class PaymentSuccessView(TemplateView):
    """Display payment success page."""
    template_name = 'payments/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get order from session
        order_id = self.request.session.get('pending_order_id')
        if order_id:
            context['order'] = get_object_or_404(Order, id=order_id)
            # Clear session
            del self.request.session['pending_order_id']
        
        return context


class PaymentFailedView(TemplateView):
    """Display payment failure page."""
    template_name = 'payments/failed.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get order from session
        order_id = self.request.session.get('pending_order_id')
        if order_id:
            context['order'] = get_object_or_404(Order, id=order_id)
        
        return context


# --- SumUp OAuth ---

def sumup_connect_start(request, artist_id):
    artist = get_object_or_404(Artist, pk=artist_id, is_active=True)
    state = f"{artist.id}:{uuid.uuid4()}"
    request.session["sumup_oauth_state"] = state
    return redirect(sumup_api.oauth_authorize_url(state))

def sumup_connect_callback(request):
    state_sent = request.session.get("sumup_oauth_state")
    state_recv = request.GET.get("state")
    code = request.GET.get("code")
    if not code or state_sent != state_recv:
        return HttpResponseBadRequest("Bad OAuth state or missing code")

    artist_id = int(state_recv.split(":")[0])
    artist = get_object_or_404(Artist, pk=artist_id)

    tokens = sumup_api.exchange_code_for_tokens(code)
    ArtistSumUpAuth.objects.update_or_create(
        artist=artist,
        defaults={
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_at": tokens["expires_at"],
            "scope": tokens["scope"],
        },
    )
    return HttpResponse("SumUp connected. You can close this window.")

# --- Create checkout for an artist's order ---

def start_checkout(request, artist_id):
    # Use User model instead of Artist
    from accounts.models import User
    from orders.models import Order as UserOrder  # Use the actual Order model
    
    artist = get_object_or_404(User, pk=artist_id, user_type='artist')
    
    # Create a simple test order
    order = UserOrder.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=request.user.email if request.user.is_authenticated else 'test@example.com',
        phone='01534123456',
        delivery_first_name='Test',
        delivery_last_name='User',
        delivery_address_line_1='123 Test St',
        delivery_parish='st_helier',
        delivery_postcode='JE2 3AB',
        subtotal=Decimal('100.00'),
        shipping_cost=Decimal('0.00'),
        total=Decimal('100.00'),
        status='pending'
    )
    
    # Create SumUp checkout
    checkout = SumUpCheckout.objects.create(
        order=order,
        artist=artist,
        customer=request.user if request.user.is_authenticated else None,
        amount=order.total,
        currency='GBP',
        description=f'Order {order.order_number}',
        merchant_code='TEST123',
        return_url=request.build_absolute_uri(reverse("payments:payment_success")),
        checkout_reference=str(uuid.uuid4()),
        sumup_checkout_id=f'test_{uuid.uuid4().hex[:8]}',
        status='pending'
    )
    
    # For testing, just redirect to success
    return redirect('payments:payment_success')

def payment_success(request):
    ref = request.GET.get("ref")
    if not ref:
        return HttpResponse("Thanks! If you paid, your order will appear shortly.")

    order = get_object_or_404(Order, reference=ref)
    checkout = sumup_api.get_checkout(order.artist.sumup, order.payment.checkout_id)
    status = checkout.get("status", "PENDING")

    if status == "SUCCESSFUL":
        order.status = "PAID"
        order.save()
        order.payment.status = "SUCCESSFUL"
        order.payment.raw = checkout
        order.payment.save()
        # TODO: send confirmation email/QR, update stock/capacity
    elif status == "FAILED":
        order.status = "FAILED"
        order.save()
        order.payment.status = "FAILED"
        order.payment.raw = checkout
        order.payment.save()

    return render(request, "payments/summary.html", {"order": order, "checkout": checkout})

def payment_fail(request):
    return HttpResponse("Payment failed or cancelled. Try again when ready.")

# --- SumUp webhook: source of truth for paid/failed ---

@csrf_exempt
def sumup_webhook(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Handle test checkout IDs
    checkout_id = data.get("id") or data.get("checkout_id")
    status = data.get("status")
    
    if not checkout_id:
        return HttpResponse("ok")
    
    # Try to find SumUpCheckout
    try:
        checkout = SumUpCheckout.objects.get(sumup_checkout_id=checkout_id)
    except SumUpCheckout.DoesNotExist:
        # Try the Payment model as fallback for legacy code
        try:
            p = Payment.objects.get(checkout_id=checkout_id)
            if status == "SUCCESSFUL" or status == "PAID":
                p.status = "SUCCESSFUL"
                p.raw = data
                p.save()
                p.order.status = "PAID"
                p.order.save()
            return HttpResponse("ok")
        except Payment.DoesNotExist:
            return HttpResponse("ok")
    
    # Handle SumUpCheckout
    if status == "PAID" or status == "SUCCESSFUL":
        checkout.status = 'paid'
        checkout.paid_at = timezone.now()
        checkout.sumup_response = data
        checkout.save()
        
        # Update order
        order = checkout.order
        order.is_paid = True
        order.status = 'confirmed'
        order.paid_at = timezone.now()
        order.save()
        
    elif status == "FAILED":
        checkout.status = 'failed'
        checkout.sumup_response = data
        checkout.save()
        
        order = checkout.order
        order.status = 'cancelled'
        order.save()
    
    return HttpResponse("ok")

# --- Monthly subscription billing (CityPay or SumUp token) ---

def run_monthly_billing(request):
    """You can wire this behind admin auth or as a cron/Celery task trigger."""
    results = []
    today = timezone.now().date()
    subs = Subscription.objects.select_related("artist").filter(is_active=True, next_charge_date__lte=today)
    for s in subs:
        ref = f"sub-{s.artist_id}-{uuid.uuid4().hex[:8]}"
        try:
            if s.citypay_token:
                resp = citypay_api.charge_citypay_token(s.citypay_token, float(s.amount_gbp), ref)
                # decide success by resp fields; update next date
            elif s.sumup_token:
                # TODO: call SumUp "charge token" endpoint if you keep it all in SumUp
                resp = {"status": "NOT_IMPLEMENTED"}
                raise RuntimeError("SumUp token charging not implemented in this snippet.")
            else:
                raise RuntimeError("No stored token for subscription.")

            # If charge OK:
            s.next_charge_date = today + datetime.timedelta(days=30)
            s.save()
            results.append({"artist": s.artist_id, "ok": True})
        except Exception as e:
            # Dunning: email the artist; maybe pause listings after N failures
            results.append({"artist": s.artist_id, "ok": False, "error": str(e)})
    return JsonResponse({"ran": len(results), "results": results})

class CheckoutWidgetView(TemplateView):
    template_name = 'payments/checkout_widget.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['checkout_id'] = self.kwargs['checkout_id']
        return context
    
@login_required
def process_subscription(request, subscription_payment_id):
    """Process a subscription payment."""
    from subscriptions.models import SubscriptionPayment
    
    payment = get_object_or_404(SubscriptionPayment, id=subscription_payment_id)
    
    # For testing, just mark as completed
    payment.status = 'completed'
    payment.paid_at = timezone.now()
    payment.save()
    
    messages.success(request, "Subscription payment processed successfully.")
    return redirect('payments:subscription_history')

@login_required
def subscription_history(request):
    """View subscription payment history."""
    from subscriptions.models import SubscriptionPayment
    
    # Get payments for the current user's subscription
    payments = SubscriptionPayment.objects.filter(
        subscription__user=request.user
    ).order_by('-created_at')
    
    context = {
        'payments': payments
    }
    return render(request, 'payments/subscription_history.html', context)
