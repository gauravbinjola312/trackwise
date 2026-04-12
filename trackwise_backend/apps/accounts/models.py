"""
Custom User model + Profile + OTP model for 2FA.
"""
import uuid
import random
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email             = models.EmailField(unique=True, db_index=True)
    phone             = models.CharField(max_length=15, blank=True, db_index=True)
    full_name         = models.CharField(max_length=150, blank=True)
    is_active         = models.BooleanField(default=True)
    is_staff          = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    created_at        = models.DateTimeField(default=timezone.now)
    last_login        = models.DateTimeField(null=True, blank=True)

    objects = UserManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        parts = self.full_name.split()
        return parts[0] if parts else ''

    @property
    def is_fully_verified(self):
        return self.is_email_verified and self.is_phone_verified

    @property
    def masked_phone(self):
        if len(self.phone) >= 4:
            return '*' * (len(self.phone) - 4) + self.phone[-4:]
        return self.phone

    @property
    def masked_email(self):
        parts = self.email.split('@')
        if len(parts) == 2 and len(parts[0]) > 2:
            return parts[0][:2] + '***' + '@' + parts[1]
        return self.email


class Profile(models.Model):
    user           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', primary_key=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency       = models.CharField(max_length=3, default='INR')
    avatar_url     = models.URLField(blank=True)
    timezone       = models.CharField(max_length=50, default='Asia/Kolkata')
    notifications_enabled = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles'

    def __str__(self):
        return f'Profile({self.user.email})'


class OTP(models.Model):
    """6-digit OTP for 2FA. Channels: email/sms. Purposes: register/login/reset."""
    CHANNEL_CHOICES = [('email', 'Email'), ('sms', 'SMS')]
    PURPOSE_CHOICES = [('register', 'Registration'), ('login', 'Login'), ('reset', 'Password Reset')]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code       = models.CharField(max_length=6)
    channel    = models.CharField(max_length=5, choices=CHANNEL_CHOICES)
    purpose    = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default='login')
    is_used    = models.BooleanField(default=False)
    attempts   = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'otps'
        ordering = ['-created_at']

    def __str__(self):
        return f'OTP({self.user.email}, {self.channel}, {self.purpose})'

    @property
    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now() and self.attempts < 5

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))

    @classmethod
    def create_for_user(cls, user, channel, purpose, minutes=10):
        cls.objects.filter(user=user, channel=channel, purpose=purpose, is_used=False).update(is_used=True)
        return cls.objects.create(
            user=user, code=cls.generate_code(), channel=channel, purpose=purpose,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
        )


class EmailVerificationToken(models.Model):
    """Legacy — kept for backward compat."""
    TOKEN_TYPES = [('verify', 'Email Verification'), ('reset', 'Password Reset')]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    token_type = models.CharField(max_length=10, choices=TOKEN_TYPES)
    is_used    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'email_verification_tokens'

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()
