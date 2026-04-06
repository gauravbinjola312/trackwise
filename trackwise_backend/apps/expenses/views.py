"""
Expense Views

GET    /api/v1/expenses/              List (paginated, filterable, searchable)
POST   /api/v1/expenses/              Create one
GET    /api/v1/expenses/{id}/         Get one
PUT    /api/v1/expenses/{id}/         Replace one
PATCH  /api/v1/expenses/{id}/         Partial update
DELETE /api/v1/expenses/{id}/         Delete one
POST   /api/v1/expenses/bulk-create/  Create many at once
GET    /api/v1/expenses/summary/      30-day stats + category breakdown
DELETE /api/v1/expenses/bulk-delete/  Delete multiple by IDs
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFilter, CharFilter, NumberFilter
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Expense
from .serializers import ExpenseSerializer, ExpenseListSerializer, ExpenseBulkSerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin, UserOwnedQuerysetMixin


class ExpenseFilter(FilterSet):
    """
    Filter expenses by:
    - date_from, date_to   (date range)
    - category             (exact)
    - payment              (exact)
    - min_amount, max_amount
    - search               (description keyword)
    """
    date_from  = DateFilter(field_name='date', lookup_expr='gte')
    date_to    = DateFilter(field_name='date', lookup_expr='lte')
    min_amount = NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = NumberFilter(field_name='amount', lookup_expr='lte')

    class Meta:
        model  = Expense
        fields = ['category', 'payment', 'date_from', 'date_to', 'min_amount', 'max_amount']


class ExpenseViewSet(SuccessResponseMixin, UserOwnedQuerysetMixin, viewsets.ModelViewSet):
    """
    Full CRUD for expenses.
    All endpoints require Bearer token.
    All queries are scoped to the requesting user.
    """
    queryset         = Expense.objects.all()
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = ExpenseFilter
    search_fields    = ['description', 'notes']
    ordering_fields  = ['date', 'amount', 'category', 'created_at']
    ordering         = ['-date', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseListSerializer
        return ExpenseSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/expenses/
        Query params: ?page=1&page_size=25&category=Food&date_from=2024-01-01&date_to=2024-01-31
        """
        queryset   = self.filter_queryset(self.get_queryset())
        page       = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return self.success(serializer.data)

    def create(self, request, *args, **kwargs):
        """POST /api/v1/expenses/"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.created(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(serializer.data, 'Updated successfully')

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return self.deleted()

    @action(detail=False, methods=['POST'], url_path='bulk-create')
    def bulk_create(self, request):
        """
        POST /api/v1/expenses/bulk-create/
        Body: [{ date, description, category, amount, payment, notes }, ...]
        Efficiently creates many expenses in one DB call.
        """
        serializer = ExpenseBulkSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        expenses = [Expense(**item, user=request.user) for item in serializer.validated_data]
        created  = Expense.objects.bulk_create(expenses)
        return self.created({'created_count': len(created)}, f'{len(created)} expenses created.')

    @action(detail=False, methods=['DELETE'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        DELETE /api/v1/expenses/bulk-delete/
        Body: { "ids": ["uuid1", "uuid2"] }
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'success': False, 'error': {'message': 'ids list is required.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        deleted_count, _ = Expense.objects.filter(user=request.user, id__in=ids).delete()
        return self.success({'deleted_count': deleted_count})

    @action(detail=False, methods=['GET'], url_path='summary')
    def summary(self, request):
        """
        GET /api/v1/expenses/summary/?days=30

        Returns:
        - total amount
        - count
        - category breakdown (amount + percentage)
        - daily average
        - highest single expense
        - row flag counts (red/yellow/green)
        """
        days     = int(request.query_params.get('days', 30))
        from_dt  = date.today() - timedelta(days=days)
        expenses = self.get_queryset().filter(date__gte=from_dt)

        total    = expenses.aggregate(total=Sum('amount'), count=Count('id'))
        total_amt= float(total['total'] or 0)
        count    = total['count'] or 0

        # Category breakdown
        by_cat = expenses.values('category').annotate(
            amount=Sum('amount'), count=Count('id')
        ).order_by('-amount')

        categories = []
        for row in by_cat:
            amt = float(row['amount'] or 0)
            categories.append({
                'category':   row['category'],
                'amount':     amt,
                'count':      row['count'],
                'percentage': round((amt / total_amt * 100) if total_amt else 0, 1),
            })

        # Flag counts
        flag_counts = {'red': 0, 'yellow': 0, 'green': 0}
        for exp in expenses:
            flag_counts[exp.row_flag] += 1

        return self.success({
            'period_days':   days,
            'total_amount':  total_amt,
            'total_count':   count,
            'daily_average': round(total_amt / days, 2) if days else 0,
            'categories':    categories,
            'flag_counts':   flag_counts,
        })
