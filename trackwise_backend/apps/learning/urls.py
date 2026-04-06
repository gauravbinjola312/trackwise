from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'learning'
router   = DefaultRouter()
router.register('', views.LearningViewSet, basename='learning')

urlpatterns = [path('', include(router.urls))]
