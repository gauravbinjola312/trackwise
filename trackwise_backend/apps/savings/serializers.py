from rest_framework import serializers
from .models import SavingEntry


class SavingEntrySerializer(serializers.ModelSerializer):
    row_flag         = serializers.ReadOnlyField()
    savings_rate_pct = serializers.ReadOnlyField()
    type             = serializers.CharField(source='inv_type')

    class Meta:
        model  = SavingEntry
        fields = [
            'id', 'date', 'name', 'type', 'amount', 'monthly_income',
            'platform', 'notes', 'row_flag', 'savings_rate_pct', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'row_flag', 'savings_rate_pct', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount cannot be negative.')
        return value


class SavingEntryListSerializer(serializers.ModelSerializer):
    row_flag = serializers.ReadOnlyField()
    type     = serializers.CharField(source='inv_type')

    class Meta:
        model  = SavingEntry
        fields = ['id', 'date', 'name', 'type', 'amount', 'monthly_income', 'platform', 'row_flag']
