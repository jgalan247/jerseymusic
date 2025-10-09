# Complete imports for the top of orders/views.py
# Replace ALL imports at the top of your orders/views.py with these:

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View  # Add this for basic View
from django.views.generic import ListView, DetailView, TemplateView, FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from decimal import Decimal
import json
from datetime import datetime, timedelta
from django.template.loader import render_to_string 
# Import your models
from .models import Order, OrderItem, OrderStatusHistory, RefundRequest
from .forms import CheckoutForm, PaymentMethodForm, OrderStatusForm, RefundRequestForm
from cart.models import Cart
from accounts.models import User
from events.models import Event, Ticket
from payments.models import SumUpCheckout
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import csv
# Any other app imports you might need
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.http import HttpResponse
# # from weasyprint import HTML, CSS  # Removed - using xhtml2pdf  # Optional for PDF
# from weasyprint.text.fonts import FontConfiguration
import tempfile
import os

class OrderConfirmationView(DetailView):
    """Display order confirmation after successful payment."""
    model = Order
    template_name = 'orders/confirmation.html'
    context_object_name = 'order'

    def get_object(self):
        return get_object_or_404(Order, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get tickets for this order
        context['tickets'] = Ticket.objects.filter(order=self.object)

        # Get order items with event details
        context['order_items'] = self.object.items.select_related('event')

        # Send confirmation email if not already sent
        if self.object.status == 'confirmed' and not hasattr(self, 'email_sent'):
            self.send_confirmation_email()
            self.email_sent = True

        return context

    def send_confirmation_email(self):
        """Send order confirmation email with tickets."""
        order = self.object
        tickets = Ticket.objects.filter(order=order)

        # Prepare email context
        context = {
            'order': order,
            'tickets': tickets,
            'order_items': order.items.select_related('event'),
            'site_url': self.request.build_absolute_uri('/')[:-1]
        }

        # Render email templates
        subject = f'Order Confirmation - Jersey Events #{order.order_number}'
        html_content = render_to_string('orders/emails/confirmation.html', context)
        text_content = render_to_string('orders/emails/confirmation.txt', context)

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email]
        )
        email.attach_alternative(html_content, "text/html")

        # Attach ticket PDFs if available
        for ticket in tickets:
            if ticket.qr_code:
                # Attach QR code image
                email.attach(
                    f'ticket_{ticket.ticket_number}.png',
                    ticket.qr_code.read(),
                    'image/png'
                )

        # Send email
        try:
            email.send(fail_silently=False)
            messages.success(self.request, "Confirmation email sent successfully!")
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
            messages.warning(self.request, "Confirmation email could not be sent. Please save your ticket information.")


@login_required
def my_orders(request):
    # You can add logic here to get the user's orders
    # orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/my_orders.html')

@login_required
def artist_orders(request):
    """Display orders containing the artist's artwork"""
    if request.user.user_type != 'artist':
        return HttpResponseForbidden("Artists only")
    
    # Get orders containing this artist's artwork
    orders = Order.objects.filter(
        items__artwork__artist=request.user
    ).distinct().order_by('-created_at')
    
    context = {
        'orders': orders
    }
    return render(request, 'orders/artist_orders.html', context)

class CustomerOrderListView(LoginRequiredMixin, ListView):
    """View for customers to see their orders."""
    model = Order
    template_name = 'orders/my_orders.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Order.objects.filter(
            user=self.request.user
        ).exclude(
            status='pending'
        ).order_by('-created_at')
        
        # Apply filters
        form = OrderStatusForm(self.request.GET)
        if form.is_valid():
            # Status filter
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])
            
            # Period filter
            if form.cleaned_data['period']:
                period = form.cleaned_data['period']
                today = timezone.now().date()
                
                if period == 'today':
                    queryset = queryset.filter(created_at__date=today)
                elif period == 'week':
                    start_date = today - timedelta(days=7)
                    queryset = queryset.filter(created_at__date__gte=start_date)
                elif period == 'month':
                    start_date = today - timedelta(days=30)
                    queryset = queryset.filter(created_at__date__gte=start_date)
                elif period == '3months':
                    start_date = today - timedelta(days=90)
                    queryset = queryset.filter(created_at__date__gte=start_date)
                elif period == '6months':
                    start_date = today - timedelta(days=180)
                    queryset = queryset.filter(created_at__date__gte=start_date)
                elif period == 'year':
                    queryset = queryset.filter(created_at__year=today.year)
            
            # Search filter
            if form.cleaned_data['search']:
                search_term = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(order_number__icontains=search_term) |
                    Q(email__icontains=search_term)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = OrderStatusForm(self.request.GET)
        
        # Calculate order statistics
        user_orders = Order.objects.filter(user=self.request.user)
        context['total_orders'] = user_orders.count()
        context['total_spent'] = user_orders.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a specific order."""
    model = Order
    template_name = 'orders/detail.html'
    context_object_name = 'order'
    
    def get_object(self):
        return get_object_or_404(
            Order,
            order_number=self.kwargs['order_number'],
            user=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get order items with artwork details
        context['order_items'] = self.object.items.select_related(
            'artwork',
            'artwork__artist'
        )
        
        # Get status history
        context['status_history'] = self.object.status_history.order_by('-created_at')
        
        # Check if refund exists
        context['refund'] = self.object.refunds.first()
        context['can_request_refund'] = (
            self.object.status in ['delivered', 'processing', 'confirmed', 'shipped'] and
            not context['refund'] and
            self.object.is_paid
        )
        
        return context


class GuestOrderTrackingView(View):
    """Allow guests to track orders with order number and email."""
    template_name = 'orders/guest_tracking.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        order_number = request.POST.get('order_number')
        email = request.POST.get('email')
        
        try:
            order = Order.objects.get(
                order_number=order_number,
                email=email
            )
            
            # Render order details
            context = {
                'order': order,
                'order_items': order.items.select_related('artwork'),
                'status_history': order.status_history.order_by('-created_at')
            }
            return render(request, 'orders/guest_tracking_result.html', context)
            
        except Order.DoesNotExist:
            messages.error(request, "Order not found. Please check your details.")
            return render(request, self.template_name)


class ArtistOrderListView(LoginRequiredMixin, ListView):
    """View for artists to see orders containing their artworks."""
    model = Order
    template_name = 'orders/artist_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.user_type != 'artist':
            return HttpResponseForbidden("Artists only")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # Get orders that contain this artist's artworks
        return Order.objects.filter(
            items__artwork__artist=self.request.user,
            is_paid=True
        ).distinct().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate artist statistics
        artist_items = OrderItem.objects.filter(
            artwork__artist=self.request.user,
            order__is_paid=True
        )
        
        context['total_sales'] = artist_items.count()
        context['total_revenue'] = artist_items.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        # Calculate commission (assuming 10% platform fee)
        context['total_earnings'] = context['total_revenue'] * Decimal('0.9')
        
        # Get top selling artworks
        context['top_artworks'] = artist_items.values(
            'artwork__title',
            'artwork__id'
        ).annotate(
            sold_count=Count('id'),
            revenue=Sum('total')
        ).order_by('-sold_count')[:5]
        
        return context


class RequestRefundView(LoginRequiredMixin, FormView):
    """Allow customers to request refunds."""
    template_name = 'orders/request_refund.html'
    form_class = RefundRequestForm
    
    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(
            Order,
            order_number=kwargs['order_number'],
            user=request.user
        )
        
        # Check if refund can be requested
        if not self.order.can_cancel:
            messages.error(request, "This order cannot be refunded.")
            return redirect('orders:detail', order_number=self.order.order_number)
        
        # Check if refund already exists
        if self.order.refunds.exists():
            messages.info(request, "A refund request already exists for this order.")
            return redirect('orders:detail', order_number=self.order.order_number)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['order'] = self.order
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        return context
    
    def form_valid(self, form):
        refund = form.save()
        
        # Create status history entry
        OrderStatusHistory.objects.create(
            order=self.order,
            status='refund_requested',
            note=f"Refund requested: {refund.reason}"
        )
        
        messages.success(
            self.request,
            "Your refund request has been submitted. We'll review it within 2-3 business days."
        )
        
        # TODO: Send email notification to admin and customer
        
        return redirect('orders:detail', order_number=self.order.order_number)


class DownloadInvoiceView(LoginRequiredMixin, View):
    """Generate and download invoice PDF."""
    
    def get(self, request, order_number):
        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user
        )
        
        # Prepare context for template
        context = {
            'order': order,
            'order_items': order.items.select_related('artwork'),
            'company_name': 'Jersey Artwork',
            'company_address': 'St. Helier, Jersey',
            'company_email': 'info@jerseyartwork.je',
            'company_phone': '+44 1534 123456'
        }
        
        # Render HTML template
        html_string = render_to_string('orders/invoice_pdf.html', context)
        
        # Create PDF
        try:
            # Configure font handling
            font_config = FontConfiguration()
            
            # Generate PDF from HTML
            html = HTML(string=html_string)
            pdf = html.write_pdf(font_config=font_config)
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order_number}.pdf"'
            
            return response
            
        except Exception as e:
            # Fallback to HTML if PDF generation fails
            messages.error(
                request, 
                f"PDF generation failed: {str(e)}. Showing HTML version instead."
            )
            
            # Return HTML version as fallback
            response = HttpResponse(html_string, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order_number}.html"'
            return response


class OrderStatisticsView(LoginRequiredMixin, View):
    """API endpoint for order statistics (for charts)."""
    
    def get(self, request):
        user = request.user
        period = request.GET.get('period', '30')  # Days
        
        if user.user_type == 'artist':
            # Get artist statistics
            end_date = timezone.now()
            start_date = end_date - timedelta(days=int(period))
            
            orders = Order.objects.filter(
                items__artwork__artist=user,
                is_paid=True,
                created_at__range=[start_date, end_date]
            ).distinct()
            
            # Group by date
            daily_sales = {}
            for order in orders:
                date_key = order.created_at.date().isoformat()
                if date_key not in daily_sales:
                    daily_sales[date_key] = {
                        'count': 0,
                        'revenue': 0
                    }
                
                # Calculate revenue for this artist
                artist_items = order.items.filter(artwork__artist=user)
                revenue = sum(item.total for item in artist_items)
                
                daily_sales[date_key]['count'] += 1
                daily_sales[date_key]['revenue'] += float(revenue)
            
            return JsonResponse({
                'daily_sales': daily_sales,
                'total_orders': orders.count(),
                'total_revenue': sum(d['revenue'] for d in daily_sales.values())
            })
        
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
# Add these views to your existing orders/views.py




class ArtistDashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard for artists showing sales overview."""
    template_name = 'orders/artist_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.user_type == 'artist':
            messages.error(request, "This page is only for artists.")
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        artist = self.request.user
        
        # Get all orders containing artist's artworks
        artist_orders = Order.objects.filter(
            items__artwork__artist=artist,
            is_paid=True
        ).distinct()
        
        # Calculate time periods
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # This month's sales
        this_month_orders = artist_orders.filter(
            created_at__date__gte=this_month_start
        )
        
        # Last month's sales
        last_month_orders = artist_orders.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lt=this_month_start
        )
        
        # Calculate revenues
        def calculate_revenue(orders, artist_user):
            total = 0
            for order in orders:
                items = order.items.filter(artwork__artist=artist_user)
                total += sum(item.total for item in items)
            return total
        
        context['this_month_revenue'] = calculate_revenue(this_month_orders, artist)
        context['last_month_revenue'] = calculate_revenue(last_month_orders, artist)
        context['total_revenue'] = calculate_revenue(artist_orders, artist)
        
        # Platform fees (10% commission)
        context['this_month_earnings'] = context['this_month_revenue'] * Decimal('0.9')
        context['platform_fees'] = context['this_month_revenue'] * Decimal('0.1')
        
        # Recent orders
        context['recent_orders'] = artist_orders.order_by('-created_at')[:10]
        
        # Pending refund requests
        context['pending_refunds'] = RefundRequest.objects.filter(
            artist=artist,
            status__in=['requested', 'artist_reviewing']
        ).count()
        
        # Best selling artworks
        context['best_sellers'] = OrderItem.objects.filter(
            artwork__artist=artist,
            order__is_paid=True
        ).values(
            'artwork__title',
            'artwork__id',
            'artwork__main_image'
        ).annotate(
            total_sold=Count('id'),
            revenue=Sum('total')
        ).order_by('-total_sold')[:5]
        
        # Sales by artwork type
        context['sales_by_type'] = OrderItem.objects.filter(
            artwork__artist=artist,
            order__is_paid=True
        ).values('artwork__artwork_type').annotate(
            count=Count('id'),
            revenue=Sum('total')
        )
        
        return context


class ArtistOrderDetailView(LoginRequiredMixin, DetailView):
    """Artist view of a specific order containing their artwork."""
    model = Order
    template_name = 'orders/artist_order_detail.html'
    context_object_name = 'order'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.user_type == 'artist':
            messages.error(request, "This page is only for artists.")
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        order = get_object_or_404(
            Order,
            order_number=self.kwargs['order_number']
        )
        
        # Check if order contains artist's artwork
        if not order.items.filter(artwork__artist=self.request.user).exists():
            raise Http404("Order not found")
        
        return order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get only this artist's items from the order
        context['artist_items'] = self.object.items.filter(
            artwork__artist=self.request.user
        ).select_related('artwork')
        
        # Calculate artist's revenue from this order
        context['artist_revenue'] = sum(
            item.total for item in context['artist_items']
        )
        
        # Platform fee (10%)
        context['platform_fee'] = context['artist_revenue'] * Decimal('0.1')
        context['artist_earnings'] = context['artist_revenue'] * Decimal('0.9')
        
        # Check for refund requests
        context['refund_request'] = RefundRequest.objects.filter(
            order=self.object,
            artist=self.request.user
        ).first()
        
        return context


class ArtistRefundListView(LoginRequiredMixin, ListView):
    """List of refund requests for artist."""
    model = RefundRequest
    template_name = 'orders/artist_refund_list.html'
    context_object_name = 'refund_requests'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.user_type == 'artist':
            messages.error(request, "This page is only for artists.")
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return RefundRequest.objects.filter(
            artist=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        all_requests = RefundRequest.objects.filter(artist=self.request.user)
        context['total_requests'] = all_requests.count()
        context['pending_requests'] = all_requests.filter(
            status__in=['requested', 'artist_reviewing']
        ).count()
        context['approved_requests'] = all_requests.filter(status='approved').count()
        
        return context


class ArtistHandleRefundView(LoginRequiredMixin, FormView):
    """Artist responds to refund request."""
    template_name = 'orders/artist_handle_refund.html'
    form_class = RefundRequestForm 
    def dispatch(self, request, *args, **kwargs):
        if not request.user.user_type == 'artist':
            messages.error(request, "This page is only for artists.")
            return redirect('events:home')
        
        self.refund_request = get_object_or_404(
            RefundRequest,
            id=kwargs['refund_id'],
            artist=request.user
        )
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['refund_request'] = self.refund_request
        context['order'] = self.refund_request.order
        
        # Get artist's items from this order
        context['artist_items'] = self.refund_request.order.items.filter(
            artwork__artist=self.request.user
        )
        
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        response_message = request.POST.get('response_message', '')
        
        if action == 'approve':
            self.refund_request.status = 'approved'
            self.refund_request.artist_approved = True
            self.refund_request.artist_response = response_message
            self.refund_request.artist_message = f"""
            Your refund has been approved. 
            Please allow 5-7 business days for the refund to be processed through SumUp.
            
            Artist's message: {response_message}
            """
            
            messages.success(request, "Refund approved. Customer will be notified.")
            
        elif action == 'reject':
            self.refund_request.status = 'rejected'
            self.refund_request.artist_approved = False
            self.refund_request.artist_response = response_message
            self.refund_request.artist_message = f"""
            After reviewing your request, we cannot approve the refund at this time.
            
            Reason: {response_message}
            """
            
            messages.info(request, "Refund rejected. Customer will be notified.")
        
        elif action == 'need_info':
            self.refund_request.status = 'artist_reviewing'
            self.refund_request.artist_message = response_message
            
            messages.info(request, "Message sent to customer.")
        
        self.refund_request.save()
        
        # TODO: Send email notification to customer
        
        return redirect('orders:artist_refund_list')


class ArtistSalesReportView(LoginRequiredMixin, View):
    """Generate sales report for artist."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.user_type == 'artist':
            messages.error(request, "This page is only for artists.")
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        # Get date range from query params
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        # Get sales data
        sales_data = OrderItem.objects.filter(
            artwork__artist=request.user,
            order__is_paid=True,
            order__created_at__date__range=[start_date, end_date]
        ).values(
            'order__order_number',
            'order__created_at',
            'artwork__title',
            'quantity',
            'price',
            'total'
        ).order_by('-order__created_at')
        
        # Calculate totals
        total_revenue = sales_data.aggregate(Sum('total'))['total__sum'] or 0
        platform_fees = total_revenue * Decimal('0.1')
        net_earnings = total_revenue * Decimal('0.9')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Sales Report', f'{start_date} to {end_date}'])
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow(['Total Revenue', f'£{total_revenue:.2f}'])
        writer.writerow(['Platform Fees (10%)', f'£{platform_fees:.2f}'])
        writer.writerow(['Net Earnings', f'£{net_earnings:.2f}'])
        writer.writerow([])
        writer.writerow(['Order Number', 'Date', 'Artwork', 'Quantity', 'Price', 'Total'])
        
        for sale in sales_data:
            writer.writerow([
                sale['order__order_number'],
                sale['order__created_at'].strftime('%Y-%m-%d %H:%M'),
                sale['artwork__title'],
                sale['quantity'],
                f"£{sale['price']:.2f}",
                f"£{sale['total']:.2f}"
            ])
        
        return response