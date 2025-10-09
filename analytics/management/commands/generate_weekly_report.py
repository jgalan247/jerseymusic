from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from analytics.services import ReportGenerator


class Command(BaseCommand):
    help = 'Generate weekly adoption reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week-start',
            type=str,
            help='Week start date in YYYY-MM-DD format (defaults to last Monday)',
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send the report via email after generation',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if report already exists',
        )

    def handle(self, *args, **options):
        report_generator = ReportGenerator()

        if options['week_start']:
            try:
                week_start = timezone.datetime.strptime(options['week_start'], '%Y-%m-%d').date()
                # Ensure it's a Monday
                if week_start.weekday() != 0:
                    self.stdout.write(
                        self.style.WARNING(f"Adjusting week start to Monday: {week_start}")
                    )
                    week_start = week_start - timedelta(days=week_start.weekday())
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            # Default to last Monday
            today = timezone.now().date()
            days_since_monday = (today.weekday() + 7) % 7
            week_start = today - timedelta(days=days_since_monday + 7)

        week_end = week_start + timedelta(days=6)
        send_email = options['send_email']
        force = options['force']

        self.stdout.write(f"📊 Generating weekly report for {week_start} to {week_end}")

        try:
            # Check if report already exists
            existing_report = report_generator.get_existing_report(week_start, week_end)
            if existing_report and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ Report already exists for this week (ID: {existing_report.id}). "
                        "Use --force to regenerate."
                    )
                )
                report = existing_report
            else:
                # Generate new report
                report = report_generator.generate_weekly_report(week_start, week_end)
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Generated report (ID: {report.id})")
                )

            # Display report summary
            self.stdout.write("\n" + "="*60)
            self.stdout.write(f"📈 WEEKLY REPORT SUMMARY")
            self.stdout.write("="*60)
            self.stdout.write(f"Week: {report.week_start} to {report.week_end}")
            self.stdout.write(f"Connection Rate: {report.initial_connection_rate}% → {report.final_connection_rate}%")
            self.stdout.write(f"New Connections: {report.new_connections}")
            self.stdout.write(f"Disconnections: {report.disconnections}")
            self.stdout.write(f"Invitations Sent: {report.invitations_sent}")
            self.stdout.write(f"Campaigns Sent: {report.campaigns_sent}")
            self.stdout.write(f"Growth Rate: {report.calculate_growth_rate()}%")

            if report.key_insights:
                self.stdout.write(f"\n🔍 Key Insights:")
                self.stdout.write(report.key_insights)

            if report.recommendations:
                self.stdout.write(f"\n💡 Recommendations:")
                self.stdout.write(report.recommendations)

            # Send email if requested
            if send_email:
                try:
                    email_sent = report_generator.send_weekly_report(report)
                    if email_sent:
                        self.stdout.write(
                            self.style.SUCCESS(f"📧 Report emailed successfully!")
                        )
                        report.sent = True
                        report.sent_at = timezone.now()
                        report.save()
                    else:
                        self.stdout.write(
                            self.style.WARNING("⚠️ Report generated but email sending failed")
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error sending email: {e}")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error generating report: {e}")
            )

        self.stdout.write(f"\nCompleted at {timezone.now()}")