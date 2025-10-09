"""Management command to notify artists about SumUp OAuth migration."""

from django.core.management.base import BaseCommand
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings
from accounts.models import ArtistProfile


class Command(BaseCommand):
    help = 'Send notification emails to artists about SumUp OAuth migration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--approved-only',
            action='store_true',
            help='Only send to approved artists',
        )

    def handle(self, *args, **options):
        """Send migration notification emails to artists."""
        # Get artists to notify
        artists = ArtistProfile.objects.all()

        if options['approved_only']:
            artists = artists.filter(is_approved=True)

        if not artists.exists():
            self.stdout.write(
                self.style.WARNING('No artists found to notify.')
            )
            return

        self.stdout.write(
            f'Found {artists.count()} artists to notify about SumUp migration...'
        )

        # Prepare email data
        emails = []
        for artist in artists:
            subject = 'Action Required: Reconnect Your SumUp Payment Account'

            # Render email content
            html_message = f"""
            <html>
            <body>
                <h2>Hi {artist.display_name},</h2>

                <p>We've upgraded our payment system to provide better service and direct payments to your SumUp account!</p>

                <h3>What's Changed:</h3>
                <ul>
                    <li><strong>Direct Payments:</strong> Customers pay directly into your SumUp merchant account</li>
                    <li><strong>Faster Payouts:</strong> No more waiting for platform payouts</li>
                    <li><strong>Better Security:</strong> OAuth integration for secure, token-based connections</li>
                    <li><strong>Transparent Fees:</strong> Clear visibility of platform commission</li>
                </ul>

                <h3>Action Required:</h3>
                <p>To continue receiving payments, you need to reconnect your SumUp account:</p>

                <p>
                    <a href="{settings.SITE_URL}/accounts/dashboard/"
                       style="background-color: #28a745; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reconnect SumUp Account
                    </a>
                </p>

                <h3>How to Reconnect:</h3>
                <ol>
                    <li>Log in to your artist dashboard</li>
                    <li>Click "Connect SumUp" in the Payment Connection section</li>
                    <li>Authorize Jersey Events to connect to your SumUp account</li>
                    <li>You're ready to receive direct payments!</li>
                </ol>

                <p><strong>Important:</strong> Until you reconnect, customers won't be able to purchase tickets for your events.</p>

                <p>If you need help or have questions, please reply to this email.</p>

                <p>Thank you,<br>
                The Jersey Events Team</p>

                <hr>
                <small>This is a one-time migration notice. You won't receive this email again once you've reconnected your account.</small>
            </body>
            </html>
            """

            plain_message = f"""
            Hi {artist.display_name},

            We've upgraded our payment system to provide better service and direct payments to your SumUp account!

            WHAT'S CHANGED:
            - Direct Payments: Customers pay directly into your SumUp merchant account
            - Faster Payouts: No more waiting for platform payouts
            - Better Security: OAuth integration for secure, token-based connections
            - Transparent Fees: Clear visibility of platform commission

            ACTION REQUIRED:
            To continue receiving payments, you need to reconnect your SumUp account:

            1. Log in to your artist dashboard: {settings.SITE_URL}/accounts/dashboard/
            2. Click "Connect SumUp" in the Payment Connection section
            3. Authorize Jersey Events to connect to your SumUp account
            4. You're ready to receive direct payments!

            IMPORTANT: Until you reconnect, customers won't be able to purchase tickets for your events.

            If you need help or have questions, please reply to this email.

            Thank you,
            The Jersey Events Team

            ---
            This is a one-time migration notice. You won't receive this email again once you've reconnected.
            """

            emails.append((
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [artist.user.email]
            ))

        # Send or preview emails
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would send {len(emails)} notification emails')
            )
            self.stdout.write('\nSample email content:')
            self.stdout.write('=' * 50)
            self.stdout.write(f'To: {emails[0][3][0]}')
            self.stdout.write(f'Subject: {emails[0][0]}')
            self.stdout.write('\nContent:')
            self.stdout.write(emails[0][1][:500] + '...')
        else:
            # Send emails in batches
            try:
                send_mass_mail(emails, fail_silently=False)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully sent {len(emails)} notification emails')
                )

                # Update artist records to track notification
                artists.update(sumup_connection_status='not_connected')  # Ensure status is correct

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to send emails: {e}')
                )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('NEXT STEPS:')
        self.stdout.write('=' * 60)
        self.stdout.write('1. Monitor artist dashboard for reconnections')
        self.stdout.write('2. Follow up with artists who haven\'t reconnected after 1 week')
        self.stdout.write('3. Check /admin/ for connection status updates')
        self.stdout.write('=' * 60)