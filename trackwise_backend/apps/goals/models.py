import uuid
from datetime import date
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Goal(models.Model):
    CATEGORY_CHOICES = [
        ('Finance',   'Finance'),
        ('Learning',  'Learning'),
        ('Skill',     'Skill'),
        ('Career',    'Career'),
        ('Personal',  'Personal'),
        ('Travel',    'Travel'),
        ('Business',  'Business'),
    ]

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    name     = models.CharField(max_length=255)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='Finance')
    target   = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)])
    current  = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    deadline = models.DateField()
    notes    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'goals'
        ordering = ['deadline', '-created_at']
        indexes  = [
            models.Index(fields=['user', 'deadline']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f'{self.user.email} | {self.name} | {self.pct_complete}%'

    @property
    def pct_complete(self):
        if not self.target:
            return 0
        return min(100, round(float(self.current) / float(self.target) * 100, 1))

    @property
    def days_left(self):
        return (self.deadline - date.today()).days

    @property
    def is_overdue(self):
        return self.days_left < 0

    @property
    def daily_required(self):
        """How much progress needed per day to hit deadline."""
        remaining = float(self.target) - float(self.current)
        dl = self.days_left
        if dl <= 0 or remaining <= 0:
            return 0
        return round(remaining / dl, 2)

    @property
    def status(self):
        pct = self.pct_complete
        dl  = self.days_left
        if self.is_overdue:
            return 'overdue'
        if dl < 30 and pct < 70:
            return 'at_risk'
        if dl < 60 and pct < 50:
            return 'behind'
        if pct >= 80:
            return 'almost_done'
        return 'on_track'
