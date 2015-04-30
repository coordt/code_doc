from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from django.conf import settings

from code_doc.models import Author

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
