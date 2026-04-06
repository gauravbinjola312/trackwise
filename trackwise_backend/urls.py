"""
TrackWise API — URL Configuration

BASE: /api/v1/

AUTH:          /api/v1/auth/
EXPENSES:      /api/v1/expenses/
LEARNING:      /api/v1/learning/
GOALS:         /api/v1/goals/
SAVINGS:       /api/v1/savings/
SUBSCRIPTIONS: /api/v1/subscriptions/
DASHBOARD:     /api/v1/dashboard/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for load balancers / uptime monitors."""
    return JsonResponse({
        'status':  'healthy',
        'service': 'trackwise-api',
        'version': '2.0.0',
    })


API_V1 = 'api/v1/'

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health check (no auth required)
    path('health/', health_check, name='health-check'),

    # API v1
    path(API_V1 + 'auth/',          include('trackwise_backend.apps.accounts.urls',      namespace='auth')),
    path(API_V1 + 'expenses/',      include('trackwise_backend.apps.expenses.urls',      namespace='expenses')),
    path(API_V1 + 'learning/',      include('trackwise_backend.apps.learning.urls',      namespace='learning')),
    path(API_V1 + 'goals/',         include('trackwise_backend.apps.goals.urls',         namespace='goals')),
    path(API_V1 + 'savings/',       include('trackwise_backend.apps.savings.urls',       namespace='savings')),
    path(API_V1 + 'subscriptions/', include('trackwise_backend.apps.subscriptions.urls', namespace='subscriptions')),
    path(API_V1 + 'dashboard/',     include('trackwise_backend.apps.dashboard.urls',     namespace='dashboard')),
]

# Debug toolbar (dev only)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

# Serve media in dev
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
