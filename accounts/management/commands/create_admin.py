"""
Management command to create a superuser for production deployment.
Uses environment variables for credentials.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser using environment variables'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@coderra.je')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write(
                self.style.ERROR('DJANGO_SUPERUSER_PASSWORD environment variable is required')
            )
            return

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'User {email} already exists. Skipping creation.')
            )
            return

        # Create superuser
        user = User.objects.create_superuser(
            email=email,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created superuser: {email}')
        )
