"""
TrackWise Backend — Base Settings
Shared across development, staging, and production.
"""
import os
from datetime import timedelta
from pathlib import Path

# ── BASE DIR ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── SECURITY ──────────────────────────────────────────────────
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-in-production')
DEBUG      = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')

# ── APPLICATIONS ──────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
]

LOCAL_APPS = [
    'trackwise_backend.apps.accounts',
    'trackwise_backend.apps.expenses',
    'trackwise_backend.apps.learning',
    'trackwise_backend.apps.goals',
    'trackwise_backend.apps.savings',
    'trackwise_backend.apps.subscriptions',
    'trackwise_backend.apps.dashboard',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── MIDDLEWARE ────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # Must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'trackwise_backend.utils.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'trackwise_backend.urls'
WSGI_APPLICATION = 'trackwise_backend.wsgi.application'
AUTH_USER_MODEL = 'accounts.User'

# ── TEMPLATES ─────────────────────────────────────────────────
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS':    [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# ── DATABASE ──────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME', 'trackwise_db'),
        'USER':     os.environ.get('DB_USER', 'trackwise'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST':     os.environ.get('DB_HOST', 'localhost'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,   # Connection pooling
        'OPTIONS':  { 'connect_timeout': 10 },
    }
}

# ── CACHE ─────────────────────────────────────────────────────
# Uses Redis if REDIS_URL is set, otherwise falls back to local memory
_REDIS_URL = os.environ.get('REDIS_URL', '')
if _REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND':  'django_redis.cache.RedisCache',
            'LOCATION': _REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'trackwise-cache',
        }
    }

# ── PASSWORD VALIDATION ───────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': { 'min_length': 8 } },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' },
]

# ── INTERNATIONALISATION ──────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── STATIC & MEDIA ────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# ── REST FRAMEWORK ────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'trackwise_backend.utils.pagination.StandardPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '2000/hour',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'trackwise_backend.utils.exceptions.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'DATE_FORMAT':     '%Y-%m-%d',
}

# ── JWT CONFIGURATION ─────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':         timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME':        timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 30))),
    'ROTATE_REFRESH_TOKENS':         True,
    'BLACKLIST_AFTER_ROTATION':      True,
    'UPDATE_LAST_LOGIN':             True,
    'ALGORITHM':                     'HS256',
    'SIGNING_KEY':                   SECRET_KEY,
    'AUTH_HEADER_TYPES':             ('Bearer',),
    'AUTH_HEADER_NAME':              'HTTP_AUTHORIZATION',
    'USER_ID_FIELD':                 'id',
    'USER_ID_CLAIM':                 'user_id',
    'AUTH_TOKEN_CLASSES':            ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM':              'token_type',
    'JTI_CLAIM':                     'jti',
}

# ── CORS ──────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:19006,exp://localhost:19000'
).split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]

# ── EMAIL ─────────────────────────────────────────────────────
EMAIL_BACKEND    = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST       = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT       = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS    = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER  = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'TrackWise <noreply@trackwise.in>')

# ── CELERY ────────────────────────────────────────────────────
CELERY_BROKER_URL         = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND     = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TIMEZONE           = 'Asia/Kolkata'
CELERY_ENABLE_UTC         = True

# ── RAZORPAY ──────────────────────────────────────────────────
RAZORPAY_KEY_ID          = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET      = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET  = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
RAZORPAY_PLAN_ID_MONTHLY = os.environ.get('RAZORPAY_PLAN_ID_MONTHLY', '')
RAZORPAY_PLAN_ID_YEARLY  = os.environ.get('RAZORPAY_PLAN_ID_YEARLY', '')

# ── APP CONFIG ────────────────────────────────────────────────
FRONTEND_URL           = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
TRIAL_PERIOD_DAYS      = 7
MAX_USERS              = 500            # Enforced at signup
RATE_LIMIT_PER_USER    = 2000          # API calls per hour

# ── LOGGING ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': { 'format': '[{asctime}] {levelname} {name} {message}', 'style': '{' },
        'simple':  { 'format': '{levelname} {message}', 'style': '{' },
    },
    'handlers': {
        'console': { 'class': 'logging.StreamHandler', 'formatter': 'verbose' },
        'file':    { 'class': 'logging.handlers.RotatingFileHandler', 'filename': BASE_DIR / 'logs/trackwise.log', 'maxBytes': 10485760, 'backupCount': 5, 'formatter': 'verbose' },
    },
    'loggers': {
        'django':           { 'handlers': ['console'], 'level': 'INFO' },
        'trackwise_backend':{ 'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False },
    },
}
