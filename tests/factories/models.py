"""
Factory classes for generating test data
"""
import factory
from factory.django import DjangoModelFactory
from factory import fuzzy
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, timedelta
import random

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for User model"""
    class Meta:
        model = User
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_artist = False
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password('defaultpass123')
    
    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                obj.groups.add(group)


class ArtistFactory(UserFactory):
    """Factory for Artist users"""
    username = factory.Sequence(lambda n: f'artist{n}')
    is_artist = True
    bio = factory.Faker('text', max_nb_chars=200)
    portfolio_url = factory.Faker('url')


class CustomerFactory(UserFactory):
    """Factory for Customer users"""
    username = factory.Sequence(lambda n: f'customer{n}')
    is_artist = False


class ArtworkFactory(DjangoModelFactory):
    """Factory for Artwork model"""
    class Meta:
        model = 'artworks.Artwork'
    
    artist = factory.SubFactory(ArtistFactory)
    title = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('text', max_nb_chars=500)
    price = factory.LazyFunction(
        lambda: Decimal(random.uniform(50, 1000)).quantize(Decimal('0.01'))
    )
    stock = factory.fuzzy.FuzzyInteger(1, 100)
    is_active = True
    created_at = factory.Faker('date_time_this_year')
    
    # Image will be handled separately in tests when needed
    image = factory.django.ImageField(
        width=800, 
        height=600,
        color='blue'
    )
    
    @factory.post_generation
    def categories(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for category in extracted:
                obj.categories.add(category)


class CategoryFactory(DjangoModelFactory):
    """Factory for Category model"""
    class Meta:
        model = 'artworks.Category'
        django_get_or_create = ('name',)
    
    name = factory.Faker('word')
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
    description = factory.Faker('sentence')


class OrderFactory(DjangoModelFactory):
    """Factory for Order model"""
    class Meta:
        model = 'orders.Order'
    
    customer = factory.SubFactory(CustomerFactory)
    status = 'pending'
    total_amount = Decimal('0.00')
    shipping_address = factory.Faker('street_address')
    shipping_city = factory.Faker('city')
    shipping_postal_code = factory.Faker('postcode')
    shipping_country = 'JE'
    created_at = factory.Faker('date_time_this_month')
    
    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            total = Decimal('0.00')
            for artwork, quantity in extracted:
                OrderItemFactory(
                    order=obj,
                    artwork=artwork,
                    quantity=quantity,
                    price=artwork.price
                )
                total += artwork.price * quantity
            obj.total_amount = total
            obj.save()


class OrderItemFactory(DjangoModelFactory):
    """Factory for OrderItem model"""
    class Meta:
        model = 'orders.OrderItem'
    
    order = factory.SubFactory(OrderFactory)
    artwork = factory.SubFactory(ArtworkFactory)
    quantity = factory.fuzzy.FuzzyInteger(1, 5)
    price = factory.LazyAttribute(lambda obj: obj.artwork.price)


class CartFactory(DjangoModelFactory):
    """Factory for Cart model"""
    class Meta:
        model = 'cart.Cart'
    
    user = factory.SubFactory(CustomerFactory)
    created_at = factory.Faker('date_time_this_week')


class CartItemFactory(DjangoModelFactory):
    """Factory for CartItem model"""
    class Meta:
        model = 'cart.CartItem'
    
    cart = factory.SubFactory(CartFactory)
    artwork = factory.SubFactory(ArtworkFactory)
    quantity = factory.fuzzy.FuzzyInteger(1, 3)


class RefundFactory(DjangoModelFactory):
    """Factory for Refund model"""
    class Meta:
        model = 'orders.Refund'
    
    order = factory.SubFactory(OrderFactory)
    reason = factory.Faker('text', max_nb_chars=200)
    status = 'pending'
    amount = factory.LazyAttribute(lambda obj: obj.order.total_amount)
    requested_at = factory.Faker('date_time_this_week')
    
    @factory.post_generation
    def processed_by(obj, create, extracted, **kwargs):
        if extracted:
            obj.processed_by = extracted
            obj.processed_at = datetime.now()
            obj.save()


class OrderStatusHistoryFactory(DjangoModelFactory):
    """Factory for OrderStatusHistory model"""
    class Meta:
        model = 'orders.OrderStatusHistory'
    
    order = factory.SubFactory(OrderFactory)
    status = factory.Iterator(['pending', 'confirmed', 'processing', 'shipped'])
    changed_by = factory.SubFactory(UserFactory)
    changed_at = factory.Faker('date_time_this_week')
    notes = factory.Faker('sentence')


class PaymentFactory(DjangoModelFactory):
    """Factory for Payment model"""
    class Meta:
        model = 'payments.Payment'
    
    order = factory.SubFactory(OrderFactory)
    amount = factory.LazyAttribute(lambda obj: obj.order.total_amount)
    payment_method = 'stripe'
    transaction_id = factory.Faker('uuid4')
    status = 'completed'
    created_at = factory.Faker('date_time_this_week')


class SubscriptionFactory(DjangoModelFactory):
    """Factory for Subscription model"""
    class Meta:
        model = 'subscriptions.Subscription'
    
    artist = factory.SubFactory(ArtistFactory)
    plan = factory.Iterator(['basic', 'premium', 'professional'])
    status = 'active'
    start_date = factory.Faker('date_this_month')
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=30)
    )
    auto_renew = True


# Batch creation helpers
def create_test_data():
    """Create a complete set of test data"""
    # Create users
    artists = ArtistFactory.create_batch(3)
    customers = CustomerFactory.create_batch(5)
    
    # Create categories
    categories = CategoryFactory.create_batch(5)
    
    # Create artworks
    artworks = []
    for artist in artists:
        artist_works = ArtworkFactory.create_batch(
            5, 
            artist=artist,
            categories=random.sample(categories, k=2)
        )
        artworks.extend(artist_works)
    
    # Create orders
    orders = []
    for customer in customers:
        # Create 1-3 orders per customer
        for _ in range(random.randint(1, 3)):
            order = OrderFactory(customer=customer)
            # Add 1-3 items to each order
            items = random.sample(artworks, k=random.randint(1, 3))
            for artwork in items:
                OrderItemFactory(
                    order=order,
                    artwork=artwork,
                    quantity=random.randint(1, 2)
                )
            orders.append(order)
    
    return {
        'artists': artists,
        'customers': customers,
        'categories': categories,
        'artworks': artworks,
        'orders': orders
    }