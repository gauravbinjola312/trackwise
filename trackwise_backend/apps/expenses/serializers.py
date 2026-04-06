from rest_framework import serializers
from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    """Full serializer for create/update/read."""
    row_flag = serializers.ReadOnlyField()

    class Meta:
        model   = Expense
        fields  = ['id', 'date', 'description', 'category', 'amount', 'payment', 'notes', 'row_flag', 'created_at', 'updated_at']
        read_only_fields = ['id', 'row_flag', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount cannot be negative.')
        return value


class ExpenseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    row_flag = serializers.ReadOnlyField()

    class Meta:
        model  = Expense
        fields = ['id', 'date', 'description', 'category', 'amount', 'payment', 'row_flag']


class ExpenseBulkCreateSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        expenses = [Expense(**item) for item in validated_data]
        return Expense.objects.bulk_create(expenses)


class ExpenseBulkSerializer(serializers.ModelSerializer):
    class Meta:
        model       = Expense
        fields      = ['date', 'description', 'category', 'amount', 'payment', 'notes']
        list_serializer_class = ExpenseBulkCreateSerializer
