from django.apps import AppConfig

class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'trackwise_backend.apps.goals'
    label              = 'goals'
    verbose_name       = 'Goals'
