from .base import *

from .base import *

# Override to use SQLite for quick local testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    }
}

DEBUG = True
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')

# Use SQLite for quick local dev (optional — use Postgres for real dev)
# DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
# DATABASES['default']['NAME'] = BASE_DIR / 'db.sqlite3'

# Email in console during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE     += ['debug_toolbar.middleware.DebugToolbarMiddleware']
except ImportError:
    pass
INTERNAL_IPS    = ['127.0.0.1']

# Relaxed CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Disable rate limiting in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',
    'user': '10000/hour',
}
