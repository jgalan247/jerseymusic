from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from analytics.services import AnalyticsService
from analytics.models import DailyConnectionMetrics


class Command(BaseCommand):
    help = 'Update daily connection metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date in YYYY-MM-DD format (defaults to yesterday)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to update (defaults to 1)',
        )

    def handle(self, *args, **options):
        analytics_service = AnalyticsService()

        if options['date']:
            try:
                target_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            # Default to yesterday
            target_date = (timezone.now() - timedelta(days=1)).date()

        days_to_update = options['days']

        self.stdout.write(f"Updating daily metrics for {days_to_update} day(s) starting from {target_date}")

        updated_count = 0
        for i in range(days_to_update):
            date_to_update = target_date - timedelta(days=i)

            try:
                metrics = analytics_service.update_daily_metrics(date_to_update)
                updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Updated metrics for {date_to_update}: "
                        f"{metrics.connected_artists}/{metrics.total_artists} "
                        f"({metrics.connection_rate}% connected)"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to update metrics for {date_to_update}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted! Updated {updated_count} day(s) of metrics.")
        )