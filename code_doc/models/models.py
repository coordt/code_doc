from django.db import models
from django.core.urlresolvers import reverse

import datetime
import logging

logger = logging.getLogger(__name__)


class CopyrightHolder(models.Model):
    """The entity that holds the copyright over a product"""
    name = models.CharField(max_length=50)
    year = models.IntegerField(default=datetime.datetime.now().year)

    def __unicode__(self):
        return "%s (%d)" % (self.name, self.year)


class Copyright(models.Model):
    """The copyright type (BSD + version, MIT + version etc)"""
    name = models.CharField(max_length=50)
    content = models.TextField(max_length=2500)
    url = models.CharField(max_length=50)

    def __unicode__(self):
        return "%s @ %s" % (self.name, self.url)


class Topic(models.Model):
    """A topic associated to a project"""
    name = models.CharField(max_length=20)
    description_mk = models.TextField('Description in Markdown format',
                                      max_length=200, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('topic', kwargs={'topic_id': self.pk})

    def __unicode__(self):
        return "%s" % (self.name)


def manage_permission_on_object(userobj, user_permissions, group_permissions,
                                default=None):
    """If (in order)

    * userobj is a superuser, then true
    * userobj is not active, then default. If default is None, then True
    * no credentials set in the groups user_permissions / group_permissions,
      the default. If default is None, then True.
    * userobj in user_permissions, then True
    * userobj in one of the groups in group_permissions, the True
    * otherwise False

    """
    if userobj.is_superuser:
        return True

    if not userobj.is_active:
        return default if default is not None else True

    # no permission has been set, so no restriction by default
    if user_permissions.count() == 0 and group_permissions.count() == 0:
        return default if default is not None else True

    if user_permissions.filter(id=userobj.id).count() > 0:
        return True

    return group_permissions.filter(id__in=[g.id for g in userobj.groups.all()]).count() > 0
