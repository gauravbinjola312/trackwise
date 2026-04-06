from rest_framework import serializers
from .models import Subscription, PaymentEvent


class SubscriptionSerializer(serializers.ModelSerializer):
    is_active       = serializers.ReadOnlyField()
    trial_days_left = serializers.ReadOnlyField()
    plan_price      = serializers.ReadOnlyField()

    class Meta:
        model  = Subscription
        fields = [
            'id', 'status', 'plan', 'is_active', 'trial_days_left', 'plan_price',
            'trial_ends_at', 'paid_until', 'razorpay_sub_id', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'razorpay_sub_id', 'trial_ends_at', 'paid_until', 'created_at', 'updated_at']


class CreateSubscriptionSerializer(serializers.Serializer):
    """POST /api/v1/subscriptions/ — choose monthly or yearly."""
    plan = serializers.ChoiceField(choices=['monthly', 'yearly'])


class PaymentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PaymentEvent
        fields = ['id', 'event_type', 'amount', 'processed_at']
