"""Analytics dashboard views for SumUp connection adoption monitoring."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Q, F, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, date
import json

from accounts.models import ArtistProfile
from .models import (
    SumUpConnectionEvent,
    DailyConnectionMetrics,
    EmailCampaignMetrics,
    EmailRecipient,
    ConnectionAlert,
    WeeklyReport
)
from .services import (
    AnalyticsService,
    FunnelTracker,
    AlertManager,
    ReportGenerator,
    EmailService
)


@staff_member_required
def analytics_dashboard(request):
    """Main analytics dashboard view."""
    analytics_service = AnalyticsService()

    # Get current metrics
    current_metrics = analytics_service.get_current_metrics()

    # Get recent alerts
    recent_alerts = ConnectionAlert.objects.filter(
        acknowledged=False
    )[:5]

    # Get chart data for the past 30 days
    chart_data = analytics_service.get_daily_metrics_chart(days=30)

    # Get funnel data
    funnel_data = analytics_service.get_conversion_funnel_data()

    # Get artists needing connection
    artists_need_connection = ArtistProfile.objects.filter(
        sumup_connection_status='not_connected',
        is_approved=True
    ).select_related('user')[:10]

    context = {
        'current_metrics': current_metrics,
        'recent_alerts': recent_alerts,
        'chart_data': json.dumps(chart_data),
        'funnel_data': funnel_data,
        'artists_need_connection': artists_need_connection,
    }

    return render(request, 'analytics/dashboard.html', context)


@staff_member_required
def connection_widgets_api(request):
    """API endpoint for connection widgets data."""
    analytics_service = AnalyticsService()

    total_artists = ArtistProfile.objects.filter(is_approved=True).count()
    connected_artists = ArtistProfile.objects.filter(
        sumup_connection_status='connected',
        is_approved=True
    ).count()

    connection_rate = (connected_artists / total_artists * 100) if total_artists > 0 else 0

    # Get daily change
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    yesterday_metrics = DailyConnectionMetrics.objects.filter(date=yesterday).first()
    yesterday_connected = yesterday_metrics.connected_artists if yesterday_metrics else 0

    daily_change = connected_artists - yesterday_connected

    # Get week-over-week change
    week_ago = today - timedelta(days=7)
    week_ago_metrics = DailyConnectionMetrics.objects.filter(date=week_ago).first()
    week_ago_connected = week_ago_metrics.connected_artists if week_ago_metrics else 0

    weekly_change = connected_artists - week_ago_connected

    return JsonResponse({
        'total_artists': total_artists,
        'connected_artists': connected_artists,
        'connection_rate': round(connection_rate, 2),
        'daily_change': daily_change,
        'weekly_change': weekly_change,
        'not_connected': total_artists - connected_artists,
    })


@staff_member_required
def conversion_funnel_view(request):
    """Conversion funnel analysis view."""
    funnel_tracker = FunnelTracker()

    # Get time range from request
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)

    funnel_data = funnel_tracker.get_funnel_data(start_date)

    # Get detailed breakdown
    funnel_details = funnel_tracker.get_detailed_breakdown(start_date)

    # Get conversion rates by stage
    conversion_rates = funnel_tracker.calculate_conversion_rates(funnel_data)

    context = {
        'funnel_data': funnel_data,
        'funnel_details': funnel_details,
        'conversion_rates': conversion_rates,
        'days': days,
        'start_date': start_date,
    }

    return render(request, 'analytics/conversion_funnel.html', context)


@staff_member_required
def daily_metrics_chart_api(request):
    """API endpoint for daily metrics chart data."""
    days = int(request.GET.get('days', 30))

    analytics_service = AnalyticsService()
    chart_data = analytics_service.get_daily_metrics_chart(days)

    return JsonResponse(chart_data)


@staff_member_required
def artists_need_connection(request):
    """List of artists who need to connect with reminder options."""
    # Filter parameters
    status_filter = request.GET.get('status', 'not_connected')
    sort_by = request.GET.get('sort', 'user__date_joined')
    search = request.GET.get('search', '')

    # Base queryset
    artists = ArtistProfile.objects.filter(
        is_approved=True
    ).select_related('user')

    # Apply filters
    if status_filter and status_filter != 'all':
        artists = artists.filter(sumup_connection_status=status_filter)

    if search:
        artists = artists.filter(
            Q(display_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    # Apply sorting
    if sort_by:
        artists = artists.order_by(sort_by)

    # Get engagement data for each artist
    artists_with_engagement = []
    for artist in artists:
        last_event = artist.connection_events.first()
        campaigns = artist.campaign_emails.filter(
            campaign__status='sent'
        ).select_related('campaign')

        engagement_data = {
            'artist': artist,
            'last_event': last_event,
            'total_campaigns': campaigns.count(),
            'opened_any': campaigns.filter(opened=True).exists(),
            'clicked_any': campaigns.filter(clicked=True).exists(),
            'days_since_last_event': (
                (timezone.now().date() - last_event.created_at.date()).days
                if last_event else None
            ),
        }
        artists_with_engagement.append(engagement_data)

    # Pagination
    paginator = Paginator(artists_with_engagement, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'search': search,
    }

    return render(request, 'analytics/artists_need_connection.html', context)


@staff_member_required
def email_campaigns_dashboard(request):
    """Email campaign performance dashboard."""
    # Get all campaigns
    campaigns = EmailCampaignMetrics.objects.all()

    # Get summary stats
    total_campaigns = campaigns.count()
    total_recipients = campaigns.aggregate(
        total=Sum('total_recipients')
    )['total'] or 0

    avg_open_rate = campaigns.aggregate(
        avg=Avg('open_rate')
    )['avg'] or 0

    avg_conversion_rate = campaigns.aggregate(
        avg=Avg('conversion_rate')
    )['avg'] or 0

    # Recent campaigns
    recent_campaigns = campaigns[:10]

    # Performance over time
    campaign_performance = []
    for campaign in recent_campaigns:
        campaign_performance.append({
            'name': campaign.name,
            'sent_date': campaign.sent_at.strftime('%Y-%m-%d') if campaign.sent_at else '',
            'open_rate': float(campaign.open_rate),
            'click_rate': float(campaign.click_rate),
            'conversion_rate': float(campaign.conversion_rate),
        })

    context = {
        'total_campaigns': total_campaigns,
        'total_recipients': total_recipients,
        'avg_open_rate': round(avg_open_rate, 2),
        'avg_conversion_rate': round(avg_conversion_rate, 2),
        'recent_campaigns': recent_campaigns,
        'campaign_performance': json.dumps(campaign_performance),
    }

    return render(request, 'analytics/email_campaigns.html', context)


@staff_member_required
def send_reminder_emails_api(request):
    """API endpoint to send reminder emails to artists."""
    if request.method == 'POST':
        artist_ids = request.POST.getlist('artist_ids')

        if not artist_ids:
            return JsonResponse({
                'success': False,
                'message': 'No artists selected'
            })

        try:
            email_service = EmailService()
            count = email_service.send_reminder_emails(artist_ids)

            return JsonResponse({
                'success': True,
                'message': f'Sent reminder emails to {count} artists'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error sending emails: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@staff_member_required
def track_event_api(request):
    """API endpoint to track connection events."""
    if request.method == 'POST':
        data = json.loads(request.body)

        artist_id = data.get('artist_id')
        event_type = data.get('event_type')
        metadata = data.get('metadata', {})

        if not artist_id or not event_type:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            })

        try:
            artist = ArtistProfile.objects.get(id=artist_id)

            # Track the event
            event = SumUpConnectionEvent.objects.create(
                artist=artist,
                event_type=event_type,
                metadata=metadata,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            # Update daily metrics
            analytics_service = AnalyticsService()
            analytics_service.update_daily_metrics(timezone.now().date())

            return JsonResponse({
                'success': True,
                'event_id': event.id
            })

        except ArtistProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Artist not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@staff_member_required
def alerts_dashboard(request):
    """Connection alerts dashboard."""
    # Get all alerts with filter options
    alert_filter = request.GET.get('filter', 'unacknowledged')

    alerts = ConnectionAlert.objects.all()

    if alert_filter == 'unacknowledged':
        alerts = alerts.filter(acknowledged=False)
    elif alert_filter == 'critical':
        alerts = alerts.filter(severity='critical')
    elif alert_filter == 'warning':
        alerts = alerts.filter(severity='warning')

    # Get summary stats
    total_alerts = ConnectionAlert.objects.count()
    unacknowledged_alerts = ConnectionAlert.objects.filter(acknowledged=False).count()
    critical_alerts = ConnectionAlert.objects.filter(severity='critical', acknowledged=False).count()

    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'alert_filter': alert_filter,
        'total_alerts': total_alerts,
        'unacknowledged_alerts': unacknowledged_alerts,
        'critical_alerts': critical_alerts,
    }

    return render(request, 'analytics/alerts_dashboard.html', context)


@staff_member_required
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert."""
    if request.method == 'POST':
        try:
            alert = get_object_or_404(ConnectionAlert, id=alert_id)
            alert.acknowledged = True
            alert.acknowledged_by = request.user
            alert.acknowledged_at = timezone.now()
            alert.save()

            return JsonResponse({
                'success': True,
                'message': 'Alert acknowledged successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return redirect('analytics:alerts')


@staff_member_required
def weekly_reports_dashboard(request):
    """Weekly reports dashboard."""
    # Get all reports
    reports = WeeklyReport.objects.all()[:20]

    # Get summary stats
    total_reports = WeeklyReport.objects.count()
    sent_reports = WeeklyReport.objects.filter(sent=True).count()

    # Get recent report data for chart
    recent_reports = WeeklyReport.objects.all()[:12]
    chart_data = {
        'weeks': [f"{report.week_start}" for report in reversed(recent_reports)],
        'connection_rates': [float(report.final_connection_rate) for report in reversed(recent_reports)],
        'new_connections': [report.new_connections for report in reversed(recent_reports)],
    }

    context = {
        'reports': reports,
        'total_reports': total_reports,
        'sent_reports': sent_reports,
        'chart_data': json.dumps(chart_data),
    }

    return render(request, 'analytics/weekly_reports.html', context)


@staff_member_required
def generate_weekly_report_api(request):
    """API endpoint to generate a weekly report."""
    if request.method == 'POST':
        try:
            report_generator = ReportGenerator()

            # Generate report for the current week
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

            report = report_generator.generate_weekly_report(week_start, week_end)

            return JsonResponse({
                'success': True,
                'message': 'Weekly report generated successfully',
                'report_id': report.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error generating report: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})
