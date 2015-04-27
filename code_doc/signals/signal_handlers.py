from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from django.contrib.auth.models import User


import logging
# logger for this file
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def registerAuthor(sender, **kwargs):
    logger.debug('Saving new user')


@receiver(pre_save, sender=User)
def registerAuthor2(sender, **kwargs):
    pass


@receiver(pre_delete, sender=User)
def deleting(sender, **kwargs):
    logger.debug('Deleting a user')
