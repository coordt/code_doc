from django.db import models

# from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.conf import settings

import os
import logging

logger = logging.getLogger(__name__)


def get_author_image_location(instance, filename):

    if (instance.firstname is not "") and (instance.lastname is not ""):
        author_name = instance.firstname + instance.lastname
    else:
        author_name = 'default'

    media_relative_dir = os.path.join('author_images',
                                      author_name)

    root_dir = os.path.join(settings.MEDIA_ROOT, media_relative_dir)

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    return os.path.join(media_relative_dir, filename)


class Author(models.Model):
    """An author, may appear in several projects, and is not someone that is
    allowed to login (not a user of Django)."""
    lastname = models.CharField(max_length=50)
    firstname = models.CharField(max_length=50)
    gravatar_email = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=50,
                              unique=True,
                              db_index=True)
    home_page_url = models.CharField(max_length=250, blank=True)
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                       related_name='author',
                                       blank=True,
                                       null=True,
                                       help_text='The Django User, this Author is corresponding to.')
    image = models.ImageField(blank=True, null=True, upload_to=get_author_image_location)

    class Meta:
        permissions = (
            ("author_edit", "Can edit the Author's details"),
        )

    def __unicode__(self):
        return "%s %s (%s)" % (self.firstname, self.lastname, self.email)

    def has_user_author_edit_permission(self, user):
        """In order for a Django User to be allowed to edit the details of an Author,
           he has to be a superuser or be the User, this Author is linked to.
        """
        return user.is_superuser or (hasattr(user, 'author') and (user.author == self))

    def get_absolute_url(self):
        return reverse('author', kwargs={'author_id': self.pk})
