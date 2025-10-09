"""URL configuration for analytics app."""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main dashboard
    path('', views.analytics_dashboard, name='dashboard'),

    # API endpoints
    path('api/widgets/', views.connection_widgets_api, name='widgets_api'),
    path('api/daily-chart/', views.daily_metrics_chart_api, name='daily_chart_api'),
    path('api/track-event/', views.track_event_api, name='track_event_api'),
    path('api/send-reminders/', views.send_reminder_emails_api, name='send_reminders_api'),

    # Detailed views
    path('funnel/', views.conversion_funnel_view, name='funnel'),
    path('artists/', views.artists_need_connection, name='artists_need_connection'),
    path('campaigns/', views.email_campaigns_dashboard, name='email_campaigns'),
    path('alerts/', views.alerts_dashboard, name='alerts'),
    path('reports/', views.weekly_reports_dashboard, name='weekly_reports'),

    # Alert management
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),

    # Report generation
    path('api/generate-report/', views.generate_weekly_report_api, name='generate_report_api'),
]