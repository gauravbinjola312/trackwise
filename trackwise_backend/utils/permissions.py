"""
Custom DRF permissions.
"""
from rest_framework.permissions import BasePermission
from django.utils import timezone


class IsSubscriptionActive(BasePermission):
    """
    Allows access only to users with an active subscription or trial.
    Used on premium-only endpoints.
    """
    message = 'An active subscription is required to access this feature.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.subscription.is_active
        except Exception:
            return False


class IsOwner(BasePermission):
    """
    Object-level permission: only the owner of an object can access it.
    The model must have a `user` FK field.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsEmailVerified(BasePermission):
    """Only verified users can access. Good for write operations."""
    message = 'Please verify your email address first.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_email_verified
        )
