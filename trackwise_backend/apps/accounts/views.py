"""
Auth Views — 2FA Authentication Flow.

POST   /api/v1/auth/register/          → Create account + send OTP
POST   /api/v1/auth/login/             → Validate creds + send OTP
POST   /api/v1/auth/verify-otp/        → Verify OTP → return JWT tokens
POST   /api/v1/auth/resend-otp/        → Resend OTP codes
POST   /api/v1/auth/logout/            → Blacklist refresh token
POST   /api/v1/auth/token/refresh/     → Get new access token
POST   /api/v1/auth/change-password/   → Change password (authenticated)
POST   /api/v1/auth/forgot-password/   → Send reset OTP
POST   /api/v1/auth/reset-password/    → Reset password with OTP
GET    /api/v1/auth/me/                → Get current user info
PATCH  /api/v1/auth/profile/           → Update profile
DELETE /api/v1/auth/account/           → Delete account
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Profile, OTP
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer,
    ResetPasswordSerializer, UpdateProfileSerializer,
)
from trackwise_backend.utils.exceptions import UserLimitReachedError
from trackwise_backend.utils.otp_service import send_otp, verify_otp

User   = get_user_model()
logger = logging.getLogger('trackwise_backend')


def _jwt_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ── REGISTRATION (Step 1: create account + send OTP) ─────────

class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Body: { full_name, email, phone, password, password_confirm }
    Response: { otp_required: true, user_id, sent_to: {email, phone} }
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        if User.objects.count() >= settings.MAX_USERS:
            raise UserLimitReachedError()

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        Profile.objects.create(user=user)

        from trackwise_backend.apps.subscriptions.models import Subscription
        Subscription.objects.create(
            user=user, status='trial',
            trial_ends_at=timezone.now() + timedelta(days=settings.TRIAL_PERIOD_DAYS),
        )

        # Send OTP to email + phone
        sent_to = send_otp(user, purpose='register')

        logger.info(f'New user registered (pending OTP): {user.email}')

        return Response({
            'success': True,
            'message': 'Account created. Please verify with OTP.',
            'data': {
                'otp_required': True,
                'user_id':      str(user.id),
                'sent_to':      sent_to,
            }
        }, status=status.HTTP_201_CREATED)


# ── LOGIN (Step 1: validate creds + send OTP) ────────────────

class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Body: { email, password }
    Response: { otp_required: true, user_id, sent_to: {email, phone} }
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        email    = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response({'success': False, 'error': {'message': 'Email and password are required.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request=request, email=email, password=password)

        if not user:
            return Response({'success': False, 'error': {'message': 'Invalid email or password.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            return Response({'success': False, 'error': {'message': 'This account has been deactivated.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        # Demo account bypass — skip OTP for testing
        if email == 'demo@trackwise.in':
            tokens = _jwt_for_user(user)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            logger.info(f'Demo user logged in (OTP bypassed): {email}')
            return Response({
                'success': True,
                'data': {**tokens, 'user': UserSerializer(user).data},
            })

        # Send OTP for normal users
        sent_to = send_otp(user, purpose='login')

        logger.info(f'Login OTP sent to: {user.email}')

        return Response({
            'success': True,
            'message': 'OTP sent. Please verify to complete login.',
            'data': {
                'otp_required': True,
                'user_id':      str(user.id),
                'sent_to':      sent_to,
            }
        })


# ── VERIFY OTP (Step 2: verify codes + return tokens) ────────

class VerifyOTPView(APIView):
    """
    POST /api/v1/auth/verify-otp/
    Body: { user_id, email_otp, phone_otp (optional if no phone), purpose }
    Response: { access, refresh, user }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id    = request.data.get('user_id', '')
        email_otp  = request.data.get('email_otp', '').strip()
        phone_otp  = request.data.get('phone_otp', '').strip() or None
        purpose    = request.data.get('purpose', 'login')

        if not user_id or not email_otp:
            return Response({'success': False, 'error': {'message': 'user_id and email_otp are required.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, Exception):
            return Response({'success': False, 'error': {'message': 'Invalid user.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        success, error = verify_otp(user, email_otp, phone_otp, purpose)

        if not success:
            return Response({'success': False, 'error': {'message': error}},
                            status=status.HTTP_400_BAD_REQUEST)

        # OTP verified — issue tokens
        tokens = _jwt_for_user(user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        logger.info(f'OTP verified, logged in: {user.email}')

        return Response({
            'success': True,
            'data': {
                **tokens,
                'user': UserSerializer(user).data,
            }
        })


# ── RESEND OTP ────────────────────────────────────────────────

class ResendOTPView(APIView):
    """
    POST /api/v1/auth/resend-otp/
    Body: { user_id, purpose }
    Rate limited: max 1 per 60 seconds.
    """
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        user_id = request.data.get('user_id', '')
        purpose = request.data.get('purpose', 'login')

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, Exception):
            return Response({'success': False, 'error': {'message': 'Invalid user.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        # Rate limit: check if OTP was sent in last 60 seconds
        recent = OTP.objects.filter(
            user=user, purpose=purpose,
            created_at__gte=timezone.now() - timedelta(seconds=60)
        ).exists()

        if recent:
            return Response({'success': False, 'error': {'message': 'Please wait 60 seconds before requesting a new OTP.'}},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        sent_to = send_otp(user, purpose)

        return Response({
            'success': True,
            'message': 'OTP resent.',
            'data':    {'sent_to': sent_to},
        })


# ── LOGOUT ────────────────────────────────────────────────────

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            logger.info(f'User logged out: {request.user.email}')
            return Response({'success': True, 'message': 'Logged out successfully.'})
        except Exception:
            return Response({'success': True, 'message': 'Logged out.'})


# ── TOKEN REFRESH ─────────────────────────────────────────────

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response({'success': True, 'data': response.data})
        return response


# ── CURRENT USER ──────────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'success': True, 'data': UserSerializer(request.user).data})


# ── PROFILE UPDATE ────────────────────────────────────────────

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = UpdateProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Profile updated.', 'data': UserSerializer(request.user).data})


# ── CHANGE PASSWORD ───────────────────────────────────────────

class ChangePasswordView(APIView):
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
    permission_classes = [AllowAny]
    throttle_scope     = 'anon'

    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        try:
            user = User.objects.get(email=email, is_active=True)
            send_otp(user, purpose='reset')
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists
        return Response({'success': True, 'message': 'If that email exists, a reset code has been sent.'})


# ── RESET PASSWORD ────────────────────────────────────────────

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email     = serializer.validated_data.get('email', '').lower().strip()
        otp_code  = serializer.validated_data.get('otp_code', '')
        new_pass  = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'success': False, 'error': {'message': 'Invalid email.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        success, error = verify_otp(user, otp_code, purpose='reset')
        if not success:
            return Response({'success': False, 'error': {'message': error}},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_pass)
        user.save()
        logger.info(f'Password reset for: {user.email}')
        return Response({'success': True, 'message': 'Password reset successfully. You can now login.'})


# ── VERIFY EMAIL (legacy — now handled by OTP) ───────────────

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({'success': True, 'message': 'Use /verify-otp/ endpoint for verification.'})


# ── DELETE ACCOUNT ────────────────────────────────────────────

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({'success': False, 'error': {'message': 'Incorrect password.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        user.is_active = False
        user.email = f'deleted_{user.id}@deleted.trackwise'
        user.save()
        logger.info(f'Account deleted: {user.id}')
        return Response({'success': True, 'message': 'Account deleted.'}, status=status.HTTP_204_NO_CONTENT)
