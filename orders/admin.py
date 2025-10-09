from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import Order, OrderItem, OrderStatusHistory, RefundRequest

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'customer_name',
        'email',
        'total',
        'status_display',
        'terms_acceptance_display',
        'payment_verification_status',
        'created_at'
    )
    list_filter = ('status', 'is_paid', 'terms_accepted', 'created_at', 'delivery_parish')
    search_fields = ('order_number', 'email', 'user__username', 'delivery_first_name', 'delivery_last_name')
    readonly_fields = (
        'order_number',
        'created_at',
        'updated_at',
        'payment_notes_display',
        'terms_acceptance_details_display'
    )
    ordering = ('-created_at',)
    actions = ['approve_payment_verification', 'reject_payment_verification']

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Customer Details', {
            'fields': ('email', 'phone', 'delivery_first_name', 'delivery_last_name')
        }),
        ('Payment Information', {
            'fields': ('total', 'is_paid', 'paid_at', 'payment_method', 'transaction_id')
        }),
        ('Terms & Conditions Acceptance', {
            'fields': ('terms_acceptance_details_display',),
            'description': 'Legal record of Terms & Conditions acceptance'
        }),
        ('Payment Verification', {
            'fields': ('payment_notes_display', 'admin_note'),
            'classes': ('collapse',)
        }),
        ('Delivery Information', {
            'fields': ('delivery_address_line_1', 'delivery_address_line_2', 'delivery_parish', 'delivery_postcode'),
            'classes': ('collapse',)
        }),
    )

    def customer_name(self, obj):
        return f"{obj.delivery_first_name} {obj.delivery_last_name}"
    customer_name.short_description = 'Customer'

    def terms_acceptance_display(self, obj):
        """Display T&C acceptance status in list view."""
        if obj.terms_accepted:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Accepted</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Not Accepted</span>'
        )
    terms_acceptance_display.short_description = 'T&C'

    def terms_acceptance_details_display(self, obj):
        """Display full T&C acceptance details."""
        if not obj.terms_accepted:
            return format_html(
                '<div style="background: #ffebee; padding: 15px; border-radius: 4px; border-left: 4px solid #f44336;">'
                '<strong>⚠️ Terms & Conditions Not Accepted</strong><br>'
                '<small>This order was created before T&C acceptance was implemented.</small>'
                '</div>'
            )

        html = f'''
        <div style="background: #e8f5e9; padding: 15px; border-radius: 4px; border-left: 4px solid #4caf50;">
            <strong>✅ Terms & Conditions Accepted</strong><br><br>

            <table style="width: 100%; font-family: monospace;">
                <tr>
                    <td style="padding: 4px; width: 180px;"><strong>Accepted:</strong></td>
                    <td style="padding: 4px;">{"Yes" if obj.terms_accepted else "No"}</td>
                </tr>
                <tr>
                    <td style="padding: 4px;"><strong>Acceptance Date/Time:</strong></td>
                    <td style="padding: 4px;">{obj.terms_accepted_at.strftime('%Y-%m-%d %H:%M:%S %Z') if obj.terms_accepted_at else 'Not recorded'}</td>
                </tr>
                <tr>
                    <td style="padding: 4px;"><strong>T&C Version:</strong></td>
                    <td style="padding: 4px;">{obj.terms_version or 'Not recorded'}</td>
                </tr>
                <tr>
                    <td style="padding: 4px;"><strong>IP Address:</strong></td>
                    <td style="padding: 4px;">{obj.acceptance_ip or 'Not recorded'}</td>
                </tr>
            </table>

            <div style="margin-top: 10px; padding: 10px; background: #fff; border-radius: 4px;">
                <small><strong>ℹ️ Legal Record:</strong> This information is legally binding proof of customer acceptance of the Terms & Conditions at the time of purchase.
                The IP address can be used for dispute resolution if needed.</small>
            </div>
        </div>
        '''

        return format_html(html)
    terms_acceptance_details_display.short_description = 'T&C Acceptance Details'

    def status_display(self, obj):
        if obj.status == 'pending_verification':
            return format_html(
                '<span style="color: orange; font-weight: bold;">🚨 NEEDS MANUAL VERIFICATION</span>'
            )
        elif obj.status == 'confirmed' and obj.is_paid:
            return format_html('<span style="color: green;">✅ Confirmed & Paid</span>')
        elif obj.status == 'pending':
            return format_html('<span style="color: blue;">⏳ Pending Payment</span>')
        return obj.get_status_display()
    status_display.short_description = 'Status'

    def payment_verification_status(self, obj):
        if obj.status == 'pending_verification':
            return format_html(
                '<a href="{}">🔍 Verify Payment</a>',
                reverse('admin:orders_order_verify_payment', args=[obj.pk])
            )
        elif obj.is_paid:
            return '✅ Verified'
        return '❌ Not Paid'
    payment_verification_status.short_description = 'Payment Status'

    def payment_notes_display(self, obj):
        if obj.payment_notes:
            return format_html('<div style="background: #fff3cd; padding: 10px; border-radius: 4px;">{}</div>', obj.payment_notes)
        return 'No payment notes'
    payment_notes_display.short_description = 'Payment Verification Notes'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:order_id>/verify-payment/',
                self.admin_site.admin_view(self.verify_payment_view),
                name='orders_order_verify_payment',
            ),
        ]
        return custom_urls + urls

    def verify_payment_view(self, request, order_id):
        from django.shortcuts import render, get_object_or_404
        from django.core.mail import send_mail
        from django.conf import settings

        order = get_object_or_404(Order, id=order_id)

        if request.method == 'POST':
            action = request.POST.get('action')
            admin_notes = request.POST.get('admin_notes', '')

            if action == 'approve':
                # Mark order as confirmed and paid
                order.status = 'confirmed'
                order.is_paid = True
                order.paid_at = timezone.now()
                order.admin_note = f"Payment manually verified by {request.user.username} at {timezone.now()}. Notes: {admin_notes}"
                order.payment_notes = f"MANUALLY VERIFIED: {admin_notes}"
                order.save()

                # Generate tickets
                try:
                    from payments.redirect_success_fixed import generate_tickets_for_order, send_confirmation_emails
                    tickets = generate_tickets_for_order(order)
                    send_confirmation_emails(order, tickets)

                    messages.success(request, f'Order {order.order_number} approved! Customer has been emailed.')
                except Exception as e:
                    messages.warning(request, f'Order approved but email failed: {e}')

            elif action == 'reject':
                # Mark order as cancelled
                order.status = 'cancelled'
                order.admin_note = f"Payment rejected by {request.user.username} at {timezone.now()}. Reason: {admin_notes}"
                order.payment_notes = f"PAYMENT REJECTED: {admin_notes}"
                order.save()

                # Send rejection email to customer
                try:
                    send_mail(
                        subject=f'Order {order.order_number} - Payment Issue',
                        message=f'''
Dear {order.delivery_first_name},

We were unable to verify your payment for order {order.order_number}.

Reason: {admin_notes}

Please contact us at support@jerseyevents.je if you believe this is an error.

Best regards,
Jersey Events Team
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[order.email],
                        fail_silently=False
                    )
                    messages.success(request, f'Order {order.order_number} rejected. Customer has been notified.')
                except Exception as e:
                    messages.warning(request, f'Order rejected but customer email failed: {e}')

            return HttpResponseRedirect(reverse('admin:orders_order_changelist'))

        # GET request - show verification form
        context = {
            'order': order,
            'title': f'Verify Payment for Order {order.order_number}',
            'opts': self.model._meta,
        }
        return render(request, 'admin/orders/verify_payment.html', context)

    def approve_payment_verification(self, request, queryset):
        pending_orders = queryset.filter(status='pending_verification')
        if not pending_orders.exists():
            messages.warning(request, 'No orders with pending verification selected.')
            return

        messages.info(request, f'To approve payments, please verify each order individually by clicking "Verify Payment" link.')
    approve_payment_verification.short_description = "Manually verify selected payments"

    def reject_payment_verification(self, request, queryset):
        cancelled_count = 0
        for order in queryset.filter(status='pending_verification'):
            order.status = 'cancelled'
            order.admin_note = f"Payment batch rejected by {request.user.username} at {timezone.now()}"
            order.save()
            cancelled_count += 1

        messages.success(request, f'{cancelled_count} orders marked as cancelled due to payment verification failure.')
    reject_payment_verification.short_description = "Reject payment verification (cancel orders)"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'event', 'quantity', 'price')
    list_filter = ('event__category', 'event__status')
    search_fields = ('order__email', 'event__title')

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'created_at', 'changed_by')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'reason', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')