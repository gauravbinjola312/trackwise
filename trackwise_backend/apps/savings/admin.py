from django.contrib import admin
from .models import SavingEntry

@admin.register(SavingEntry)
class SavingAdmin(admin.ModelAdmin):
    list_display  = ['user', 'date', 'name', 'inv_type', 'amount', 'monthly_income', 'platform']
    list_filter   = ['inv_type', 'date']
    search_fields = ['name', 'user__email', 'platform']
    ordering      = ['-date']
    date_hierarchy = 'date'
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_select_related = ['user']
