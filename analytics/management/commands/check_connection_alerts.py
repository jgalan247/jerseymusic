from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.services import AlertManager


class Command(BaseCommand):
    help = 'Check connection rates and trigger alerts if necessary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what alerts would be triggered without actually creating them',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force check even if already checked recently',
        )

    def handle(self, *args, **options):
        alert_manager = AlertManager()
        dry_run = options['dry_run']
        force_check = options['force']

        self.stdout.write("🔍 Checking connection rate alerts...")

        if dry_run:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No alerts will be created"))

        try:
            # Check for low connection rate
            low_rate_alert = alert_manager.check_low_connection_rate(dry_run=dry_run)
            if low_rate_alert:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"Would create LOW RATE alert: {low_rate_alert['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"🚨 Created LOW RATE alert: {low_rate_alert.message}")
                    )

            # Check for declining rate
            declining_alert = alert_manager.check_declining_rate(dry_run=dry_run)
            if declining_alert:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"Would create DECLINING RATE alert: {declining_alert['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"⚠️ Created DECLINING RATE alert: {declining_alert.message}")
                    )

            # Check for stagnant rate
            stagnant_alert = alert_manager.check_stagnant_rate(dry_run=dry_run)
            if stagnant_alert:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"Would create STAGNANT RATE alert: {stagnant_alert['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"⏸️ Created STAGNANT RATE alert: {stagnant_alert.message}")
                    )

            # Check milestones
            milestone_alert = alert_manager.check_milestones(dry_run=dry_run)
            if milestone_alert:
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f"Would create MILESTONE alert: {milestone_alert['message']}")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"🎉 Created MILESTONE alert: {milestone_alert.message}")
                    )

            if not any([low_rate_alert, declining_alert, stagnant_alert, milestone_alert]):
                self.stdout.write(self.style.SUCCESS("✅ No alerts triggered - connection rates look good!"))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error checking alerts: {e}")
            )

        self.stdout.write(f"Completed at {timezone.now()}")