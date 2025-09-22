from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class DebugLoginTest(TestCase):
    def test_debug_login(self):
        user = User.objects.create_user(
            username='test',
            email='test@test.com',
            password='test123',
            email_verified=True,
            user_type='customer'
        )
        
        # Try different field combinations
        response = self.client.post('/accounts/login/', {
            'email': 'test@test.com',
            'password': 'test123'
        })
        print(f"Email/password: {response.status_code}")
        print(f"Content: {response.content[:200]}")
        
        response = self.client.post('/accounts/login/', {
            'username': 'test@test.com',
            'password': 'test123'
        })
        print(f"Username/password: {response.status_code}")