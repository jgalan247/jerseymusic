from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    SumUpConnectionEvent,
    DailyConnectionMetrics,
    EmailCampaignMetrics,
    EmailRecipient,
    ConnectionAlert,
    WeeklyReport
)


@admin.register(SumUpConnectionEvent)
class SumUpConnectionEventAdmin(admin.ModelAdmin):
    list_display = ['artist_display_name', 'event_type', 'created_at', 'ip_address']
    list_filter = ['event_type', 'created_at']
    search_fields = ['artist__display_name', 'artist__user__email']
    readonly_fields = ['created_at', 'metadata_display']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('artist', 'event_type', 'created_at')
        }),
        ('Tracking Info', {
            'fields': ('ip_address', 'user_agent', 'metadata_display'),
            'classes': ('collapse',)
        }),
    )

    def artist_display_name(self, obj):
        return obj.artist.display_name
    artist_display_name.short_description = 'Artist'

    def metadata_display(self, obj):
        if obj.metadata:
            return format_html('<pre>{}</pre>', str(obj.metadata))
        return 'No metadata'
    metadata_display.short_description = 'Metadata'


@admin.register(DailyConnectionMetrics)
class DailyConnectionMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'connection_rate', 'connected_artists',
        'total_artists', 'new_connections', 'oauth_completions'
    ]
    list_filter = ['date']
    ordering = ['-date']
    date_hierarchy = 'date'

    fieldsets = (
        ('Basic Metrics', {
            'fields': ('date', 'total_artists', 'connected_artists', 'connection_rate')
        }),
        ('Daily Changes', {
            'fields': ('new_connections', 'disconnections', 'invitations_sent')
        }),
        ('Funnel Metrics', {
            'fields': ('page_views', 'oauth_starts', 'oauth_completions', 'oauth_failures')
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.calculate_connection_rate()
        super().save_model(request, obj, form, change)


@admin.register(EmailCampaignMetrics)
class EmailCampaignMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status', 'total_recipients', 'open_rate',
        'click_rate', 'conversion_rate', 'sent_at'
    ]
    list_filter = ['status', 'sent_at']
    search_fields = ['name', 'subject']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Campaign Info', {
            'fields': ('name', 'subject', 'status', 'scheduled_at', 'sent_at')
        }),
        ('Recipients', {
            'fields': ('total_recipients', 'successful_sends', 'failed_sends')
        }),
        ('Engagement', {
            'fields': ('opens', 'unique_opens', 'clicks', 'unique_clicks')
        }),
        ('Conversions', {
            'fields': ('oauth_starts', 'oauth_completions')
        }),
        ('Calculated Rates', {
            'fields': ('open_rate', 'click_rate', 'conversion_rate'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.calculate_rates()
        super().save_model(request, obj, form, change)


class EmailRecipientInline(admin.TabularInline):
    model = EmailRecipient
    extra = 0
    readonly_fields = ['sent_at', 'first_opened_at', 'first_clicked_at', 'oauth_completed_at']
    fields = [
        'artist', 'delivered', 'opened', 'clicked',
        'oauth_started', 'oauth_completed'
    ]


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = [
        'campaign_name', 'artist_display_name', 'delivered',
        'opened', 'clicked', 'oauth_completed', 'sent_at'
    ]
    list_filter = [
        'delivered', 'opened', 'clicked', 'oauth_completed',
        'campaign__status', 'sent_at'
    ]
    search_fields = ['artist__display_name', 'artist__user__email', 'campaign__name']
    ordering = ['-sent_at']
    date_hierarchy = 'sent_at'

    fieldsets = (
        ('Campaign & Artist', {
            'fields': ('campaign', 'artist')
        }),
        ('Delivery Status', {
            'fields': ('sent_at', 'delivered', 'bounced')
        }),
        ('Engagement', {
            'fields': (
                'opened', 'first_opened_at', 'open_count',
                'clicked', 'first_clicked_at', 'click_count'
            )
        }),
        ('Conversion', {
            'fields': ('oauth_started', 'oauth_completed', 'oauth_completed_at')
        }),
    )

    def campaign_name(self, obj):
        return obj.campaign.name
    campaign_name.short_description = 'Campaign'

    def artist_display_name(self, obj):
        return obj.artist.display_name
    artist_display_name.short_description = 'Artist'


@admin.register(ConnectionAlert)
class ConnectionAlertAdmin(admin.ModelAdmin):
    list_display = [
        'alert_type', 'severity', 'triggered_at', 'acknowledged',
        'current_value', 'threshold_value'
    ]
    list_filter = ['alert_type', 'severity', 'acknowledged', 'triggered_at']
    search_fields = ['message']
    ordering = ['-triggered_at']
    date_hierarchy = 'triggered_at'

    fieldsets = (
        ('Alert Info', {
            'fields': ('alert_type', 'severity', 'message')
        }),
        ('Thresholds', {
            'fields': ('threshold_value', 'current_value')
        }),
        ('Status', {
            'fields': ('triggered_at', 'acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
    )

    readonly_fields = ['triggered_at']

    actions = ['mark_acknowledged']

    def mark_acknowledged(self, request, queryset):
        updated = queryset.update(
            acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} alert(s) marked as acknowledged.'
        )
    mark_acknowledged.short_description = 'Mark selected alerts as acknowledged'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.acknowledged:
            readonly_fields.extend(['acknowledged', 'acknowledged_by', 'acknowledged_at'])
        return readonly_fields


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = [
        'week_period', 'final_connection_rate', 'new_connections',
        'campaigns_sent', 'sent', 'generated_at'
    ]
    list_filter = ['sent', 'generated_at', 'week_start']
    ordering = ['-week_start']
    date_hierarchy = 'week_start'

    fieldsets = (
        ('Report Period', {
            'fields': ('week_start', 'week_end')
        }),
        ('Starting Metrics', {
            'fields': (
                'initial_total_artists', 'initial_connected_artists',
                'initial_connection_rate'
            )
        }),
        ('Ending Metrics', {
            'fields': (
                'final_total_artists', 'final_connected_artists',
                'final_connection_rate'
            )
        }),
        ('Weekly Activity', {
            'fields': (
                'new_connections', 'disconnections', 'invitations_sent',
                'emails_opened', 'links_clicked'
            )
        }),
        ('Campaign Performance', {
            'fields': (
                'campaigns_sent', 'average_open_rate',
                'average_click_rate', 'average_conversion_rate'
            )
        }),
        ('Analysis', {
            'fields': ('key_insights', 'recommendations')
        }),
        ('Status', {
            'fields': ('generated_at', 'sent', 'sent_at')
        }),
    )

    readonly_fields = ['generated_at', 'growth_rate_display']

    def week_period(self, obj):
        return f"{obj.week_start} to {obj.week_end}"
    week_period.short_description = 'Week Period'

    def growth_rate_display(self, obj):
        rate = obj.calculate_growth_rate()
        color = 'green' if rate >= 0 else 'red'
        return format_html(
            '<span style="color: {};">{:+.1f}%</span>',
            color, rate
        )
    growth_rate_display.short_description = 'Growth Rate'

    actions = ['mark_as_sent']

    def mark_as_sent(self, request, queryset):
        updated = queryset.update(sent=True, sent_at=timezone.now())
        self.message_user(
            request,
            f'{updated} report(s) marked as sent.'
        )
    mark_as_sent.short_description = 'Mark selected reports as sent'


# Admin site customization
admin.site.site_header = "SumUp Analytics Administration"
admin.site.site_title = "SumUp Analytics Admin"
admin.site.index_title = "Analytics Dashboard Administration"
