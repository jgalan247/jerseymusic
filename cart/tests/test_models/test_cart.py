from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from cart.models import Cart, CartItem
from artworks.models import Artwork

User = get_user_model()


class CartModelTest(TestCase):
    
    def test_cart_creation(self):
        """Test creating a cart"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        cart = Cart.objects.create(user=user)
        self.assertEqual(cart.user, user)
        self.assertTrue(cart.is_active)
