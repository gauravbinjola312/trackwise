from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ['user', 'date', 'description', 'category', 'amount', 'payment']
    list_filter   = ['category', 'payment', 'date']
    search_fields = ['description', 'user__email']
    ordering      = ['-date']
    date_hierarchy = 'date'
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_select_related = ['user']
