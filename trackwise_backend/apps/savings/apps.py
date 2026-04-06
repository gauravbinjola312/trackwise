from django.apps import AppConfig

class SavingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'trackwise_backend.apps.savings'
    label              = 'savings'
    verbose_name       = 'Savings'
