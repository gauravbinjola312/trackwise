from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'savings'
router   = DefaultRouter()
router.register('', views.SavingViewSet, basename='saving')

urlpatterns = [path('', include(router.urls))]
