import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class LearningSession(models.Model):
    SOURCE_CHOICES = [
        ('Online Course',   'Online Course'),
        ('YouTube',         'YouTube'),
        ('Book',            'Book'),
        ('Podcast',         'Podcast'),
        ('Documentation',   'Documentation'),
        ('Mentor',          'Mentor'),
        ('Other',           'Other'),
    ]
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Completed',   'Completed'),
        ('On Hold',     'On Hold'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_sessions')
    date       = models.DateField()
    topic      = models.CharField(max_length=255)
    source     = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Online Course')
    hours      = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(0.1)])
    status     = models.CharField(max_length=15, choices=STATUS_CHOICES, default='In Progress')
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'learning_sessions'
        ordering = ['-date', '-created_at']
        indexes  = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.user.email} | {self.date} | {self.topic} | {self.hours}h'

    @property
    def row_flag(self):
        from datetime import date
        days_old = (date.today() - self.date).days
        if self.status == 'Completed':
            return 'green'
        if self.status == 'On Hold':
            return 'yellow'
        if self.status == 'In Progress' and days_old > 7:
            return 'yellow'
        return 'none'
