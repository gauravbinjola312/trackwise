"""
WSGI config for TrackWise backend.
Used by Gunicorn in production:
    gunicorn trackwise_backend.wsgi:application --workers 4 --bind 0.0.0.0:8000
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackwise_backend.settings.production')
application = get_wsgi_application()
