"""
WSGI config for Jersey Artwork project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'artworks.settings')
application = get_wsgi_application()
