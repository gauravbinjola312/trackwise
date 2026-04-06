from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('',         views.SubscriptionView.as_view(),     name='subscription'),
    path('cancel/',  views.CancelSubscriptionView.as_view(),name='cancel'),
    path('history/', views.PaymentHistoryView.as_view(),    name='history'),
    path('webhook/', views.SubscriptionWebhookView.as_view(),name='webhook'),
]
