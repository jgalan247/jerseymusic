"""Services for analytics data processing and calculations."""

from django.utils import timezone
from django.db.models import Count, Q, F, Sum, Avg
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta, date
from decimal import Decimal

from accounts.models import ArtistProfile
from .models import (
    SumUpConnectionEvent,
    DailyConnectionMetrics,
    EmailCampaignMetrics,
    EmailRecipient,
    ConnectionAlert,
    WeeklyReport
)


class AnalyticsService:
    """Service for analytics data processing."""

    def get_current_metrics(self):
        """Get current connection metrics."""
        total_artists = ArtistProfile.objects.filter(is_approved=True).count()
        connected_artists = ArtistProfile.objects.filter(
            sumup_connection_status='connected',
            is_approved=True
        ).count()

        connection_rate = (connected_artists / total_artists * 100) if total_artists > 0 else 0

        # Get today's activity
        today = timezone.now().date()
        today_events = SumUpConnectionEvent.objects.filter(
            created_at__date=today
        )

        return {
            'total_artists': total_artists,
            'connected_artists': connected_artists,
            'not_connected_artists': total_artists - connected_artists,
            'connection_rate': round(connection_rate, 2),
            'today_page_views': today_events.filter(event_type='page_viewed').count(),
            'today_oauth_starts': today_events.filter(event_type='oauth_started').count(),
            'today_completions': today_events.filter(event_type='oauth_completed').count(),
        }

    def get_daily_metrics_chart(self, days=30):
        """Get chart data for daily metrics."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        metrics = DailyConnectionMetrics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')

        chart_data = {
            'labels': [],
            'datasets': [
                {
                    'label': 'Connection Rate (%)',
                    'data': [],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                    'yAxisID': 'y',
                },
                {
                    'label': 'New Connections',
                    'data': [],
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                    'yAxisID': 'y1',
                },
                {
                    'label': 'Page Views',
                    'data': [],
                    'borderColor': 'rgb(255, 206, 86)',
                    'backgroundColor': 'rgba(255, 206, 86, 0.1)',
                    'yAxisID': 'y1',
                }
            ]
        }

        for metric in metrics:
            chart_data['labels'].append(metric.date.strftime('%m/%d'))
            chart_data['datasets'][0]['data'].append(float(metric.connection_rate))
            chart_data['datasets'][1]['data'].append(metric.new_connections)
            chart_data['datasets'][2]['data'].append(metric.page_views)

        return chart_data

    def get_conversion_funnel_data(self):
        """Get conversion funnel data."""
        # Get data for the past 30 days
        start_date = timezone.now().date() - timedelta(days=30)

        funnel_data = {
            'invited': SumUpConnectionEvent.objects.filter(
                event_type='invited',
                created_at__date__gte=start_date
            ).values('artist').distinct().count(),

            'email_opened': SumUpConnectionEvent.objects.filter(
                event_type='email_opened',
                created_at__date__gte=start_date
            ).values('artist').distinct().count(),

            'page_viewed': SumUpConnectionEvent.objects.filter(
                event_type='page_viewed',
                created_at__date__gte=start_date
            ).values('artist').distinct().count(),

            'oauth_started': SumUpConnectionEvent.objects.filter(
                event_type='oauth_started',
                created_at__date__gte=start_date
            ).values('artist').distinct().count(),

            'oauth_completed': SumUpConnectionEvent.objects.filter(
                event_type='oauth_completed',
                created_at__date__gte=start_date
            ).values('artist').distinct().count(),
        }

        # Calculate conversion rates
        funnel_data['email_open_rate'] = (
            funnel_data['email_opened'] / funnel_data['invited'] * 100
            if funnel_data['invited'] > 0 else 0
        )

        funnel_data['page_view_rate'] = (
            funnel_data['page_viewed'] / funnel_data['email_opened'] * 100
            if funnel_data['email_opened'] > 0 else 0
        )

        funnel_data['oauth_start_rate'] = (
            funnel_data['oauth_started'] / funnel_data['page_viewed'] * 100
            if funnel_data['page_viewed'] > 0 else 0
        )

        funnel_data['completion_rate'] = (
            funnel_data['oauth_completed'] / funnel_data['oauth_started'] * 100
            if funnel_data['oauth_started'] > 0 else 0
        )

        funnel_data['overall_conversion_rate'] = (
            funnel_data['oauth_completed'] / funnel_data['invited'] * 100
            if funnel_data['invited'] > 0 else 0
        )

        return funnel_data

    def update_daily_metrics(self, target_date=None):
        """Update daily metrics for a specific date."""
        if target_date is None:
            target_date = timezone.now().date()

        # Get or create daily metrics record
        metrics, created = DailyConnectionMetrics.objects.get_or_create(
            date=target_date,
            defaults={}
        )

        # Calculate current totals
        total_artists = ArtistProfile.objects.filter(is_approved=True).count()
        connected_artists = ArtistProfile.objects.filter(
            sumup_connection_status='connected',
            is_approved=True
        ).count()

        # Get daily events
        daily_events = SumUpConnectionEvent.objects.filter(
            created_at__date=target_date
        )

        # Update metrics
        metrics.total_artists = total_artists
        metrics.connected_artists = connected_artists
        metrics.invitations_sent = daily_events.filter(event_type='invited').count()
        metrics.page_views = daily_events.filter(event_type='page_viewed').count()
        metrics.oauth_starts = daily_events.filter(event_type='oauth_started').count()
        metrics.oauth_completions = daily_events.filter(event_type='oauth_completed').count()
        metrics.oauth_failures = daily_events.filter(event_type='oauth_failed').count()

        # Calculate new connections for the day
        if not created:
            # Get previous day's connected count
            prev_day = target_date - timedelta(days=1)
            prev_metrics = DailyConnectionMetrics.objects.filter(date=prev_day).first()
            prev_connected = prev_metrics.connected_artists if prev_metrics else 0
            metrics.new_connections = max(0, connected_artists - prev_connected)

        metrics.calculate_connection_rate()
        metrics.save()

        return metrics


class FunnelTracker:
    """Service for tracking conversion funnel."""

    def get_funnel_data(self, start_date):
        """Get detailed funnel data."""
        events_by_type = SumUpConnectionEvent.objects.filter(
            created_at__date__gte=start_date
        ).values('event_type').annotate(
            unique_artists=Count('artist', distinct=True),
            total_events=Count('id')
        )

        funnel_data = {}
        for event in events_by_type:
            funnel_data[event['event_type']] = {
                'unique_artists': event['unique_artists'],
                'total_events': event['total_events']
            }

        return funnel_data

    def get_detailed_breakdown(self, start_date):
        """Get detailed funnel breakdown by artist."""
        artists_with_events = SumUpConnectionEvent.objects.filter(
            created_at__date__gte=start_date
        ).values('artist').annotate(
            events=Count('id'),
            last_event=F('created_at')
        ).order_by('-events')

        return artists_with_events

    def calculate_conversion_rates(self, funnel_data):
        """Calculate conversion rates between funnel stages."""
        rates = {}

        event_order = [
            'invited', 'email_opened', 'page_viewed',
            'oauth_started', 'oauth_completed'
        ]

        for i, current_event in enumerate(event_order):
            if i > 0:
                previous_event = event_order[i - 1]
                current_count = funnel_data.get(current_event, {}).get('unique_artists', 0)
                previous_count = funnel_data.get(previous_event, {}).get('unique_artists', 0)

                if previous_count > 0:
                    rates[f"{previous_event}_to_{current_event}"] = (
                        current_count / previous_count * 100
                    )
                else:
                    rates[f"{previous_event}_to_{current_event}"] = 0

        return rates


class AlertManager:
    """Service for managing connection rate alerts."""

    def __init__(self):
        self.thresholds = {
            'low_rate': Decimal('50.00'),  # Alert if connection rate < 50%
            'declining_rate': Decimal('5.00'),  # Alert if rate declines by > 5%
            'stagnant_days': 7,  # Alert if no progress for 7 days
        }

    def check_connection_rate_alerts(self):
        """Check for connection rate alerts."""
        today = timezone.now().date()
        current_metrics = DailyConnectionMetrics.objects.filter(date=today).first()

        if not current_metrics:
            return

        alerts = []

        # Check for low connection rate
        if current_metrics.connection_rate < self.thresholds['low_rate']:
            alert = self.create_alert(
                alert_type='low_rate',
                severity='warning' if current_metrics.connection_rate > 30 else 'critical',
                message=f"Connection rate is {current_metrics.connection_rate}%, below threshold of {self.thresholds['low_rate']}%",
                threshold_value=self.thresholds['low_rate'],
                current_value=current_metrics.connection_rate
            )
            alerts.append(alert)

        # Check for declining rate
        week_ago = today - timedelta(days=7)
        week_ago_metrics = DailyConnectionMetrics.objects.filter(date=week_ago).first()

        if week_ago_metrics:
            rate_change = current_metrics.connection_rate - week_ago_metrics.connection_rate

            if rate_change < -self.thresholds['declining_rate']:
                alert = self.create_alert(
                    alert_type='declining_rate',
                    severity='warning',
                    message=f"Connection rate has declined by {abs(rate_change):.2f}% over the past week",
                    threshold_value=self.thresholds['declining_rate'],
                    current_value=abs(rate_change)
                )
                alerts.append(alert)

        # Check for stagnant rate
        stagnant_days = self.check_stagnant_rate(today)
        if stagnant_days >= self.thresholds['stagnant_days']:
            alert = self.create_alert(
                alert_type='stagnant_rate',
                severity='info',
                message=f"No new connections for {stagnant_days} days",
                current_value=Decimal(str(stagnant_days))
            )
            alerts.append(alert)

        return alerts

    def create_alert(self, alert_type, severity, message, threshold_value=None, current_value=None):
        """Create a new alert."""
        # Check if similar alert already exists
        existing_alert = ConnectionAlert.objects.filter(
            alert_type=alert_type,
            acknowledged=False,
            triggered_at__date=timezone.now().date()
        ).first()

        if existing_alert:
            return existing_alert

        alert = ConnectionAlert.objects.create(
            alert_type=alert_type,
            severity=severity,
            message=message,
            threshold_value=threshold_value,
            current_value=current_value
        )

        return alert

    def check_stagnant_rate(self, end_date):
        """Check how many days since last new connection."""
        metrics = DailyConnectionMetrics.objects.filter(
            date__lte=end_date,
            new_connections__gt=0
        ).order_by('-date').first()

        if metrics:
            return (end_date - metrics.date).days
        else:
            return 999  # No connections ever


class ReportGenerator:
    """Service for generating weekly reports."""

    def generate_weekly_report(self, week_start, week_end):
        """Generate a weekly adoption report."""
        # Check if report already exists
        existing_report = WeeklyReport.objects.filter(
            week_start=week_start,
            week_end=week_end
        ).first()

        if existing_report:
            return existing_report

        # Get metrics for the week
        start_metrics = DailyConnectionMetrics.objects.filter(
            date=week_start
        ).first()

        end_metrics = DailyConnectionMetrics.objects.filter(
            date=week_end
        ).first()

        # Get weekly activity
        weekly_events = SumUpConnectionEvent.objects.filter(
            created_at__date__range=[week_start, week_end]
        )

        # Get campaign data
        weekly_campaigns = EmailCampaignMetrics.objects.filter(
            sent_at__date__range=[week_start, week_end]
        )

        # Create report
        report = WeeklyReport.objects.create(
            week_start=week_start,
            week_end=week_end,
            initial_total_artists=start_metrics.total_artists if start_metrics else 0,
            initial_connected_artists=start_metrics.connected_artists if start_metrics else 0,
            initial_connection_rate=start_metrics.connection_rate if start_metrics else Decimal('0.00'),
            final_total_artists=end_metrics.total_artists if end_metrics else 0,
            final_connected_artists=end_metrics.connected_artists if end_metrics else 0,
            final_connection_rate=end_metrics.connection_rate if end_metrics else Decimal('0.00'),
            new_connections=weekly_events.filter(event_type='oauth_completed').count(),
            disconnections=weekly_events.filter(event_type='disconnected').count(),
            invitations_sent=weekly_events.filter(event_type='invited').count(),
            emails_opened=weekly_events.filter(event_type='email_opened').count(),
            links_clicked=weekly_events.filter(event_type='link_clicked').count(),
            campaigns_sent=weekly_campaigns.filter(status='sent').count(),
            average_open_rate=weekly_campaigns.aggregate(avg=Avg('open_rate'))['avg'] or Decimal('0.00'),
            average_click_rate=weekly_campaigns.aggregate(avg=Avg('click_rate'))['avg'] or Decimal('0.00'),
            average_conversion_rate=weekly_campaigns.aggregate(avg=Avg('conversion_rate'))['avg'] or Decimal('0.00'),
        )

        # Generate insights and recommendations
        report.key_insights = self.generate_insights(report)
        report.recommendations = self.generate_recommendations(report)
        report.save()

        return report

    def generate_insights(self, report):
        """Generate key insights for the report."""
        insights = []

        # Connection rate change
        rate_change = report.final_connection_rate - report.initial_connection_rate
        if rate_change > 0:
            insights.append(f"Connection rate increased by {rate_change:.2f}% this week")
        elif rate_change < 0:
            insights.append(f"Connection rate decreased by {abs(rate_change):.2f}% this week")
        else:
            insights.append("Connection rate remained stable this week")

        # New artist growth
        artist_growth = report.final_total_artists - report.initial_total_artists
        if artist_growth > 0:
            insights.append(f"{artist_growth} new artists joined the platform")

        # Campaign performance
        if report.campaigns_sent > 0:
            if report.average_conversion_rate > 10:
                insights.append("Email campaigns performed exceptionally well")
            elif report.average_conversion_rate > 5:
                insights.append("Email campaigns performed above average")
            else:
                insights.append("Email campaign performance needs improvement")

        return "\n".join(insights)

    def generate_recommendations(self, report):
        """Generate recommendations for the report."""
        recommendations = []

        # Based on connection rate
        if report.final_connection_rate < 50:
            recommendations.append("Focus on improving onboarding process to increase connection rate")

        # Based on funnel performance
        if report.links_clicked > 0 and report.new_connections == 0:
            recommendations.append("Artists are clicking but not completing OAuth - review connection flow")

        # Based on email performance
        if report.average_open_rate < 20:
            recommendations.append("Improve email subject lines to increase open rates")

        if report.average_click_rate < 5:
            recommendations.append("Optimize email content and call-to-action buttons")

        # Growth recommendations
        if report.final_total_artists - report.initial_total_artists == 0:
            recommendations.append("Focus on artist acquisition to grow the platform")

        return "\n".join(recommendations)


class EmailService:
    """Service for sending reminder emails."""

    def send_reminder_emails(self, artist_ids):
        """Send reminder emails to specific artists."""
        artists = ArtistProfile.objects.filter(
            id__in=artist_ids,
            sumup_connection_status='not_connected'
        ).select_related('user')

        sent_count = 0

        for artist in artists:
            try:
                # Create email campaign entry
                campaign, created = EmailCampaignMetrics.objects.get_or_create(
                    name=f"Connection Reminder - {timezone.now().date()}",
                    defaults={
                        'subject': 'Complete Your SumUp Connection - Jersey Events',
                        'status': 'sent',
                        'sent_at': timezone.now(),
                    }
                )

                # Track recipient
                recipient, created = EmailRecipient.objects.get_or_create(
                    campaign=campaign,
                    artist=artist,
                    defaults={
                        'sent_at': timezone.now(),
                        'delivered': True,
                    }
                )

                # Send email
                self.send_connection_reminder(artist)

                # Track the event
                SumUpConnectionEvent.objects.create(
                    artist=artist,
                    event_type='invited',
                    metadata={'campaign_id': campaign.id}
                )

                sent_count += 1

            except Exception as e:
                print(f"Failed to send email to {artist.user.email}: {e}")

        return sent_count

    def send_connection_reminder(self, artist):
        """Send connection reminder email to an artist."""
        subject = 'Complete Your SumUp Connection - Jersey Events'

        context = {
            'artist': artist,
            'connection_url': f"{settings.SITE_URL}/accounts/sumup/connect/",
        }

        html_content = render_to_string('emails/connection_reminder.html', context)
        plain_content = render_to_string('emails/connection_reminder.txt', context)

        send_mail(
            subject=subject,
            message=plain_content,
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[artist.user.email],
            fail_silently=False,
        )