from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, time
from decimal import Decimal
import random

from accounts.models import User
from events.models import Event, Category


class Command(BaseCommand):
    help = "Create demo data for Jersey Events (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing demo Events before seeding.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible data (default: 42).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(opts["seed"])
        self.stdout.write(self.style.WARNING("Seeding demo data..."))

        if opts["fresh"]:
            deleted = Event.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted existing events: {deleted}"))

        # --- Categories ---
        categories = [
            ("Music", "music"),
            ("Theatre", "theatre"),
            ("Sports", "sports"),
            ("Food & Drink", "food"),
            ("Arts", "arts"),
            ("Workshops", "workshops"),
            ("Comedy", "comedy"),
            ("Family", "family"),
        ]

        created_categories = []
        for name, slug in categories:
            cat, created = Category.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            # If the category existed with a different name, keep slug the source of truth
            if not created and cat.name != name:
                cat.name = name
                cat.save(update_fields=["name"])
            created_categories.append(cat)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Category: {name}"))

        # --- Customers (5) ---
        for i in range(5):
            username = f"customer{i+1}"
            email = f"{username}@test.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "user_type": "customer",
                    "first_name": f"Customer{i+1}",
                    "last_name": "Test",
                },
            )
            if created:
                user.set_password("TestPass123")
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"User created: {username}"))

        # --- Organisers (3) ---
        organisers = []
        for i in range(3):
            username = f"organiser{i+1}"
            email = f"{username}@test.com"
            # If your app uses 'artist' to mean organiser, keep it; otherwise change to your choice
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "user_type": "artist",
                    "first_name": f"Organiser{i+1}",
                    "last_name": "Events",
                },
            )
            if created:
                user.set_password("TestPass123")
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"User created: {username}"))
            organisers.append(user)

        event_titles = [
            "Jersey Jazz Festival",
            "Comedy Night at the Opera House",
            "Food & Wine Festival",
            "Marathon Jersey",
            "Art Exhibition: Island Views",
            "Kids Theatre Workshop",
            "Rock Concert: Island Sounds",
            "Cooking Masterclass",
            "Business Networking Evening",
            "Yoga in the Park",
            "Photography Workshop",
            "Wine Tasting Experience",
            "Live Music at the Pub",
            "Family Fun Day",
            "Stand-up Comedy Show",
        ]

        venues = [
            "Opera House Jersey",
            "Fort Regent",
            "Royal Square",
            "St Helier Town Hall",
            "Jersey Arts Centre",
            "Liberation Square",
            "Radisson Blu Waterfront",
            "The Pomme d'Or Hotel",
            "St Brelade's Bay Hotel",
            "Durrell Wildlife Park",
        ]

        descriptions = [
            "Join us for an amazing event celebrating the best of Jersey!",
            "Don't miss this exciting opportunity to connect with the community.",
            "Experience the vibrant culture and entertainment of our beautiful island.",
            "A wonderful evening of entertainment for all ages.",
            "Discover local talent and enjoy a memorable experience.",
        ]

        # --- Events: 3–5 per organiser ---
        # Adjust these based on your model fields (see notes below)
        total_created = 0
        for organiser in organisers:
            for _ in range(random.randint(3, 5)):
                base_title = random.choice(event_titles)

                # Ensure unique title if your model requires uniqueness
                title = base_title
                counter = 2
                while Event.objects.filter(title=title).exists():
                    title = f"{base_title} {counter}"
                    counter += 1

                event_date = timezone.now().date() + timedelta(
                    days=random.randint(7, 90)
                )

                # Choose a random category
                category = random.choice(created_categories)

                # If your Event has DecimalField for price, use Decimal; otherwise use int
                ticket_price = Decimal(random.randrange(10, 76))  # £10–£75

                # If your Event has TimeField, pass a `time` object; for CharField you can use "19:00"
                event_time = time(19, 0)

                event, created = Event.objects.update_or_create(
                    # Choose a stable lookup. If titles aren't unique, you might key on (title, organiser)
                    title=title,
                    defaults={
                        "organiser": organiser,
                        "venue_name": random.choice(venues),
                        "venue_address": "St Helier, Jersey JE1 1AA",
                        "event_date": event_date,
                        "event_time": event_time,
                        "capacity": random.randint(50, 300),
                        "ticket_price": ticket_price,
                        "status": "published",
                        "category": category,
                        "description": random.choice(descriptions),
                    },
                )
                if created:
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f"Event: {title}"))

        self.stdout.write(
            self.style.SUCCESS(f"Demo data seeding complete. Events created: {total_created}")
        )
        self.stdout.write("Login creds:")
        self.stdout.write("- Customers: customer1@test.com … customer5@test.com / password: TestPass123")
        self.stdout.write("- Organisers: organiser1@test.com … organiser3@test.com / password: TestPass123")
