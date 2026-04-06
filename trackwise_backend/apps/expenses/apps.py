from django.apps import AppConfig

class ExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'trackwise_backend.apps.expenses'
    label              = 'expenses'
    verbose_name       = 'Expenses'
