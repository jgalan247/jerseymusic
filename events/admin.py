from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from events.models import Event, EventImage, Category, Ticket, EventFee, TicketTier

# Register Category
admin.site.register(Category)


class TicketTierInline(admin.TabularInline):
    """Inline admin for ticket tiers."""
    model = TicketTier
    extra = 0
    fields = ['tier_type', 'name', 'price', 'quantity_available', 'quantity_sold', 'is_active', 'min_purchase', 'max_purchase', 'sort_order']
    readonly_fields = ['quantity_sold']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            # Add help text showing remaining capacity
            formset.help_texts = {
                'quantity_available': f'Event capacity: {obj.capacity} | Sold: {obj.tickets_sold} | Available: {obj.tickets_available}'
            }
        return formset


# Register Event with approval actions
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'organiser',
        'event_date',
        'pricing_tier_display',
        'ticket_price',
        'tickets_sold',
        'capacity',
        'processing_fee_display',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'event_date', 'category', 'processing_fee_passed_to_customer']
    search_fields = ['title', 'description', 'venue_name', 'organiser__email']
    actions = ['make_published', 'make_draft', 'mark_sold_out']
    date_hierarchy = 'event_date'
    inlines = [TicketTierInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'organiser', 'category', 'description')
        }),
        ('Venue & Date', {
            'fields': ('venue_name', 'venue_address', 'event_date', 'event_time')
        }),
        ('Ticketing & Pricing', {
            'fields': (
                'capacity',
                'tickets_sold',
                'ticket_price',
                'processing_fee_passed_to_customer',
                'pricing_breakdown_display'
            ),
            'description': 'Configure ticket pricing and capacity. Platform fee is calculated based on capacity tier.'
        }),
        ('Media & Status', {
            'fields': ('main_image', 'status', 'featured')
        }),
        ('Jersey-Specific', {
            'fields': ('is_local_organiser', 'jersey_heritage'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['slug', 'tickets_sold', 'created_at', 'updated_at', 'pricing_breakdown_display']

    def pricing_tier_display(self, obj):
        """Display pricing tier based on capacity."""
        tier = obj.get_pricing_tier()
        if tier:
            return format_html(
                '<span style="background: #e3f2fd; padding: 4px 8px; border-radius: 4px; font-weight: bold;">'
                'Tier {}: £{}'
                '</span>',
                tier['tier'],
                tier['fee']
            )
        return format_html('<span style="color: orange;">Custom pricing required</span>')
    pricing_tier_display.short_description = 'Platform Fee Tier'

    def processing_fee_display(self, obj):
        """Display who pays the processing fee."""
        if obj.processing_fee_passed_to_customer:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Customer Pays</span>'
            )
        return format_html(
            '<span style="color: orange;">✗ Organizer Absorbs</span>'
        )
    processing_fee_display.short_description = 'Processing Fee (1.69%)'

    def pricing_breakdown_display(self, obj):
        """Show complete pricing breakdown."""
        breakdown = obj.get_fee_breakdown()

        if not breakdown['tier']:
            return format_html(
                '<div style="background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107;">'
                '<strong>⚠️ Capacity exceeds 500 tickets</strong><br>'
                'Contact admin@coderra.je for custom pricing'
                '</div>'
            )

        html = f'''
        <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; font-family: monospace;">
            <strong>💰 Fee Breakdown (Per Ticket):</strong><br><br>

            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #e3f2fd;">
                    <td style="padding: 8px;"><strong>Pricing Tier:</strong></td>
                    <td style="padding: 8px;">{breakdown['tier']['name']} (Tier {breakdown['tier']['tier']})</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">Base Ticket Price:</td>
                    <td style="padding: 8px;">£{breakdown['base_ticket_price']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">Platform Fee:</td>
                    <td style="padding: 8px;">£{breakdown['platform_fee']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">Processing Fee (1.69%):</td>
                    <td style="padding: 8px;">£{breakdown['processing_fee']:.2f}</td>
                </tr>
                <tr style="border-top: 2px solid #ddd; background: #fff3cd;">
                    <td style="padding: 8px;"><strong>Customer Pays:</strong></td>
                    <td style="padding: 8px;"><strong>£{breakdown['customer_pays']:.2f}</strong></td>
                </tr>
                <tr style="background: #c8e6c9;">
                    <td style="padding: 8px;"><strong>Organizer Receives:</strong></td>
                    <td style="padding: 8px;"><strong>£{breakdown['organizer_receives']:.2f}</strong></td>
                </tr>
            </table>

            <br>
            <strong>📊 Full Event Projection:</strong><br>
            <table style="width: 100%; margin-top: 10px; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px;">Total Capacity:</td>
                    <td style="padding: 8px;">{breakdown['total_capacity']} tickets</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">Tickets Sold:</td>
                    <td style="padding: 8px;">{breakdown['tickets_sold']} ({breakdown['tickets_sold']/breakdown['total_capacity']*100:.1f}%)</td>
                </tr>
                <tr style="background: #e8f5e9; font-weight: bold;">
                    <td style="padding: 8px;">Est. Total Revenue (if sold out):</td>
                    <td style="padding: 8px;">£{breakdown['estimated_total_revenue']:.2f}</td>
                </tr>
            </table>

            <div style="margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 4px;">
                <strong>ℹ️ Note:</strong>
                {'Customer pays the 1.69% processing fee (£' + f"{breakdown['processing_fee']:.2f}" + ' added to ticket price)' if breakdown['processing_fee_passed_to_customer'] else 'Organizer absorbs the 1.69% processing fee (deducted from revenue)'}
            </div>
        </div>
        '''

        return mark_safe(html)
    pricing_breakdown_display.short_description = 'Fee Breakdown'

    def make_published(self, request, queryset):
        count = queryset.update(status='published')
        self.message_user(request, f'{count} event(s) published!')
    make_published.short_description = "✅ Publish selected events"

    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'{count} event(s) set to DRAFT')
    make_draft.short_description = "📝 Set selected events to DRAFT"

    def mark_sold_out(self, request, queryset):
        count = queryset.update(status='sold_out')
        self.message_user(request, f'{count} event(s) marked as sold out')
    mark_sold_out.short_description = "🎫 Mark as SOLD OUT"

# Register Ticket
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'event', 'customer', 'tier_display', 'status', 'validation_status', 'purchase_date']
    list_filter = ['status', 'is_validated', 'purchase_date', 'event__event_date', 'ticket_tier__tier_type']
    search_fields = ['ticket_number', 'event__title', 'customer__email', 'customer_email']
    readonly_fields = ['ticket_number', 'qr_code', 'validation_hash', 'qr_data', 'pdf_file']

    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'event', 'customer', 'customer_email', 'customer_name', 'ticket_tier', 'order')
        }),
        ('Status & Pricing', {
            'fields': ('status', 'price', 'purchase_date')
        }),
        ('Validation', {
            'fields': ('is_validated', 'validated_at', 'validated_by', 'validation_hash', 'qr_data'),
            'description': 'Ticket validation information for entry at the event'
        }),
        ('Files', {
            'fields': ('qr_code', 'pdf_file'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('seat_number', 'special_requirements'),
            'classes': ('collapse',)
        }),
    )

    def tier_display(self, obj):
        """Display ticket tier if available."""
        if obj.ticket_tier:
            return format_html(
                '<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">{}</span>',
                obj.ticket_tier.get_tier_type_display()
            )
        return format_html('<span style="color: #999;">Standard</span>')
    tier_display.short_description = 'Tier'

    def validation_status(self, obj):
        """Display validation status."""
        if obj.is_validated:
            return format_html(
                '<span style="color: green;">✓ Validated</span><br>'
                '<small>{}</small>',
                obj.validated_at.strftime('%Y-%m-%d %H:%M') if obj.validated_at else ''
            )
        return format_html('<span style="color: orange;">Not Validated</span>')
    validation_status.short_description = 'Validation'


# Register TicketTier
@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    """Standalone admin for ticket tiers."""
    list_display = ['name', 'event', 'tier_type', 'price', 'tickets_remaining_display', 'is_active', 'sort_order']
    list_filter = ['tier_type', 'is_active', 'event__event_date']
    search_fields = ['name', 'event__title', 'description']
    ordering = ['event', 'sort_order', 'tier_type']

    fieldsets = (
        ('Tier Information', {
            'fields': ('event', 'tier_type', 'name', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'quantity_available', 'quantity_sold', 'is_active')
        }),
        ('Purchase Limits', {
            'fields': ('min_purchase', 'max_purchase'),
            'description': 'Set minimum and maximum tickets per purchase for this tier'
        }),
        ('Display', {
            'fields': ('sort_order',),
            'description': 'Lower numbers display first'
        }),
    )

    readonly_fields = ['quantity_sold']

    def tickets_remaining_display(self, obj):
        """Display tickets remaining with progress bar."""
        remaining = obj.tickets_remaining
        total = obj.quantity_available
        percentage = (obj.quantity_sold / total * 100) if total > 0 else 0

        if obj.is_sold_out:
            color = '#f44336'
            status = 'SOLD OUT'
        elif remaining < 10:
            color = '#ff9800'
            status = f'{remaining} left'
        else:
            color = '#4caf50'
            status = f'{remaining} available'

        return format_html(
            '<div style="width: 150px;">'
            '<div style="background: #e0e0e0; border-radius: 10px; overflow: hidden; height: 20px;">'
            '<div style="background: {}; width: {}%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold;">'
            '{:.0f}%'
            '</div>'
            '</div>'
            '<small style="color: {};">{}</small>'
            '</div>',
            color,
            percentage,
            percentage,
            color,
            status
        )
    tickets_remaining_display.short_description = 'Availability'


# Register EventFee
@admin.register(EventFee)
class EventFeeAdmin(admin.ModelAdmin):
    list_display = ['event', 'amount', 'payment_status', 'due_date', 'paid_date']
    list_filter = ['payment_status', 'due_date']
    search_fields = ['event__title', 'event__organiser__email']
    actions = ['mark_as_paid', 'mark_as_overdue']

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(payment_status='paid', paid_date=timezone.now())
        self.message_user(request, f'{count} fee(s) marked as paid!')
    mark_as_paid.short_description = "💰 Mark as PAID"

    def mark_as_overdue(self, request, queryset):
        count = queryset.update(payment_status='overdue')
        self.message_user(request, f'{count} fee(s) marked as overdue')
    mark_as_overdue.short_description = "⚠️ Mark as OVERDUE"

# Register EventImage
admin.site.register(EventImage)

# Customize admin header
admin.site.site_header = "🎫 Jersey Events Admin"
admin.site.site_title = "Jersey Events Admin"
admin.site.index_title = "Events Administration"