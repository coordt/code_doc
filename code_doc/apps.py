from django.apps import AppConfig


class CodeDocAppConfig(AppConfig):

    name = "code_doc"
    verbose_name = "Code Doc"

    def ready(self):
        from .signals import signal_handlers  # NOQA
        from .signals import project_handlers  # NOQA
