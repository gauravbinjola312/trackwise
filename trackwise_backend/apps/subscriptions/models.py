import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trial',     'Trial'),
        ('active',    'Active'),
        ('expired',   'Expired'),
        ('cancelled', 'Cancelled'),
        ('paused',    'Paused'),
    ]
    PLAN_CHOICES = [
        ('monthly', 'Monthly - ₹199'),
        ('yearly',  'Yearly  - ₹1,999'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    status           = models.CharField(max_length=12, choices=STATUS_CHOICES, default='trial')
    plan             = models.CharField(max_length=8,  choices=PLAN_CHOICES,  default='monthly', blank=True)
    razorpay_sub_id  = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_cust_id = models.CharField(max_length=100, blank=True)
    trial_ends_at    = models.DateTimeField(null=True, blank=True)
    paid_until       = models.DateTimeField(null=True, blank=True)
    cancelled_at     = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f'{self.user.email} | {self.status} | {self.plan}'

    @property
    def is_active(self):
        now = timezone.now()
        if self.status == 'active' and self.paid_until and self.paid_until > now:
            return True
        if self.status == 'trial' and self.trial_ends_at and self.trial_ends_at > now:
            return True
        return False

    @property
    def trial_days_left(self):
        if self.status != 'trial' or not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)

    @property
    def plan_price(self):
        return {'monthly': 199, 'yearly': 1999}.get(self.plan, 0)


class PaymentEvent(models.Model):
    """Logs every Razorpay webhook event for audit trail."""
    EVENT_TYPES = [
        ('subscription.activated', 'Activated'),
        ('subscription.charged',   'Charged'),
        ('subscription.cancelled', 'Cancelled'),
        ('subscription.expired',   'Expired'),
        ('subscription.halted',    'Halted'),
        ('payment.failed',         'Payment Failed'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription     = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='events')
    event_type       = models.CharField(max_length=50, choices=EVENT_TYPES)
    razorpay_event_id= models.CharField(max_length=100, unique=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payload          = models.JSONField(default=dict)
    processed_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_events'
        ordering = ['-processed_at']

    def __str__(self):
        return f'{self.event_type} | {self.processed_at}'
