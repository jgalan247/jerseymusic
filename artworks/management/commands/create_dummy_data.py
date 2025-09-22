from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker
import random
from PIL import Image
import io
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Creates dummy artists, customers, and artworks for testing'

    def add_arguments(self, parser):
        parser.add_argument('--customers', type=int, default=5, help='Number of customers to create')
        parser.add_argument('--artists', type=int, default=5, help='Number of artists to create')
        parser.add_argument('--artworks', type=int, default=3, help='Artworks per artist')

    def handle(self, *args, **kwargs):
        num_customers = kwargs['customers']
        num_artists = kwargs['artists']
        num_artworks = kwargs['artworks']
        
        # Generate unique batch ID for this run
        batch_id = uuid.uuid4().hex[:6]
        
        self.stdout.write(f'Creating dummy data (batch {batch_id})...')
        
        # Create customers with unique usernames
        customers = []
        for i in range(num_customers):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f'{first_name.lower()}{last_name.lower()}{batch_id}'[:30]
            email = f'{first_name.lower()}.{last_name.lower()}.{batch_id}@test.com'
            
            # Ensure uniqueness
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{username}{counter}'[:30]
                counter += 1
            
            customer = User.objects.create_user(
                username=username,
                email=email,
                password='TestPass123!',
                first_name=first_name,
                last_name=last_name,
                user_type='customer',
                email_verified=True
            )
            customers.append(customer)
            self.stdout.write(f'Created customer: {customer.email} (password: TestPass123!)')
        
        # Create artists
        artists = []
        from accounts.models import ArtistProfile
        for i in range(num_artists):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f'artist_{first_name.lower()}{batch_id}'[:30]
            email = f'artist.{first_name.lower()}.{batch_id}@test.com'
            
            # Ensure uniqueness
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{username}{counter}'[:30]
                counter += 1
            
            artist = User.objects.create_user(
                username=username,
                email=email,
                password='TestPass123!',
                first_name=first_name,
                last_name=last_name,
                user_type='artist',
                email_verified=True
            )
            
            ArtistProfile.objects.create(
                user=artist,
                display_name=f'{first_name} {last_name} Art',
                bio=fake.text(max_nb_chars=200),
                commission_rate=Decimal('10.00')
            )
            
            artists.append(artist)
            self.stdout.write(f'Created artist: {artist.email} (password: TestPass123!)')
        
        # Create artworks
        from artworks.models import Artwork, Category
        
        categories = ['Paintings', 'Photography', 'Sculptures', 'Digital Art', 'Prints']
        for cat_name in categories:
            Category.objects.get_or_create(
                name=cat_name,
                slug=cat_name.lower().replace(' ', '-')
            )
        
        artwork_titles = [
            'Sunset Over St Ouens', 'Elizabeth Castle Morning', 'Corbiere Lighthouse',
            'Jersey Cow Portrait', 'St Brelade Bay', 'Gorey Harbour', 'Jersey Lily',
            'Mont Orgueil Castle', 'La Rocque Harbour', 'Devils Hole Path'
        ]
        
        for j in range(num_artworks):
            img = Image.new('RGB', (800, 600), color=random.choice(['blue', 'red', 'green', 'yellow']))
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG')
            img_io.seek(0)
            img_file = SimpleUploadedFile(f'artwork_{uuid.uuid4().hex[:8]}.jpg', img_io.getvalue())
            
            # Make title unique by adding UUID
            unique_id = uuid.uuid4().hex[:6]
            title = f'{random.choice(artwork_titles)} {unique_id}'
            
            artwork = Artwork.objects.create(
                artist=artist,
                title=title,
                slug=f'{title.lower().replace(" ", "-")}-{unique_id}',  # Explicitly set unique slug
                description=fake.text(max_nb_chars=300),
                category=Category.objects.order_by('?').first(),
                price=Decimal(str(round(random.uniform(50, 500), 2))),
                artwork_type=random.choice(['original', 'print']),
                stock_quantity=random.randint(1, 10),
                status='active',
                is_available=True,
                main_image=img_file,
                height=random.randint(20, 200),
                width=random.randint(20, 200),
                year_created=random.randint(2020, 2024),
                is_local_artist=True
            )
            self.stdout.write(f'  - Created artwork: {artwork.title}')
        
        self.stdout.write(self.style.SUCCESS(f"""
✅ Dummy data created successfully! (Batch: {batch_id})

Created:
- {num_customers} customers
- {num_artists} artists
- {num_artists * num_artworks} artworks

All users have password: TestPass123!

To create more data, run the command again - it will create new unique users.
        """))