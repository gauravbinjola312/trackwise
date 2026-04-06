from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',        views.DashboardView.as_view(), name='dashboard'),
    path('alerts/', views.AlertsView.as_view(),    name='alerts'),
    path('export/', views.ExportView.as_view(),    name='export'),
]
