"""
OTP Service — sends 6-digit codes via Email and SMS.

Email: Uses Django's email backend (console in dev, SMTP in prod).
SMS:   Pluggable — set SMS_PROVIDER in settings to 'msg91', 'twilio', or 'console'.
       Default is 'console' (prints to log — good for dev/testing).

To enable real SMS:
  1. Set SMS_PROVIDER = 'msg91' (or 'twilio') in settings
  2. Add SMS_AUTH_KEY, SMS_SENDER_ID in env vars
  3. pip install requests (already in most setups)
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

from trackwise_backend.apps.accounts.models import OTP

logger = logging.getLogger('trackwise_backend')


def send_otp(user, purpose='login'):
    """
    Send OTP to both email and phone (if phone exists).
    Returns dict with masked destinations.
    """
    results = {}

    # Email OTP
    email_otp = OTP.create_for_user(user, 'email', purpose)
    _send_email_otp(user.email, email_otp.code, purpose)
    results['email'] = user.masked_email
    logger.info(f'OTP sent to email: {user.email} ({purpose})')

    # SMS OTP (only if phone exists)
    if user.phone:
        sms_otp = OTP.create_for_user(user, 'sms', purpose)
        _send_sms_otp(user.phone, sms_otp.code, purpose)
        results['phone'] = user.masked_phone
        logger.info(f'OTP sent to phone: {user.masked_phone} ({purpose})')

    return results


def verify_otp(user, email_code, phone_code=None, purpose='login'):
    """
    Verify OTP codes. Returns (success, error_message).
    If user has no phone, phone_code is optional.
    """
    # Verify email OTP
    email_otp = OTP.objects.filter(
        user=user, channel='email', purpose=purpose, is_used=False
    ).order_by('-created_at').first()

    if not email_otp or not email_otp.is_valid:
        return False, 'Email OTP expired. Please request a new one.'

    email_otp.attempts += 1
    email_otp.save(update_fields=['attempts'])

    if email_otp.code != email_code:
        remaining = 5 - email_otp.attempts
        return False, f'Invalid email OTP. {remaining} attempts left.'

    # Verify phone OTP (if user has phone)
    if user.phone:
        if not phone_code:
            return False, 'Phone OTP is required.'

        sms_otp = OTP.objects.filter(
            user=user, channel='sms', purpose=purpose, is_used=False
        ).order_by('-created_at').first()

        if not sms_otp or not sms_otp.is_valid:
            return False, 'Phone OTP expired. Please request a new one.'

        sms_otp.attempts += 1
        sms_otp.save(update_fields=['attempts'])

        if sms_otp.code != phone_code:
            remaining = 5 - sms_otp.attempts
            return False, f'Invalid phone OTP. {remaining} attempts left.'

        sms_otp.is_used = True
        sms_otp.save(update_fields=['is_used'])
        user.is_phone_verified = True

    # Mark email OTP used
    email_otp.is_used = True
    email_otp.save(update_fields=['is_used'])
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified', 'is_phone_verified'])

    return True, None


def _send_email_otp(email, code, purpose):
    subject = {
        'register': 'TrackWise — Verify your email',
        'login':    'TrackWise — Login verification code',
        'reset':    'TrackWise — Password reset code',
    }.get(purpose, 'TrackWise — Verification code')

    message = f'Your TrackWise verification code is: {code}\n\nThis code expires in 10 minutes.\nDo not share this code with anyone.'

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f'Failed to send email OTP to {email}: {e}')
        # In dev, also print to console
        logger.info(f'[DEV] Email OTP for {email}: {code}')


def _send_sms_otp(phone, code, purpose):
    provider = getattr(settings, 'SMS_PROVIDER', 'console')

    if provider == 'console':
        logger.info(f'[SMS-CONSOLE] OTP for {phone}: {code}')
        print(f'\n📱 SMS OTP for {phone}: {code}\n')
        return

    if provider == 'msg91':
        _send_msg91(phone, code)
    elif provider == 'twilio':
        _send_twilio(phone, code)
    else:
        logger.warning(f'Unknown SMS_PROVIDER: {provider}, falling back to console')
        logger.info(f'[SMS-FALLBACK] OTP for {phone}: {code}')


def _send_msg91(phone, code):
    """Send SMS via MSG91 (Indian SMS gateway)."""
    try:
        import requests
        auth_key  = getattr(settings, 'MSG91_AUTH_KEY', '')
        sender_id = getattr(settings, 'MSG91_SENDER_ID', 'TRKWSE')
        template_id = getattr(settings, 'MSG91_TEMPLATE_ID', '')

        if not auth_key:
            logger.error('MSG91_AUTH_KEY not set')
            return

        url = 'https://control.msg91.com/api/v5/otp'
        payload = {
            'template_id': template_id,
            'mobile': f'91{phone}' if not phone.startswith('91') else phone,
            'authkey': auth_key,
            'otp': code,
        }
        resp = requests.post(url, json=payload, timeout=10)
        logger.info(f'MSG91 response for {phone}: {resp.status_code} {resp.text[:100]}')
    except Exception as e:
        logger.error(f'MSG91 SMS failed for {phone}: {e}')


def _send_twilio(phone, code):
    """Send SMS via Twilio."""
    try:
        from twilio.rest import Client
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

        if not all([account_sid, auth_token, from_number]):
            logger.error('Twilio credentials not set')
            return

        client = Client(account_sid, auth_token)
        formatted = f'+91{phone}' if not phone.startswith('+') else phone
        client.messages.create(
            body=f'Your TrackWise code is: {code}. Valid for 10 minutes.',
            from_=from_number,
            to=formatted,
        )
        logger.info(f'Twilio SMS sent to {phone}')
    except Exception as e:
        logger.error(f'Twilio SMS failed for {phone}: {e}')
