"""
ASGI config for Jersey Artwork project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'artworks.settings')
application = get_asgi_application()
