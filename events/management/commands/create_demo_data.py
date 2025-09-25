from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import User
from events.models import Event, Category
import random

class Command(BaseCommand):
    help = 'Create demo data for Jersey Events'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        # Create categories
        categories = [
            ('Music', 'music'),
            ('Theatre', 'theatre'),
            ('Sports', 'sports'),
            ('Food & Drink', 'food'),
            ('Arts', 'arts'),
            ('Workshops', 'workshops'),
            ('Comedy', 'comedy'),
            ('Family', 'family')
        ]

        created_categories = []
        for cat_name, cat_slug in categories:
            category, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': cat_slug}
            )
            created_categories.append(category)
            if created:
                self.stdout.write(f'Created category: {cat_name}')

        # Create customers
        for i in range(5):
            username = f'customer{i+1}'
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=f'customer{i+1}@test.com',
                    password='TestPass123',
                    user_type='customer',
                    first_name=f'Customer{i+1}',
                    last_name='Test'
                )
                self.stdout.write(f'Created customer: {username}')

        # Create organisers and events
        event_titles = [
            'Jersey Jazz Festival',
            'Comedy Night at the Opera House',
            'Food & Wine Festival',
            'Marathon Jersey',
            'Art Exhibition: Island Views',
            'Kids Theatre Workshop',
            'Rock Concert: Island Sounds',
            'Cooking Masterclass',
            'Business Networking Evening',
            'Yoga in the Park',
            'Photography Workshop',
            'Wine Tasting Experience',
            'Live Music at the Pub',
            'Family Fun Day',
            'Stand-up Comedy Show'
        ]

        venues = [
            'Opera House Jersey',
            'Fort Regent',
            'Royal Square',
            'St Helier Town Hall',
            'Jersey Arts Centre',
            'Liberation Square',
            'Radisson Blu Waterfront',
            'The Pomme d\'Or Hotel',
            'St Brelade\'s Bay Hotel',
            'Durrell Wildlife Park'
        ]

        descriptions = [
            'Join us for an amazing event celebrating the best of Jersey!',
            'Don\'t miss this exciting opportunity to connect with the community.',
            'Experience the vibrant culture and entertainment of our beautiful island.',
            'A wonderful evening of entertainment for all ages.',
            'Discover local talent and enjoy a memorable experience.',
        ]

        for i in range(3):
            username = f'organiser{i+1}'
            if not User.objects.filter(username=username).exists():
                organiser = User.objects.create_user(
                    username=username,
                    email=f'organiser{i+1}@test.com',
                    password='TestPass123',
                    user_type='artist',  # Using 'artist' as that's what the system uses for organisers
                    first_name=f'Organiser{i+1}',
                    last_name='Events'
                )
                self.stdout.write(f'Created organiser: {username}')
            else:
                organiser = User.objects.get(username=username)

            # Create 3-5 events per organiser
            for j in range(random.randint(3, 5)):
                title = random.choice(event_titles)

                # Ensure unique titles by appending a number if needed
                counter = 1
                original_title = title
                while Event.objects.filter(title=title).exists():
                    title = f"{original_title} {counter}"
                    counter += 1

                event_date = timezone.now().date() + timedelta(days=random.randint(7, 90))

                event = Event.objects.create(
                    title=title,
                    organiser=organiser,
                    venue_name=random.choice(venues),
                    venue_address='St Helier, Jersey JE1 1AA',
                    event_date=event_date,
                    event_time='19:00',
                    capacity=random.randint(50, 300),
                    ticket_price=random.randint(10, 75),
                    status='published',
                    category=random.choice(created_categories),
                    description=random.choice(descriptions)
                )

                self.stdout.write(f'Created event: {title}')

        self.stdout.write(
            self.style.SUCCESS('Demo data created successfully!')
        )
        self.stdout.write('You can now log in with:')
        self.stdout.write('- Customers: customer1@test.com, customer2@test.com, etc. (password: TestPass123)')
        self.stdout.write('- Organisers: organiser1@test.com, organiser2@test.com, etc. (password: TestPass123)')