from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from code_doc.models import Project, ProjectVersion

_project_permission_prefix = 'code_doc'

class CodedocPermissionBackend(object):
  """A class helping the management of per object permissions in the user land"""

  version_permission_map = {
    _project_permission_prefix + '.version_view' : 'has_user_view_permission',
    _project_permission_prefix + '.version_artifacts_view' : 'has_user_artifact_view_permission',}
  
  project_permission_map = {
    #_project_permission_prefix + '.project_view' : 'project_view',
    _project_permission_prefix + '.project_administrate' : 'has_project_administrate_permissions',}
  
  
  def _manage_permissions(self, user, perm, obj, permission_map):
    """Manages the permissions for a project version, per instance of ProjectVersion"""
    
    
    # the backend does not manage this kind of permissions
    if(not permission_map.has_key(perm.codename)):
      return False
    
    #assert(hasattr(obj, permission_map[perm.name]))
    func = getattr(obj, permission_map[perm.codename], None)
    assert(not func is None)
    
    if(func(user_obj)):
      return True
    
    # returning False will continue the iteration over the permission backends
    raise PermissionDenied
  
  def _populate_permissions(self,user, perm, obj, permission_map):
    return set()
  
  
  def _manage_project_permissions(self, user, perm, obj):
    """Manages the permissions of a specific project."""
  
  def has_perm(self, user_obj, perm, obj=None):
    if(obj is None):
      raise PermissionDenied
    
    if not user_obj.is_active:
      return False
    
    # manage the permission for a specific project version
    if(type(obj) is ProjectVersion):
      return self._manage_permissions(user_obj, perm, obj, version_permission_map)
      
      
      
    
    
    # manage the permission for a specific project
    if(type(obj) is Project):
      return self._manage_permissions(user_obj, perm, obj, project_permission_map)
    
    
    # we do not manage permission for other type of objects
    return False
  
  
  def get_all_permissions(self, user, obj):
    
    if(obj is None):
      return set()
    
    
    
    return set()