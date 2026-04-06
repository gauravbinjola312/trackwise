from rest_framework import serializers
from .models import LearningSession


class LearningSessionSerializer(serializers.ModelSerializer):
    row_flag = serializers.ReadOnlyField()

    class Meta:
        model  = LearningSession
        fields = ['id', 'date', 'topic', 'source', 'hours', 'status', 'notes', 'row_flag', 'created_at', 'updated_at']
        read_only_fields = ['id', 'row_flag', 'created_at', 'updated_at']

    def validate_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError('Hours must be greater than 0.')
        if value > 24:
            raise serializers.ValidationError('Hours cannot exceed 24 per session.')
        return value


class LearningSessionListSerializer(serializers.ModelSerializer):
    row_flag = serializers.ReadOnlyField()

    class Meta:
        model  = LearningSession
        fields = ['id', 'date', 'topic', 'source', 'hours', 'status', 'row_flag']
