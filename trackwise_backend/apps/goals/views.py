"""
Goal Views

GET    /api/v1/goals/                  List all goals
POST   /api/v1/goals/                  Create goal
GET    /api/v1/goals/{id}/             Get single goal
PUT    /api/v1/goals/{id}/             Full update
PATCH  /api/v1/goals/{id}/             Partial update
DELETE /api/v1/goals/{id}/             Delete goal
PATCH  /api/v1/goals/{id}/progress/   Quick progress update
GET    /api/v1/goals/summary/          Overview stats
"""
from django.db.models import Avg, Count
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Goal
from .serializers import GoalSerializer, GoalProgressSerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin, UserOwnedQuerysetMixin


class GoalFilter(FilterSet):
    class Meta:
        model  = Goal
        fields = ['category']


class GoalViewSet(SuccessResponseMixin, UserOwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset        = Goal.objects.all()
    serializer_class = GoalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = GoalFilter
    search_fields   = ['name', 'notes']
    ordering_fields = ['deadline', 'created_at']
    ordering        = ['deadline']

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
        return self.success(serializer.data, 'Goal updated')

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return self.deleted()

    @action(detail=True, methods=['PATCH'], url_path='progress')
    def progress(self, request, pk=None):
        """
        PATCH /api/v1/goals/{id}/progress/
        Body: { "current": 75000 }
        Quick shortcut to update progress without sending all fields.
        """
        goal       = self.get_object()
        serializer = GoalProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_current = serializer.validated_data['current']
        if float(new_current) > float(goal.target):
            return Response({'success': False, 'error': {'message': 'Progress cannot exceed target.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        goal.current = new_current
        goal.save(update_fields=['current', 'updated_at'])
        return self.success(GoalSerializer(goal).data, 'Progress updated')

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """
        GET /api/v1/goals/summary/
        Returns an overview of all goals with status counts.
        """
        goals = self.get_queryset()
        total = goals.count()

        status_counts = {'overdue': 0, 'at_risk': 0, 'behind': 0, 'almost_done': 0, 'on_track': 0}
        total_pct     = 0
        for g in goals:
            status_counts[g.status] += 1
            total_pct += g.pct_complete

        avg_pct = round(total_pct / total, 1) if total else 0

        return self.success({
            'total':          total,
            'average_pct':    avg_pct,
            'status_counts':  status_counts,
            'goals':          GoalSerializer(goals, many=True).data,
        })
