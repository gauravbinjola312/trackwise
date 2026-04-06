from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'trackwise_backend.apps.accounts'
    label              = 'accounts'
    verbose_name       = 'Accounts'
