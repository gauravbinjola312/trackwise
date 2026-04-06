from django.contrib import admin
from .models import Goal

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display  = ['user', 'name', 'category', 'target', 'current', 'pct_complete', 'deadline', 'status']
    list_filter   = ['category', 'deadline']
    search_fields = ['name', 'user__email']
    ordering      = ['deadline']
    readonly_fields = ['id', 'pct_complete', 'days_left', 'status', 'daily_required', 'created_at', 'updated_at']
    list_select_related = ['user']
