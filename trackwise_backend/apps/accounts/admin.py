from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display   = ['email', 'full_name', 'is_email_verified', 'is_active', 'created_at']
    list_filter    = ['is_active', 'is_email_verified', 'is_staff']
    search_fields  = ['email', 'full_name']
    ordering       = ['-created_at']
    fieldsets      = (
        (None,           {'fields': ('email', 'password')}),
        ('Personal',     {'fields': ('full_name',)}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'groups', 'user_permissions')}),
        ('Dates',        {'fields': ('created_at', 'last_login')}),
    )
    add_fieldsets  = (
        (None, {'classes': ('wide',), 'fields': ('email', 'full_name', 'password1', 'password2')}),
    )
    readonly_fields = ['created_at', 'last_login']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'monthly_income', 'currency', 'updated_at']
    search_fields = ['user__email']


@admin.register(EmailVerificationToken)
class TokenAdmin(admin.ModelAdmin):
    list_display  = ['user', 'token_type', 'is_used', 'created_at', 'expires_at']
    list_filter   = ['token_type', 'is_used']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']
