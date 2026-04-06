"""
Custom User model + Profile model.
Uses email as the primary identifier (not username).
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager — email instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user  = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    TrackWise user.
    Primary key: UUID (safer than auto-increment for APIs)
    Login field: email
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True, db_index=True)
    full_name  = models.CharField(max_length=150, blank=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table     = 'users'
        verbose_name = 'User'
        ordering     = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        parts = self.full_name.split()
        return parts[0] if parts else ''


class Profile(models.Model):
    """
    Extended user preferences and financial settings.
    One-to-one with User.
    """
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


class EmailVerificationToken(models.Model):
    """One-time tokens for email verification and password reset."""
    TOKEN_TYPES = [
        ('verify',  'Email Verification'),
        ('reset',   'Password Reset'),
    ]
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
