from django.apps import AppConfig


class CodeDocAppConfig(AppConfig):

    name = 'code_doc'
    verbose_name = 'Code Doc'

    def ready(self):
        import code_doc.signals.signal_handlers
        import code_doc.signals.project_handlers

