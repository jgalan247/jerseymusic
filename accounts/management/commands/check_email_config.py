"""
Management command to check email configuration and test email sending.
Usage: python manage.py check_email_config [test_email@example.com]
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Check email configuration and optionally send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'test_email',
            nargs='?',
            type=str,
            help='Email address to send test email to (optional)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('EMAIL CONFIGURATION DIAGNOSTICS'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))

        # Check DEBUG mode
        self.stdout.write(f"DEBUG mode: {self.style.WARNING(str(settings.DEBUG))}")

        # Check email backend
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f"Email backend: {self.style.WARNING(backend)}")

        if 'console' in backend.lower():
            self.stdout.write(self.style.ERROR(
                "\n⚠️  WARNING: Console backend is active!"
            ))
            self.stdout.write(self.style.ERROR(
                "   Emails will only print to the console, not actually send.\n"
            ))

        # Check EMAIL_PROVIDER environment variable
        email_provider = os.getenv('EMAIL_PROVIDER', 'NOT SET')
        self.stdout.write(f"EMAIL_PROVIDER env var: {self.style.WARNING(email_provider)}")

        if email_provider == 'NOT SET' or email_provider == 'console':
            self.stdout.write(self.style.ERROR(
                "\n❌ ISSUE FOUND: EMAIL_PROVIDER is not set or set to 'console'"
            ))
            self.stdout.write(self.style.ERROR(
                "   Solution: Set EMAIL_PROVIDER to 'gmail', 'sendgrid', or 'mailgun'"
            ))
            self.stdout.write(self.style.ERROR(
                "   on Railway.app environment variables.\n"
            ))

        # Check SMTP settings
        self.stdout.write("\nSMTP Configuration:")
        self.stdout.write(f"  EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
        self.stdout.write(f"  EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
        self.stdout.write(f"  EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")

        # Check credentials (without revealing them)
        email_user = os.getenv('EMAIL_HOST_USER', '')
        email_pass = os.getenv('EMAIL_HOST_PASSWORD', '')

        if email_user:
            self.stdout.write(f"  EMAIL_HOST_USER: {self.style.SUCCESS('✓ SET')} ({email_user[:3]}...)")
        else:
            self.stdout.write(f"  EMAIL_HOST_USER: {self.style.ERROR('✗ NOT SET')}")

        if email_pass:
            self.stdout.write(f"  EMAIL_HOST_PASSWORD: {self.style.SUCCESS('✓ SET')} (hidden)")
        else:
            self.stdout.write(f"  EMAIL_HOST_PASSWORD: {self.style.ERROR('✗ NOT SET')}")

        # Check DEFAULT_FROM_EMAIL
        from_email = settings.DEFAULT_FROM_EMAIL
        self.stdout.write(f"\nDEFAULT_FROM_EMAIL: {self.style.WARNING(from_email)}")

        # Send test email if requested
        test_email = options.get('test_email')
        if test_email:
            self.stdout.write(f"\n{'-'*70}")
            self.stdout.write(f"Attempting to send test email to: {test_email}")
            self.stdout.write(f"{'-'*70}\n")

            try:
                email = EmailMultiAlternatives(
                    subject='Test Email from Jersey Events',
                    body='This is a test email to verify email configuration is working correctly.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[test_email]
                )
                email.attach_alternative(
                    '<h1>Test Email</h1><p>This is a test email to verify email configuration is working correctly.</p>',
                    "text/html"
                )

                email.send(fail_silently=False)

                self.stdout.write(self.style.SUCCESS(
                    f"\n✅ Test email sent successfully to {test_email}!"
                ))

                if 'console' in backend.lower():
                    self.stdout.write(self.style.WARNING(
                        "   (Note: Console backend is active - check terminal output above)"
                    ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"\n❌ Failed to send test email: {str(e)}"
                ))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        # Summary and recommendations
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.WARNING('RECOMMENDATIONS'))
        self.stdout.write(f"{'='*70}\n")

        if not settings.DEBUG and (email_provider == 'NOT SET' or email_provider == 'console'):
            self.stdout.write(self.style.ERROR(
                "⚠️  CRITICAL: Production environment without working email!"
            ))
            self.stdout.write("\nTo fix this on Railway.app, add these environment variables:")
            self.stdout.write(self.style.SUCCESS(
                "\n  EMAIL_PROVIDER=gmail"
                "\n  EMAIL_HOST_USER=your-email@coderra.je"
                "\n  EMAIL_HOST_PASSWORD=your-app-specific-password"
            ))
            self.stdout.write("\nFor Gmail:")
            self.stdout.write("  1. Use a Google Workspace account (your-email@coderra.je)")
            self.stdout.write("  2. Enable 2-factor authentication")
            self.stdout.write("  3. Generate an App-Specific Password")
            self.stdout.write("  4. Use that app password for EMAIL_HOST_PASSWORD")
        elif settings.DEBUG:
            self.stdout.write(self.style.SUCCESS(
                "✓ Development mode - console/MailHog backend is appropriate"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "✓ Email provider is configured"
            ))
            self.stdout.write("\nTo test email sending, run:")
            self.stdout.write(f"  python manage.py check_email_config your-email@example.com")

        self.stdout.write('\n')
