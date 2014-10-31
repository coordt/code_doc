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
  
  
  def authenticate(self, **credentials):
    """Does not manage any authentication"""
    return None
  
  def _manage_has_permissions(self, user, perm, obj, permission_map):
    """Manages the permissions for a specific type of object"""
    
    # the backend does not manage this kind of permissions
    if(not permission_map.has_key(perm)):
      return False
    
    func = getattr(obj, permission_map[perm], None)
    assert(not func is None)
    
    if(func(user)):
      return True
    
    # returning False will continue the iteration over the permission backends
    return False
    #raise PermissionDenied
  
  def _populate_permissions(self, user, obj, permission_map):
    
    permission_set = set()
    
    for codename, object_attribute in permission_map.items():
      
      func = getattr(obj, object_attribute, None)
      if func is None:
        continue
    
      if(func(user)):
        permission_set.add(codename)
        
    return permission_set
  
  
  
  def has_perm(self, user_obj, perm, obj=None):
    if(obj is None):
      return False
    
    # This is delegated to the object itself, otherwise anonymous users won't get access to public objects
    #if not user_obj.is_active:
    #  print "User not active"
    #  return False
    
    # manage the permission for a specific project version
    if(type(obj) is ProjectVersion):
      return self._manage_has_permissions(user_obj, perm, obj, self.version_permission_map)
    
    # manage the permission for a specific project
    if(type(obj) is Project):
      return self._manage_has_permissions(user_obj, perm, obj, self.project_permission_map)
    
    
    # we do not manage permission for other type of objects
    return False
  
  
  def get_all_permissions(self, user, obj):
    
    if(obj is None):
      return set()
    
    permissions = set()
    for map_perms in [self.version_permission_map, self.project_permission_map]:
      permissions.update(self._populate_permissions(user, obj, map_perms))
    
    return permissions