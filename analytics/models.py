"""Analytics models for tracking SumUp connection adoption and metrics."""

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import ArtistProfile
from decimal import Decimal

User = get_user_model()


class SumUpConnectionEvent(models.Model):
    """Track individual connection events in the funnel."""

    EVENT_TYPES = [
        ('invited', 'Invitation Sent'),
        ('email_opened', 'Email Opened'),
        ('link_clicked', 'Link Clicked'),
        ('page_viewed', 'Connection Page Viewed'),
        ('oauth_started', 'OAuth Started'),
        ('oauth_completed', 'OAuth Completed'),
        ('oauth_failed', 'OAuth Failed'),
        ('disconnected', 'Disconnected'),
    ]

    artist = models.ForeignKey(
        ArtistProfile,
        on_delete=models.CASCADE,
        related_name='connection_events'
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['artist', 'event_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.artist.display_name} - {self.get_event_type_display()} - {self.created_at}"


class DailyConnectionMetrics(models.Model):
    """Daily aggregated metrics for SumUp connections."""

    date = models.DateField(unique=True)
    total_artists = models.IntegerField(default=0)
    connected_artists = models.IntegerField(default=0)
    new_connections = models.IntegerField(default=0)
    disconnections = models.IntegerField(default=0)
    invitations_sent = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    oauth_starts = models.IntegerField(default=0)
    oauth_completions = models.IntegerField(default=0)
    oauth_failures = models.IntegerField(default=0)
    connection_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Connection Metrics"
        verbose_name_plural = "Daily Connection Metrics"

    def calculate_connection_rate(self):
        """Calculate the connection rate percentage."""
        if self.total_artists > 0:
            self.connection_rate = Decimal(
                (self.connected_artists / self.total_artists) * 100
            ).quantize(Decimal('0.01'))
        else:
            self.connection_rate = Decimal('0.00')
        return self.connection_rate

    def __str__(self):
        return f"{self.date} - {self.connected_artists}/{self.total_artists} ({self.connection_rate}%)"


class EmailCampaignMetrics(models.Model):
    """Track email campaign performance for SumUp connection invitations."""

    CAMPAIGN_STATUS = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=300)
    status = models.CharField(max_length=20, choices=CAMPAIGN_STATUS, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Recipients
    total_recipients = models.IntegerField(default=0)
    successful_sends = models.IntegerField(default=0)
    failed_sends = models.IntegerField(default=0)

    # Engagement metrics
    opens = models.IntegerField(default=0)
    unique_opens = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)

    # Conversion metrics
    oauth_starts = models.IntegerField(default=0)
    oauth_completions = models.IntegerField(default=0)

    # Calculated rates
    open_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    click_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def calculate_rates(self):
        """Calculate engagement and conversion rates."""
        if self.successful_sends > 0:
            self.open_rate = Decimal(
                (self.unique_opens / self.successful_sends) * 100
            ).quantize(Decimal('0.01'))

            self.click_rate = Decimal(
                (self.unique_clicks / self.successful_sends) * 100
            ).quantize(Decimal('0.01'))

            self.conversion_rate = Decimal(
                (self.oauth_completions / self.successful_sends) * 100
            ).quantize(Decimal('0.01'))
        else:
            self.open_rate = Decimal('0.00')
            self.click_rate = Decimal('0.00')
            self.conversion_rate = Decimal('0.00')

        return {
            'open_rate': self.open_rate,
            'click_rate': self.click_rate,
            'conversion_rate': self.conversion_rate
        }

    def __str__(self):
        return f"{self.name} - {self.status} - {self.conversion_rate}% conversion"


class EmailRecipient(models.Model):
    """Track individual email recipients and their engagement."""

    campaign = models.ForeignKey(
        EmailCampaignMetrics,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    artist = models.ForeignKey(
        ArtistProfile,
        on_delete=models.CASCADE,
        related_name='campaign_emails'
    )

    # Delivery status
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered = models.BooleanField(default=False)
    bounced = models.BooleanField(default=False)

    # Engagement tracking
    opened = models.BooleanField(default=False)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    open_count = models.IntegerField(default=0)

    clicked = models.BooleanField(default=False)
    first_clicked_at = models.DateTimeField(null=True, blank=True)
    click_count = models.IntegerField(default=0)

    # Conversion tracking
    oauth_started = models.BooleanField(default=False)
    oauth_completed = models.BooleanField(default=False)
    oauth_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['campaign', 'artist']
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.campaign.name} - {self.artist.display_name}"


class ConnectionAlert(models.Model):
    """Alerts for connection rate monitoring."""

    ALERT_TYPES = [
        ('low_rate', 'Low Connection Rate'),
        ('declining_rate', 'Declining Connection Rate'),
        ('stagnant_rate', 'Stagnant Connection Rate'),
        ('milestone_reached', 'Milestone Reached'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    message = models.TextField()
    threshold_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    current_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f"{self.get_severity_display()} - {self.get_alert_type_display()} - {self.triggered_at}"


class WeeklyReport(models.Model):
    """Weekly adoption progress reports."""

    week_start = models.DateField()
    week_end = models.DateField()

    # Metrics at start of week
    initial_total_artists = models.IntegerField(default=0)
    initial_connected_artists = models.IntegerField(default=0)
    initial_connection_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Metrics at end of week
    final_total_artists = models.IntegerField(default=0)
    final_connected_artists = models.IntegerField(default=0)
    final_connection_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Weekly activity
    new_connections = models.IntegerField(default=0)
    disconnections = models.IntegerField(default=0)
    invitations_sent = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    links_clicked = models.IntegerField(default=0)

    # Campaign performance
    campaigns_sent = models.IntegerField(default=0)
    average_open_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    average_click_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    average_conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Analysis
    key_insights = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-week_start']
        unique_together = ['week_start', 'week_end']

    def calculate_growth_rate(self):
        """Calculate the weekly growth rate."""
        if self.initial_connected_artists > 0:
            growth = ((self.final_connected_artists - self.initial_connected_artists)
                     / self.initial_connected_artists) * 100
            return Decimal(growth).quantize(Decimal('0.01'))
        elif self.final_connected_artists > 0:
            return Decimal('100.00')
        return Decimal('0.00')

    def __str__(self):
        return f"Week {self.week_start} to {self.week_end} - {self.final_connection_rate}% connected"