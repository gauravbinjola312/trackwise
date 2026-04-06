from django.contrib import admin
from .models import LearningSession

@admin.register(LearningSession)
class LearningAdmin(admin.ModelAdmin):
    list_display  = ['user', 'date', 'topic', 'source', 'hours', 'status']
    list_filter   = ['status', 'source', 'date']
    search_fields = ['topic', 'user__email']
    ordering      = ['-date']
    date_hierarchy = 'date'
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_select_related = ['user']
