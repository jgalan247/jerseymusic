# Create debug_login.py to see what's happening:
from django.test import TestCase, Client
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()

class DebugLoginTest(TestCase):
    def test_debug_artist_login(self):
        # Create artist
        artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='testpass123',
            user_type='artist',
            email_verified=True
        )
        
        print(f"Created user - username: {artist.username}, email: {artist.email}")
        print(f"Email verified: {artist.email_verified}")
        print(f"User type: {artist.user_type}")
        
        # Test authentication directly
        auth_user = authenticate(username='artist@test.com', password='testpass123')
        print(f"Direct auth result: {auth_user}")
        
        # Try login via view
        response = self.client.post('/accounts/login/', {
            'email': 'artist@test.com',
            'password': 'testpass123'
        })
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            print("Login failed - stayed on page")
            # Check for error messages
            if hasattr(response, 'context') and response.context:
                messages = response.context.get('messages', [])
                for msg in messages:
                    print(f"Message: {msg}")