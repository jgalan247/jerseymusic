# conftest.py - Place in project root

import pytest
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Set Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'artworks.settings_test')

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


# ===================================
# Shared Fixtures for All Tests
# ===================================

@pytest.fixture
def customer_user(db):
    """Create a test customer user."""
    user = User.objects.create_user(
        username='testcustomer',
        email='customer@test.com',
        password='TestPass123!',
        user_type='customer',
        first_name='John',
        last_name='Doe',
        email_verified=True
    )
    
    from accounts.models import CustomerProfile
    CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            'address_line_1': '123 Test Street',
            'parish': 'st_helier',
            'postcode': 'JE2 3AB'
        }
    )
    return user


@pytest.fixture
def artist_user(db):
    """Create a test artist user."""
    user = User.objects.create_user(
        username='testartist',
        email='artist@test.com',
        password='TestPass123!',
        user_type='artist',
        first_name='Jane',
        last_name='Artist',
        email_verified=True
    )
    
    from accounts.models import ArtistProfile
    ArtistProfile.objects.get_or_create(
        user=user,
        defaults={
            'display_name': 'Jane Artist Studio',
            'bio': 'Professional artist',
            'commission_rate': Decimal('10.00')
        }
    )
    return user


@pytest.fixture
def sample_artwork(db, artist_user):
    """Create a sample artwork."""
    from artworks.models import Artwork, Category
    
    category, _ = Category.objects.get_or_create(
        name='Paintings',
        slug='paintings'
    )
    
    return Artwork.objects.create(
        artist=artist_user,
        title='Test Artwork',
        description='A beautiful test piece',
        category=category,
        price=Decimal('250.00'),
        stock_quantity=5,
        status='active',
        is_available=True
    )


@pytest.fixture
def sample_order(db, customer_user, artist_user, sample_artwork):
    """Create a sample order."""
    from orders.models import Order, OrderItem
    
    order = Order.objects.create(
        user=customer_user,
        order_number='JA-TEST001',
        email=customer_user.email,
        first_name=customer_user.first_name,
        last_name=customer_user.last_name,
        phone='+44 7797 123456',
        delivery_first_name=customer_user.first_name,
        delivery_last_name=customer_user.last_name,
        delivery_address_line_1='123 Test Street',
        delivery_parish='st_helier',
        delivery_postcode='JE2 3AB',
        subtotal=Decimal('250.00'),
        shipping_cost=Decimal('0.00'),
        total=Decimal('250.00'),
        status='processing'
    )
    
    OrderItem.objects.create(
        order=order,
        artwork=sample_artwork,
        artwork_title=sample_artwork.title,
        artwork_artist=str(artist_user),
        quantity=1,
        price=sample_artwork.price
    )
    
    return order


@pytest.fixture
def authenticated_client(client, customer_user):
    """Return a client logged in as customer."""
    client.login(username='testcustomer', password='TestPass123!')
    return client


@pytest.fixture
def artist_client(client, artist_user):
    """Return a client logged in as artist."""
    client.login(username='testartist', password='TestPass123!')
    return client


# ===================================
# E2E Test Fixtures (if using Selenium)
# ===================================

@pytest.fixture(scope="session")
def chrome_driver_init():
    """Initialize Chrome driver for E2E tests."""
    from selenium import webdriver
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # For GitHub Actions or CI environments
    if os.environ.get('CI'):
        chrome_options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()


@pytest.fixture
def live_server_url(live_server):
    """Provide the live server URL for E2E tests."""
    return live_server.url


# ===================================
# Database Fixtures
# ===================================

@pytest.fixture
def create_categories(db):
    """Create standard artwork categories."""
    from artworks.models import Category
    
    categories = [
        ('paintings', 'Paintings'),
        ('photography', 'Photography'),
        ('sculptures', 'Sculptures'),
        ('prints', 'Prints'),
        ('digital', 'Digital Art'),
    ]
    
    created = []
    for slug, name in categories:
        cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
        created.append(cat)
    
    return created


@pytest.fixture
def jersey_parishes():
    """Return list of Jersey parishes for testing."""
    return [
        'st_helier', 'st_brelade', 'st_clement', 'st_john',
        'st_lawrence', 'st_martin', 'st_mary', 'st_ouen',
        'st_peter', 'st_saviour', 'grouville', 'trinity'
    ]


@pytest.fixture
def valid_jersey_postcodes():
    """Return list of valid Jersey postcode examples."""
    return [
        'JE1 1AA', 'JE2 3AB', 'JE3 9ZZ', 
        'JE4 5XY', 'JE5 0AA', 'JE2 4WX'
    ]


# ===================================
# Mock Payment Gateway
# ===================================

@pytest.fixture
def mock_payment_gateway(mocker):
    """Mock payment gateway for testing."""
    mock = mocker.patch('payments.views.process_payment')
    mock.return_value = {
        'status': 'success',
        'transaction_id': 'TEST_TXN_123',
        'amount': Decimal('100.00')
    }
    return mock


# ===================================
# Email Testing
# ===================================

@pytest.fixture
def mailhog_client():
    """Client for interacting with MailHog if available."""
    import requests
    
    class MailHogClient:
        def __init__(self):
            self.base_url = 'http://localhost:8025/api/v2'
            
        def get_messages(self):
            try:
                response = requests.get(f'{self.base_url}/messages')
                return response.json()
            except:
                return None
                
        def delete_all(self):
            try:
                requests.delete(f'{self.base_url}/messages')
            except:
                pass
                
    return MailHogClient()