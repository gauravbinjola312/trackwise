"""
Auth Views — Full authentication flow.

POST   /api/v1/auth/register/          → Create account
POST   /api/v1/auth/login/             → Login + get tokens
POST   /api/v1/auth/logout/            → Blacklist refresh token
POST   /api/v1/auth/token/refresh/     → Get new access token
POST   /api/v1/auth/change-password/   → Change password (authenticated)
POST   /api/v1/auth/forgot-password/   → Send password reset email
POST   /api/v1/auth/reset-password/    → Reset password with token
POST   /api/v1/auth/verify-email/      → Verify email with token
GET    /api/v1/auth/me/                → Get current user info
PATCH  /api/v1/auth/profile/           → Update profile
DELETE /api/v1/auth/account/           → Delete account
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Profile, EmailVerificationToken
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer,
    ResetPasswordSerializer, UpdateProfileSerializer,
)
from trackwise_backend.utils.exceptions import UserLimitReachedError

User   = get_user_model()
logger = logging.getLogger('trackwise_backend')


# ── REGISTRATION ──────────────────────────────────────────────

class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Flow:
    1. Validate email uniqueness + password strength
    2. Check user limit (max 500)
    3. Create User + Profile + Subscription (trial)
    4. Send verification email
    5. Return JWT tokens + user info

    Request:
        { "full_name": "Rahul Sharma", "email": "rahul@example.com",
          "password": "Secret123!", "password_confirm": "Secret123!" }

    Response 201:
        { "success": true, "data": { "access": "...", "refresh": "...", "user": {...} } }
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        # Enforce user limit
        if User.objects.count() >= settings.MAX_USERS:
            raise UserLimitReachedError()

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create profile
        Profile.objects.create(user=user)

        # Create subscription (trial)
        from trackwise_backend.apps.subscriptions.models import Subscription
        Subscription.objects.create(
            user=user,
            status='trial',
            trial_ends_at=timezone.now() + timedelta(days=settings.TRIAL_PERIOD_DAYS),
        )

        # Send welcome + verification email (async via Celery)
        self._send_verification_email(user)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        logger.info(f'New user registered: {user.email}')

        return Response({
            'success': True,
            'message': 'Account created successfully. Please verify your email.',
            'data': {
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
                'user':    UserSerializer(user).data,
            }
        }, status=status.HTTP_201_CREATED)

    def _send_verification_email(self, user):
        try:
            token = EmailVerificationToken.objects.create(
                user=user,
                token_type='verify',
                expires_at=timezone.now() + timedelta(hours=48),
            )
            verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token.id}"
            send_mail(
                subject=  'Verify your TrackWise account',
                message=  f'Click to verify your email:\n\n{verify_url}\n\nLink expires in 48 hours.',
                from_email= settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f'Failed to send verification email to {user.email}: {e}')


# ── LOGIN ─────────────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Flow:
    1. Validate credentials
    2. Check if user is active
    3. Return JWT access + refresh tokens

    Request:  { "email": "rahul@example.com", "password": "Secret123!" }
    Response: { "success": true, "data": { "access": "...", "refresh": "...", "user": {...} } }
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        logger.info(f'User logged in: {user.email}')

        return Response({
            'success': True,
            'data': {
                'access':  serializer.validated_data['access'],
                'refresh': serializer.validated_data['refresh'],
                'user':    UserSerializer(user).data,
            }
        })


# ── LOGOUT ────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token, making both tokens invalid.

    Request:  { "refresh": "eyJ..." }
    Response: { "success": true, "message": "Logged out successfully." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'success': False, 'error': {'message': 'Refresh token is required.'}},
                                status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f'User logged out: {request.user.email}')
            return Response({'success': True, 'message': 'Logged out successfully.'})
        except Exception:
            return Response({'success': True, 'message': 'Logged out.'})  # Treat as success


# ── TOKEN REFRESH ─────────────────────────────────────────────

class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/
    Uses SimpleJWT's built-in view, wrapped with our response format.

    Request:  { "refresh": "eyJ..." }
    Response: { "success": true, "data": { "access": "...", "refresh": "..." } }
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response({'success': True, 'data': response.data})
        return response


# ── CURRENT USER ──────────────────────────────────────────────

class MeView(APIView):
    """
    GET  /api/v1/auth/me/    → Current user info
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})


# ── PROFILE UPDATE ────────────────────────────────────────────

class ProfileView(APIView):
    """
    PATCH /api/v1/auth/profile/

    Update name, monthly_income, currency, avatar, timezone, notifications.

    Request (all fields optional):
        { "full_name": "Rahul S", "monthly_income": "80000", "currency": "INR" }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = UpdateProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': 'Profile updated.',
            'data':    UserSerializer(request.user).data,
        })


# ── CHANGE PASSWORD ───────────────────────────────────────────

class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/

    Request: { "current_password": "old", "new_password": "New123!", "new_password_confirm": "New123!" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        logger.info(f'Password changed for: {request.user.email}')
        return Response({'success': True, 'message': 'Password changed successfully.'})


# ── FORGOT PASSWORD ───────────────────────────────────────────

class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Sends a password reset email.

    Request:  { "email": "rahul@example.com" }
    Response: { "success": true, "message": "Reset link sent if email exists." }
    (Always returns 200 to prevent email enumeration)
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()

        try:
            user  = User.objects.get(email=email, is_active=True)
            token = EmailVerificationToken.objects.create(
                user=user, token_type='reset',
                expires_at=timezone.now() + timedelta(hours=2),
            )
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.id}"
            send_mail(
                subject='Reset your TrackWise password',
                message=f'Click to reset your password:\n\n{reset_url}\n\nLink expires in 2 hours.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists

        return Response({'success': True, 'message': 'If that email exists, a reset link has been sent.'})


# ── RESET PASSWORD ────────────────────────────────────────────

class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/

    Request:  { "token": "uuid", "new_password": "New123!", "new_password_confirm": "New123!" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = EmailVerificationToken.objects.get(
                id=serializer.validated_data['token'],
                token_type='reset',
            )
        except EmailVerificationToken.DoesNotExist:
            return Response({'success': False, 'error': {'message': 'Invalid or expired token.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        if not token.is_valid():
            return Response({'success': False, 'error': {'message': 'Token has expired or already been used.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        token.user.set_password(serializer.validated_data['new_password'])
        token.user.save()
        token.is_used = True
        token.save()

        logger.info(f'Password reset for: {token.user.email}')
        return Response({'success': True, 'message': 'Password reset successfully. You can now login.'})


# ── EMAIL VERIFICATION ────────────────────────────────────────

class VerifyEmailView(APIView):
    """
    POST /api/v1/auth/verify-email/
    Request: { "token": "uuid" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token_id = request.data.get('token')
        try:
            token = EmailVerificationToken.objects.select_related('user').get(
                id=token_id, token_type='verify'
            )
        except (EmailVerificationToken.DoesNotExist, Exception):
            return Response({'success': False, 'error': {'message': 'Invalid verification token.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        if not token.is_valid():
            return Response({'success': False, 'error': {'message': 'Token expired or already used.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        token.user.is_email_verified = True
        token.user.save(update_fields=['is_email_verified'])
        token.is_used = True
        token.save()

        return Response({'success': True, 'message': 'Email verified successfully.'})


# ── DELETE ACCOUNT ────────────────────────────────────────────

class DeleteAccountView(APIView):
    """
    DELETE /api/v1/auth/account/
    Soft-deletes (deactivates) the account.
    Request: { "password": "current_password" }
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({'success': False, 'error': {'message': 'Incorrect password.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        user.is_active = False
        user.email     = f'deleted_{user.id}@deleted.trackwise'  # Free up email
        user.save()
        logger.info(f'Account deleted: {user.id}')
        return Response({'success': True, 'message': 'Account deleted.'}, status=status.HTTP_204_NO_CONTENT)
