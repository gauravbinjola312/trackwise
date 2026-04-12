from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile


class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone            = serializers.CharField(max_length=15, required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'phone', 'password', 'password_confirm']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_phone(self, value):
        if value:
            import re
            cleaned = re.sub(r'[^0-9]', '', value)
            if len(cleaned) < 10:
                raise serializers.ValidationError('Enter a valid phone number (min 10 digits).')
            return cleaned
        return ''

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
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
        refresh = RefreshToken.for_user(user)
        attrs['user']    = user
        attrs['access']  = str(refresh.access_token)
        attrs['refresh'] = str(refresh)
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password     = serializers.CharField(write_only=True)
    new_password         = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email                = serializers.EmailField()
    otp_code             = serializers.CharField(max_length=6)
    new_password         = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Profile
        fields = ['monthly_income', 'currency', 'avatar_url', 'timezone', 'notifications_enabled', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'email', 'phone', 'full_name', 'is_email_verified', 'is_phone_verified', 'created_at', 'profile']
        read_only_fields = ['id', 'email', 'phone', 'is_email_verified', 'is_phone_verified', 'created_at']


class UpdateProfileSerializer(serializers.ModelSerializer):
    full_name      = serializers.CharField(source='user.full_name', required=False)
    phone          = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency       = serializers.CharField(max_length=3, required=False)
    avatar_url     = serializers.URLField(required=False, allow_blank=True)
    timezone       = serializers.CharField(max_length=50, required=False)
    notifications_enabled = serializers.BooleanField(required=False)

    class Meta:
        model  = Profile
        fields = ['full_name', 'phone', 'monthly_income', 'currency', 'avatar_url', 'timezone', 'notifications_enabled']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if 'full_name' in user_data:
            instance.user.full_name = user_data['full_name']
        if 'phone' in user_data:
            instance.user.phone = user_data['phone']
        if user_data:
            instance.user.save(update_fields=[k for k in user_data.keys()])
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
