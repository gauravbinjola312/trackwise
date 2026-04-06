from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile


# ── AUTH SERIALIZERS ──────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    """
    POST /api/v1/auth/register/
    Body: { full_name, email, password, password_confirm }
    """
    password         = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'password', 'password_confirm']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    POST /api/v1/auth/login/
    Body: { email, password }
    Returns: { access, refresh, user }
    """
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email    = attrs['email'].lower()
        password = attrs['password']
        user     = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        attrs['user']    = user
        attrs['access']  = str(refresh.access_token)
        attrs['refresh'] = str(refresh)
        return attrs


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response shape after token refresh."""
    access  = serializers.CharField()
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    """
    POST /api/v1/auth/change-password/
    Body: { current_password, new_password, new_password_confirm }
    """
    current_password     = serializers.CharField(write_only=True)
    new_password         = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """POST /api/v1/auth/forgot-password/  Body: { email }"""
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """POST /api/v1/auth/reset-password/  Body: { token, new_password, new_password_confirm }"""
    token                = serializers.UUIDField()
    new_password         = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


# ── USER / PROFILE SERIALIZERS ────────────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Profile
        fields = ['monthly_income', 'currency', 'avatar_url', 'timezone', 'notifications_enabled', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Full user info including profile."""
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'email', 'full_name', 'is_email_verified', 'created_at', 'profile']
        read_only_fields = ['id', 'email', 'is_email_verified', 'created_at']


class UpdateProfileSerializer(serializers.ModelSerializer):
    """PATCH /api/v1/auth/profile/"""
    full_name      = serializers.CharField(source='user.full_name', required=False)
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency       = serializers.CharField(max_length=3, required=False)
    avatar_url     = serializers.URLField(required=False, allow_blank=True)
    timezone       = serializers.CharField(max_length=50, required=False)
    notifications_enabled = serializers.BooleanField(required=False)

    class Meta:
        model  = Profile
        fields = ['full_name', 'monthly_income', 'currency', 'avatar_url', 'timezone', 'notifications_enabled']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if 'full_name' in user_data:
            instance.user.full_name = user_data['full_name']
            instance.user.save(update_fields=['full_name'])
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
