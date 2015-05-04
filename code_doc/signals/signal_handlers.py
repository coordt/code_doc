from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from django.conf import settings

from code_doc.models import Author, Revision

import logging
# logger for this file
logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def linkToAuthor(sender, **kwargs):
    """Checks if a User is already linked to an Author.
       If not, then a new Author is created and the User's
       information is copied over to the Author. """
    user_instance = kwargs['instance']

    if not hasattr(user_instance, 'author'):
        linked_author = Author(lastname=user_instance.last_name,
                               firstname=user_instance.first_name,
                               email=user_instance.email,
                               django_user=user_instance)
        linked_author.save()
        user_instance.author = linked_author


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def deleting(sender, **kwargs):
    logger.debug('Deleting a user')


@receiver(post_save, sender=Revision)
def check_revision_count_and_delete(sender, **kwargs):
    """ Checks if there are to many revisions.
        If not, we dont have to do anything.
        If yes, we have to delete the least recent revision of the branch this
        new revision belongs to.
    """
    revision_instance = kwargs['instance']

    revisions_for_branch = Revision.objects.filter(branch=revision_instance.branch)

    # @todo(Stephan): Put this into the settings
    NUMBER_OF_REVISIONS_KEPT_FOR_BRANCH = 5

    if (revisions_for_branch.count() > NUMBER_OF_REVISIONS_KEPT_FOR_BRANCH):
        revision_to_delete = revisions_for_branch.earliest()
        # @todo(Stephan): Delete the earliest revision here
        revision_to_delete.delete()


@receiver(pre_delete, sender=Revision)
def delete_corresponding_artifacts(sender, **kwargs):
    """ Deletes all the artifacts, that belong to this revision"""
    revision_instance = kwargs['instance']

    for artifact in revision_instance.artifacts.all():
        # The proper deletion should be handled by the signal defined in models.py

        # @todo(Stephan): delete the artifacts here
        artifact.delete()
