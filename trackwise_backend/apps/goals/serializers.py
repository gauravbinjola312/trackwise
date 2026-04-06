from rest_framework import serializers
from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    pct_complete   = serializers.ReadOnlyField()
    days_left      = serializers.ReadOnlyField()
    is_overdue     = serializers.ReadOnlyField()
    daily_required = serializers.ReadOnlyField()
    status         = serializers.ReadOnlyField()

    class Meta:
        model  = Goal
        fields = [
            'id', 'name', 'category', 'target', 'current', 'deadline', 'notes',
            'pct_complete', 'days_left', 'is_overdue', 'daily_required', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'pct_complete', 'days_left', 'is_overdue', 'daily_required', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        current = attrs.get('current', self.instance.current if self.instance else 0)
        target  = attrs.get('target',  self.instance.target  if self.instance else 1)
        if float(current) > float(target):
            raise serializers.ValidationError({'current': 'Current progress cannot exceed target.'})
        return attrs


class GoalProgressSerializer(serializers.Serializer):
    """PATCH /api/v1/goals/{id}/progress/ — quick progress update"""
    current = serializers.DecimalField(max_digits=14, decimal_places=2)
