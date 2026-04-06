"""
ASGI config for TrackWise backend.
Supports WebSockets (future use) and async views.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackwise_backend.settings.production')
application = get_asgi_application()
