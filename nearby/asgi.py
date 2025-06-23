# nearby/asgi.py
import os
import django

# Set Django settings module and initialize Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nearby.settings')
django.setup()

# Now import other modules
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application without WebSocket support
application = get_asgi_application()
