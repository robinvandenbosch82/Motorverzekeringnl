from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Wire up image post-processing on upload (variant pre-warm + compress).
        from core import signals
        signals.register()
