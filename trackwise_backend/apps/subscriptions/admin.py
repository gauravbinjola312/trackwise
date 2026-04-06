from django.contrib import admin
from .models import Subscription, PaymentEvent

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'status', 'plan', 'is_active', 'trial_ends_at', 'paid_until']
    list_filter   = ['status', 'plan']
    search_fields = ['user__email', 'razorpay_sub_id']
    ordering      = ['-created_at']
    readonly_fields = ['id', 'is_active', 'trial_days_left', 'plan_price', 'created_at', 'updated_at']
    list_select_related = ['user']

@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display  = ['subscription', 'event_type', 'amount', 'processed_at']
    list_filter   = ['event_type']
    ordering      = ['-processed_at']
    readonly_fields = ['id', 'processed_at']
