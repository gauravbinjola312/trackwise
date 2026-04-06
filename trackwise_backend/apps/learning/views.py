"""
Learning Session Views

GET    /api/v1/learning/              List all sessions (filtered, paginated)
POST   /api/v1/learning/              Create session
GET    /api/v1/learning/{id}/         Get single session
PATCH  /api/v1/learning/{id}/         Update session
DELETE /api/v1/learning/{id}/         Delete session
GET    /api/v1/learning/summary/      Stats: total hours, week hours, heatmap
GET    /api/v1/learning/heatmap/      14-day activity grid
"""
from datetime import date, timedelta
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFilter, CharFilter
from rest_framework import viewsets, filters
from rest_framework.decorators import action

from .models import LearningSession
from .serializers import LearningSessionSerializer, LearningSessionListSerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin, UserOwnedQuerysetMixin


class LearningFilter(FilterSet):
    date_from = DateFilter(field_name='date', lookup_expr='gte')
    date_to   = DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model  = LearningSession
        fields = ['status', 'source', 'date_from', 'date_to']


class LearningViewSet(SuccessResponseMixin, UserOwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset        = LearningSession.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LearningFilter
    search_fields   = ['topic', 'notes']
    ordering_fields = ['date', 'hours', 'created_at']
    ordering        = ['-date', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LearningSessionListSerializer
        return LearningSessionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.created(serializer.data)

    def update(self, request, *args, **kwargs):
        partial    = kwargs.pop('partial', False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(serializer.data, 'Updated successfully')

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return self.deleted()

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """
        GET /api/v1/learning/summary/?days=30
        Returns aggregate stats for the period.
        """
        days    = int(request.query_params.get('days', 30))
        from_dt = date.today() - timedelta(days=days)
        qs      = self.get_queryset()

        period_sessions = qs.filter(date__gte=from_dt)
        week_sessions   = qs.filter(date__gte=date.today() - timedelta(days=7))
        all_sessions    = qs

        total_hours  = float(all_sessions.aggregate(t=Sum('hours'))['t'] or 0)
        period_hours = float(period_sessions.aggregate(t=Sum('hours'))['t'] or 0)
        week_hours   = float(week_sessions.aggregate(t=Sum('hours'))['t'] or 0)
        completed    = all_sessions.filter(status='Completed').count()

        # Last session date
        last = all_sessions.order_by('-date').first()
        last_date = str(last.date) if last else None
        days_since_last = (date.today() - last.date).days if last else None

        # Source breakdown
        by_source = period_sessions.values('source').annotate(
            hours=Sum('hours'), count=Count('id')
        ).order_by('-hours')

        return self.success({
            'period_days':    days,
            'total_hours':    round(total_hours, 1),
            'period_hours':   round(period_hours, 1),
            'week_hours':     round(week_hours, 1),
            'completed':      completed,
            'last_date':      last_date,
            'days_since_last':days_since_last,
            'by_source':      list(by_source),
        })

    @action(detail=False, methods=['GET'])
    def heatmap(self, request):
        """
        GET /api/v1/learning/heatmap/?days=14
        Returns a list of { date, hours } for the last N days.
        Used to render the activity heatmap in the mobile app.
        """
        days    = int(request.query_params.get('days', 14))
        from_dt = date.today() - timedelta(days=days - 1)

        sessions = self.get_queryset().filter(date__gte=from_dt).values('date').annotate(
            hours=Sum('hours')
        )
        hours_by_date = {str(s['date']): float(s['hours']) for s in sessions}

        cells = []
        for i in range(days):
            d    = from_dt + timedelta(days=i)
            ds   = str(d)
            hrs  = hours_by_date.get(ds, 0)
            cells.append({
                'date':  ds,
                'hours': hrs,
                'level': 2 if hrs >= 2 else 1 if hrs > 0 else 0,
            })

        return self.success({'days': days, 'cells': cells})
