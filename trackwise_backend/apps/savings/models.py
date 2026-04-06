import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class SavingEntry(models.Model):
    TYPE_CHOICES = [
        ('SIP',             'SIP'),
        ('FD',              'Fixed Deposit'),
        ('PPF',             'PPF'),
        ('Stocks',          'Stocks'),
        ('Gold',            'Gold'),
        ('Crypto',          'Crypto'),
        ('RD',              'Recurring Deposit'),
        ('Savings Account', 'Savings Account'),
        ('NPS',             'NPS'),
        ('Other',           'Other'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings')
    date           = models.DateField()
    name           = models.CharField(max_length=255)
    inv_type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default='SIP', db_column='type')
    amount         = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    monthly_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    platform       = models.CharField(max_length=100, blank=True)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = 'savings'
        ordering  = ['-date', '-created_at']
        indexes   = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'inv_type']),
        ]

    def __str__(self):
        return f'{self.user.email} | {self.date} | {self.inv_type} | ₹{self.amount}'

    @property
    def row_flag(self):
        amt    = float(self.amount)
        income = float(self.monthly_income)
        if amt >= 5000:
            return 'green'
        if income > 0 and amt < income * 0.1:
            return 'yellow'
        return 'none'

    @property
    def savings_rate_pct(self):
        if not self.monthly_income:
            return None
        return round(float(self.amount) / float(self.monthly_income) * 100, 1)
