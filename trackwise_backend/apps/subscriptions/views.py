"""
Subscription & Payment Views

GET    /api/v1/subscriptions/             Get current subscription
POST   /api/v1/subscriptions/             Create Razorpay subscription (choose plan)
POST   /api/v1/subscriptions/cancel/      Cancel active subscription
GET    /api/v1/subscriptions/history/     Payment event history
POST   /api/v1/subscriptions/webhook/     Razorpay webhook (no auth)
"""
import hashlib
import hmac
import json
import logging

try:
    import razorpay
except ImportError:
    razorpay = None
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Subscription, PaymentEvent
from .serializers import SubscriptionSerializer, CreateSubscriptionSerializer, PaymentEventSerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin

logger = logging.getLogger('trackwise_backend')


def get_razorpay_client():
    if razorpay is None:
        raise ImportError('razorpay package is not installed. Run: pip install razorpay')
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class SubscriptionView(SuccessResponseMixin, APIView):
    """
    GET  /api/v1/subscriptions/   Return current user's subscription status.
    POST /api/v1/subscriptions/   Create a Razorpay subscription and return subscription_id.

    Flow for POST:
    1. Validate plan choice (monthly/yearly)
    2. Get or create Razorpay customer for user
    3. Create Razorpay subscription with chosen plan
    4. Save razorpay_sub_id to DB
    5. Return { subscription_id, key_id } to client
    6. Client opens Razorpay checkout with subscription_id
    7. On payment, Razorpay sends webhook → SubscriptionWebhookView activates it
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub, _ = Subscription.objects.get_or_create(
            user=request.user,
            defaults={'status': 'trial', 'trial_ends_at': timezone.now() + timezone.timedelta(days=7)}
        )
        return self.success(SubscriptionSerializer(sub).data)

    def post(self, request):
        serializer = CreateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data['plan']

        plan_id = (
            settings.RAZORPAY_PLAN_ID_YEARLY
            if plan == 'yearly'
            else settings.RAZORPAY_PLAN_ID_MONTHLY
        )

        if not plan_id:
            return Response({
                'success': False,
                'error':   {'message': 'Payment is not configured. Please contact support.'}
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        sub, _ = Subscription.objects.get_or_create(user=request.user)

        try:
            client = get_razorpay_client()

            # Create or retrieve Razorpay customer
            if not sub.razorpay_cust_id:
                customer = client.customer.create({
                    'name':    request.user.full_name,
                    'email':   request.user.email,
                    'contact': '',
                })
                sub.razorpay_cust_id = customer['id']
                sub.save(update_fields=['razorpay_cust_id'])

            # Create Razorpay subscription
            rz_sub = client.subscription.create({
                'plan_id':         plan_id,
                'customer_notify': 1,
                'total_count':     120,  # 10 years max
                'customer_id':     sub.razorpay_cust_id,
            })

            sub.razorpay_sub_id = rz_sub['id']
            sub.plan            = plan
            sub.save(update_fields=['razorpay_sub_id', 'plan'])

            logger.info(f'Razorpay subscription created for {request.user.email}: {rz_sub["id"]}')

            return self.success({
                'subscription_id': rz_sub['id'],
                'key_id':          settings.RAZORPAY_KEY_ID,
                'plan':            plan,
                'amount':          1999 if plan == 'yearly' else 199,
            }, 'Subscription initiated. Complete payment in the app.')

        except Exception as e:
            logger.error(f'Razorpay error for {request.user.email}: {e}')
            return Response({
                'success': False,
                'error':   {'message': 'Payment service error. Please try again.'}
            }, status=status.HTTP_502_BAD_GATEWAY)


class CancelSubscriptionView(SuccessResponseMixin, APIView):
    """POST /api/v1/subscriptions/cancel/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            return Response({'success': False, 'error': {'message': 'No active subscription.'}},
                            status=status.HTTP_404_NOT_FOUND)

        if sub.status not in ('active',):
            return Response({'success': False, 'error': {'message': 'No active subscription to cancel.'}},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            if sub.razorpay_sub_id:
                client = get_razorpay_client()
                client.subscription.cancel(sub.razorpay_sub_id, {'cancel_at_cycle_end': 1})
        except Exception as e:
            logger.warning(f'Razorpay cancel failed for {request.user.email}: {e}')

        sub.status       = 'cancelled'
        sub.cancelled_at = timezone.now()
        sub.save(update_fields=['status', 'cancelled_at'])
        logger.info(f'Subscription cancelled: {request.user.email}')
        return self.success(SubscriptionSerializer(sub).data, 'Subscription cancelled.')


class PaymentHistoryView(SuccessResponseMixin, APIView):
    """GET /api/v1/subscriptions/history/ — Payment event log."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub    = request.user.subscription
            events = sub.events.order_by('-processed_at')[:50]
            return self.success(PaymentEventSerializer(events, many=True).data)
        except Subscription.DoesNotExist:
            return self.success([])


@method_decorator(csrf_exempt, name='dispatch')
class SubscriptionWebhookView(APIView):
    """
    POST /api/v1/subscriptions/webhook/
    Receives Razorpay webhook events. No auth — verified by HMAC signature.

    Handles:
    - subscription.activated  → set status=active, paid_until=next billing date
    - subscription.charged    → extend paid_until
    - subscription.cancelled  → set status=cancelled
    - subscription.expired    → set status=expired
    - subscription.halted     → set status=expired (payment failure)

    Security: Verifies Razorpay-Signature header before processing.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify signature
        payload   = request.body
        signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

        if not self._verify_signature(payload, signature):
            logger.warning('Razorpay webhook: invalid signature')
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get('event', '')
        entity     = event.get('payload', {}).get('subscription', {}).get('entity', {})
        rz_sub_id  = entity.get('id', '')
        event_id   = event.get('id', '')

        # Deduplicate events
        if PaymentEvent.objects.filter(razorpay_event_id=event_id).exists():
            return Response({'status': 'duplicate'})

        try:
            sub = Subscription.objects.get(razorpay_sub_id=rz_sub_id)
        except Subscription.DoesNotExist:
            logger.warning(f'Webhook: subscription not found: {rz_sub_id}')
            return Response({'status': 'not_found'})

        # Process event
        amount = None

        if event_type in ('subscription.activated', 'subscription.charged'):
            current_end = entity.get('current_end')
            if current_end:
                sub.paid_until = timezone.datetime.fromtimestamp(current_end, tz=timezone.utc)
            sub.status = 'active'
            sub.save(update_fields=['status', 'paid_until'])
            logger.info(f'Subscription activated/charged: {sub.user.email}')

        elif event_type in ('subscription.cancelled',):
            sub.status       = 'cancelled'
            sub.cancelled_at = timezone.now()
            sub.save(update_fields=['status', 'cancelled_at'])
            logger.info(f'Subscription cancelled via webhook: {sub.user.email}')

        elif event_type in ('subscription.expired', 'subscription.halted'):
            sub.status = 'expired'
            sub.save(update_fields=['status'])
            logger.info(f'Subscription expired/halted: {sub.user.email}')

        # Log the event
        PaymentEvent.objects.create(
            subscription=sub,
            event_type=event_type,
            razorpay_event_id=event_id,
            amount=amount,
            payload=event,
        )

        return Response({'status': 'processed'})

    def _verify_signature(self, payload, signature):
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            return True  # Skip in dev if secret not set
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
