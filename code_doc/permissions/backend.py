from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from code_doc.models import Project, ProjectSeries

_project_permission_prefix = 'code_doc'


# logger for this file
import logging
logger = logging.getLogger(__name__)


def get_permission_handler_name(permission_name):
  return 'has_user_%s_permission' % permission_name


class CodedocPermissionBackend(object):
  """A class helping the management of per object permissions in the user land"""

  objects_permission_handlers = {}

  def authenticate(self, **credentials):
    """Does not manage any authentication"""
    return None

  def _manage_has_permissions(self, user, perm, obj):
    """Manages the permissions for a specific type of object"""


    # the backend does not manage these permissions on this kind of object
    if(not self.objects_permission_handlers.has_key(type(obj))):
      return False
    if(not perm in self.objects_permission_handlers[type(obj)]):
      return False

    func = getattr(obj, get_permission_handler_name(perm.split('.')[1]))
    assert(not func is None)

    if(func(user)):
      return True

    # returning False will continue the iteration over the permission backends
    return False
    #raise PermissionDenied

  def _populate_permissions(self, user, obj):

    if(not self.objects_permission_handlers.has_key(type(obj))):
      return set()

    return set(codename for codename in self.objects_permission_handlers[type(obj)] if self._manage_has_permissions(user, codename, obj))



  def has_perm(self, user_obj, perm, obj=None):
    if(obj is None):
      return False

    # This is delegated to the object itself, otherwise anonymous users won't get access to public objects
    #if not user_obj.is_active:
    #  print "User not active"
    #  return False

    # manage the permission for an object that is handled by this backend
    return self._manage_has_permissions(user_obj, perm, obj)



  def get_all_permissions(self, user, obj):

    if(obj is None):
      return set()

    return self._populate_permissions(user, obj)


def create_tables():
  """Populates the tables of CodedocPermissionBackend"""


  from django.apps import apps
  from django.db import models
  config = apps.get_app_config(_project_permission_prefix)

  for cls in (m for m in config.get_models(include_auto_created=False) if issubclass(m, models.Model)):
    handler_dict = CodedocPermissionBackend.objects_permission_handlers
    if(hasattr(cls, '_meta') and hasattr(cls._meta, 'permissions')):
      for permission_name, _ in cls._meta.permissions:
        handler_function = get_permission_handler_name(permission_name)
        if(hasattr(cls, handler_function)):
          if(not handler_dict.has_key(cls)):
            handler_dict[cls] = []
          handler_dict[cls].append(_project_permission_prefix + '.' + permission_name)

        else:
          logger.warning('[permissions][backend] "%s" does not handle object permission "%s"', cls, permission_name)


  pass


create_tables()
