from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid


class Expense(models.Model):
    """
    Single expense entry.
    Each user can have unlimited expenses.
    """
    CATEGORY_CHOICES = [
        ('Food',          'Food'),
        ('Transport',     'Transport'),
        ('Entertainment', 'Entertainment'),
        ('Learning',      'Learning'),
        ('Bills',         'Bills'),
        ('Shopping',      'Shopping'),
        ('Other',         'Other'),
    ]
    PAYMENT_CHOICES = [
        ('UPI',         'UPI'),
        ('Cash',        'Cash'),
        ('Card',        'Card'),
        ('Netbanking',  'Netbanking'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses')
    date        = models.DateField()
    description = models.CharField(max_length=255)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    amount      = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment     = models.CharField(max_length=15, choices=PAYMENT_CHOICES, default='UPI')
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = 'expenses'
        ordering  = ['-date', '-created_at']
        indexes   = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'date', 'category']),
        ]

    def __str__(self):
        return f'{self.user.email} | {self.date} | {self.category} | ₹{self.amount}'

    @property
    def row_flag(self):
        """Returns red/yellow/green flag for this row."""
        amt = float(self.amount)
        if amt > 1000:
            return 'red'
        if self.category == 'Entertainment' and amt > 200:
            return 'yellow'
        if self.category == 'Food' and amt > 400:
            return 'yellow'
        if self.category == 'Shopping' and amt > 500:
            return 'yellow'
        return 'green'
