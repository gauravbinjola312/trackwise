from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'expenses'
router   = DefaultRouter()
router.register('', views.ExpenseViewSet, basename='expense')

urlpatterns = [path('', include(router.urls))]
