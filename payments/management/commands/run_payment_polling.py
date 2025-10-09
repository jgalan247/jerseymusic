"""
Management command to run payment polling service.

This command is used by Django-Q to poll SumUp API and verify pending payments.
It can also be run manually for testing.

Usage:
    python manage.py run_payment_polling
    python manage.py run_payment_polling --verbose
"""

from django.core.management.base import BaseCommand
from payments.polling_service import polling_service
import logging

logger = logging.getLogger('payments.polling_service')


class Command(BaseCommand):
    help = 'Run payment polling service to verify pending payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)

        if verbose:
            self.stdout.write(self.style.SUCCESS('Starting payment polling service...'))

        try:
            # Run the polling service
            stats = polling_service.process_pending_payments()

            # Output results
            if verbose:
                self.stdout.write(self.style.SUCCESS('\nPolling cycle complete!'))
                self.stdout.write(f"  Verified: {stats.get('verified', 0)}")
                self.stdout.write(f"  Failed: {stats.get('failed', 0)}")
                self.stdout.write(f"  Still Pending: {stats.get('still_pending', 0)}")
                self.stdout.write(f"  Errors: {stats.get('errors', 0)}")

            # Return success message
            if stats.get('message'):
                self.stdout.write(self.style.WARNING(stats['message']))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Processed {sum(stats.values())} orders"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Payment polling failed: {str(e)}')
            )
            logger.error(f"Management command error: {e}", exc_info=True)
            raise
