from django.contrib import admin
from events.models import Event, EventImage, Category, Ticket, EventFee

# Register Category
admin.site.register(Category)

# Register Event with approval actions
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organiser', 'event_date', 'ticket_price', 'tickets_sold', 'capacity', 'status', 'created_at']
    list_filter = ['status', 'event_date', 'category']
    search_fields = ['title', 'description', 'venue_name']
    actions = ['make_published', 'make_draft', 'mark_sold_out']
    date_hierarchy = 'event_date'

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
    list_display = ['ticket_number', 'event', 'customer', 'status', 'purchase_date']
    list_filter = ['status', 'purchase_date', 'event__event_date']
    search_fields = ['ticket_number', 'event__title', 'customer__email']
    readonly_fields = ['ticket_number', 'qr_code']

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