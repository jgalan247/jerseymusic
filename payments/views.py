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
from artworks.models import Artwork
#from accounts.models import User
from .models import SumUpCheckout, SumUpTransaction
from .forms import CheckoutForm, PaymentMethodForm

from django.http import HttpResponse
import datetime

from .models import SumUpCheckout, SumUpTransaction, Artist, ArtistSumUpAuth, Payment, Subscription
from . import sumup as sumup_api
from . import citypay as citypay_api




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
        context['cart_items'] = self.cart.items.select_related('artwork')
        return context
    
    def form_valid(self, form):
        """Process valid checkout form."""
        with transaction.atomic():
            # Create order
            order = self.create_order(form.cleaned_data)
            
            # Store order ID in session for payment
            self.request.session['pending_order_id'] = order.id
            
            # Redirect to payment method selection
            return redirect('payments:select_method')
    
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
                artwork=cart_item.artwork,
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
        if form.cleaned_data['payment_method'] == 'sumup':
            return redirect('payments:process_sumup')
        
        # Add other payment methods here if needed
        return redirect('payments:process_sumup')


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
            
            # Update artwork availability
            for item in order.items.all():
                if item.artwork.artwork_type == 'original':
                    item.artwork.is_available = False
                    item.artwork.status = 'sold'
                    item.artwork.save()
                else:
                    # Update stock for prints
                    item.artwork.stock_quantity -= item.quantity
                    item.artwork.save()
            
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
