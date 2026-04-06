"""
Savings Views

GET    /api/v1/savings/            List entries (paginated, filtered)
POST   /api/v1/savings/            Create entry
GET    /api/v1/savings/{id}/       Get single entry
PATCH  /api/v1/savings/{id}/       Update entry
DELETE /api/v1/savings/{id}/       Delete entry
GET    /api/v1/savings/summary/    30-day stats + savings rate + type breakdown
"""
from datetime import date, timedelta
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFilter
from rest_framework import viewsets, filters
from rest_framework.decorators import action

from .models import SavingEntry
from .serializers import SavingEntrySerializer, SavingEntryListSerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin, UserOwnedQuerysetMixin


class SavingFilter(FilterSet):
    date_from = DateFilter(field_name='date', lookup_expr='gte')
    date_to   = DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model  = SavingEntry
        fields = ['inv_type', 'date_from', 'date_to']


class SavingViewSet(SuccessResponseMixin, UserOwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset        = SavingEntry.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SavingFilter
    search_fields   = ['name', 'platform', 'notes']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering        = ['-date', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SavingEntryListSerializer
        return SavingEntrySerializer

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
        return self.success(serializer.data, 'Updated')

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return self.deleted()

    def list(self, request, *args, **kwargs):
        queryset   = self.filter_queryset(self.get_queryset())
        page       = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return self.success(serializer.data)

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        days    = int(request.query_params.get('days', 30))
        from_dt = date.today() - timedelta(days=days)
        qs      = self.get_queryset()

        period_entries = qs.filter(date__gte=from_dt)
        all_entries    = qs

        period_total = float(period_entries.aggregate(t=Sum('amount'))['t'] or 0)
        all_time     = float(all_entries.aggregate(t=Sum('amount'))['t'] or 0)

        # Savings rate (from most recent entry with income)
        with_income = period_entries.filter(monthly_income__gt=0).order_by('-date').first()
        income      = float(with_income.monthly_income) if with_income else 0
        rate_pct    = round(period_total / income * 100, 1) if income else None

        # Type breakdown
        by_type = period_entries.values('inv_type').annotate(
            amount=Sum('amount'), count=Count('id')
        ).order_by('-amount')

        unique_types = all_entries.values_list('inv_type', flat=True).distinct().count()

        return self.success({
            'period_days':   days,
            'period_total':  period_total,
            'all_time_total':all_time,
            'monthly_income':income,
            'savings_rate':  rate_pct,
            'unique_types':  unique_types,
            'by_type': [
                {
                    'type':       row['inv_type'],
                    'amount':     float(row['amount']),
                    'count':      row['count'],
                    'percentage': round(float(row['amount']) / period_total * 100, 1) if period_total else 0,
                }
                for row in by_type
            ],
        })
