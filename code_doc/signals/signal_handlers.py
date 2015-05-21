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
       information is copied over to the Author.
    """
    def user_is_linkable_to_author(user):
        """A user must provide enough information in order to be linkable to an Author."""
        return not (user.last_name == "" or
                    user.first_name == "" or
                    user.email == "")

    user_instance = kwargs['instance']

    # @todo(Stephan): How do we check if an Author is already present?
    #                 - Check for firstname + lastname?
    #                 - Update email if a different one is given by the User?

    if not hasattr(user_instance, 'author'):
        if user_is_linkable_to_author(user_instance):
            linked_author = Author.objects.create(
                                   lastname=user_instance.last_name,
                                   firstname=user_instance.first_name,
                                   email=user_instance.email,
                                   django_user=user_instance)
            user_instance.author = linked_author
            user_instance.save()


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def deleting(sender, **kwargs):
    logger.debug('Deleting a user')
