from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import ArtistProfile, User
from analytics.models import SumUpConnectionEvent, DailyConnectionMetrics
import random


class Command(BaseCommand):
    help = 'Create sample analytics data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of sample data to create',
        )
        parser.add_argument(
            '--events',
            type=int,
            default=100,
            help='Number of sample events to create',
        )

    def handle(self, *args, **options):
        days = options['days']
        events_count = options['events']

        self.stdout.write(f"🔄 Creating {days} days of sample analytics data...")

        # Get or create some test artists
        test_artists = []
        for i in range(5):
            user, created = User.objects.get_or_create(
                username=f'test_artist_{i}',
                defaults={
                    'email': f'test_artist_{i}@example.com',
                    'first_name': f'Test',
                    'last_name': f'Artist {i}',
                }
            )
            artist, created = ArtistProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': f'Test Artist {i}',
                    'is_approved': True,
                    'sumup_connection_status': random.choice(['not_connected', 'connected', 'pending'])
                }
            )
            test_artists.append(artist)
            if created:
                self.stdout.write(f"Created test artist: {artist.display_name}")

        # Create sample events
        event_types = ['invited', 'email_opened', 'link_clicked', 'page_viewed',
                      'oauth_started', 'oauth_completed', 'oauth_failed']

        events_created = 0
        for i in range(events_count):
            artist = random.choice(test_artists)
            event_type = random.choice(event_types)
            created_at = timezone.now() - timedelta(
                days=random.randint(0, days),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            event = SumUpConnectionEvent.objects.create(
                artist=artist,
                event_type=event_type,
                created_at=created_at,
                metadata={'test_data': True}
            )
            events_created += 1

        self.stdout.write(f"✅ Created {events_created} sample events")

        # Create sample daily metrics
        metrics_created = 0
        for i in range(days):
            date = (timezone.now() - timedelta(days=i)).date()

            # Simulate growing connection rates
            total_artists = len(test_artists) + random.randint(0, 10)
            connected_artists = max(1, int(total_artists * (0.3 + (i * 0.01))))  # Growing over time

            metrics, created = DailyConnectionMetrics.objects.get_or_create(
                date=date,
                defaults={
                    'total_artists': total_artists,
                    'connected_artists': connected_artists,
                    'new_connections': random.randint(0, 3),
                    'disconnections': random.randint(0, 1),
                    'invitations_sent': random.randint(5, 15),
                    'page_views': random.randint(10, 30),
                    'oauth_starts': random.randint(2, 8),
                    'oauth_completions': random.randint(1, 6),
                    'oauth_failures': random.randint(0, 2),
                }
            )

            if created:
                metrics.calculate_connection_rate()
                metrics.save()
                metrics_created += 1

        self.stdout.write(f"✅ Created {metrics_created} daily metrics records")

        # Update connection statuses based on events
        connected_count = 0
        for artist in test_artists:
            if artist.connection_events.filter(event_type='oauth_completed').exists():
                artist.sumup_connection_status = 'connected'
                artist.save()
                connected_count += 1

        self.stdout.write(f"✅ Updated {connected_count} artists to connected status")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Sample data creation complete!\n"
                f"- Created {events_created} connection events\n"
                f"- Created {metrics_created} daily metrics records\n"
                f"- Updated {connected_count} artists to connected status\n\n"
                f"You can now view the analytics dashboard at: /analytics/"
            )
        )