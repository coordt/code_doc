from django.db.models.signals import pre_save
from django.dispatch import receiver

from ..models.projects import ProjectRepository


@receiver(pre_save, sender=ProjectRepository)
def repository_cleanup_url(sender, instance, **kwargs):
    """Cleans up the URL of the repository prior to saving"""
    instance.code_source_url = instance.code_source_url.strip()
