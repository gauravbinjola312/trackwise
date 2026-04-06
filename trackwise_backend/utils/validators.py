"""
Shared validation helpers used across serializers.
"""
import re
from datetime import date
from rest_framework import serializers


def validate_indian_phone(value):
    """Validate a 10-digit Indian mobile number."""
    pattern = r'^[6-9]\d{9}$'
    if not re.match(pattern, str(value)):
        raise serializers.ValidationError('Enter a valid 10-digit Indian mobile number.')
    return value


def validate_future_date(value):
    """Date must be in the future."""
    if value <= date.today():
        raise serializers.ValidationError('Date must be in the future.')
    return value


def validate_not_future_date(value):
    """Date must not be in the future."""
    if value > date.today():
        raise serializers.ValidationError('Date cannot be in the future.')
    return value


def validate_positive(value):
    if value <= 0:
        raise serializers.ValidationError('Value must be greater than zero.')
    return value


def validate_non_negative(value):
    if value < 0:
        raise serializers.ValidationError('Value cannot be negative.')
    return value
