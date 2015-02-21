
from functools import wraps, partial
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.decorators import available_attrs
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.utils.six.moves.urllib.parse import urlparse

logger = logging.getLogger(__name__)

def _user_passes_test_with_object_getter(
         test_func, 
         object_getter, 
         login_url = None, 
         handle_access_error = None,
         raise_exception = False, 
         redirect_field_name=REDIRECT_FIELD_NAME):
  """
  Decorator for views that checks that the user passes the given test,
  redirecting to the log-in page if necessary. The test should be a callable
  that takes the user object and returns True if the user passes.
  """
  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      
      obj = object_getter(request, *args, **kwargs)

      if obj is None and not handle_access_error is None:
        logger.debug('[permissions][decorator] object not found and handling access error')
        return handle_access_error(obj)
      
      if obj is None and raise_exception:
        logger.debug('[permissions][decorator] object not found but PermissionDenied raised')
        raise PermissionDenied
      
      if not obj is None:
        logger.debug('[permissions][decorator] checking permissions')
        if test_func(request.user, obj):
          logger.debug('[permissions][decorator] checking permissions -- passed')
          return view_func(request, *args, **kwargs)
      
      logger.debug('[permissions][decorator] checking permissions -- failed')
      
      # if the user is already authenticated, there is no need to redirect him to the login page
      if(request.user.is_authenticated() and not handle_access_error is None):
        return handle_access_error(obj)
      
      if(request.user.is_authenticated()):# and raise_exception:
        raise PermissionDenied
      
      path = request.build_absolute_uri()
    
      # urlparse chokes on lazy objects in Python 3, force to str
      resolved_login_url = force_str(resolve_url(login_url or settings.LOGIN_URL))
    
      # If the login url is the same scheme and net location then just
      # use the path as the "next" url.
      login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
      current_scheme, current_netloc = urlparse(path)[:2]
      if ((not login_scheme or login_scheme == current_scheme) and
          (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()
      from django.contrib.auth.views import redirect_to_login
      return redirect_to_login(path, resolved_login_url, redirect_field_name)
    return _wrapped_view
  
  return decorator



def permission_required_on_object(
      perm, 
      object_getter, 
      login_url=None,
      handle_access_error = None, 
      raise_exception = False):
  """
  Decorator for views that checks whether a user has a particular permission
  enabled, redirecting to the log-in page if necessary.
  If the raise_exception parameter is given the PermissionDenied exception
  is raised.
  """
  def check_perms(user, obj):
    if not isinstance(perm, (list, tuple)):
      perms = (perm, )
    else:
      perms = perm
    
    # First check if the user has the permission (even anon users)
    if user.has_perms(perms, obj):
      logger.debug('[permissions][check] User %s ** has ** permissions %s', user, perms)
      return True

    logger.debug('[permissions][check] User %s ** has not ** permissions %s', user, perms)
  
    # In case the 403 handler should be called raise the exception
    #if raise_exception:
    #  raise PermissionDenied
    # this is done by the _user_passes_test_with_object_getter
    
    # As the last resort, show the login form
    return False
  
  return _user_passes_test_with_object_getter(
              check_perms, 
              object_getter, 
              login_url, 
              handle_access_error = handle_access_error, 
              raise_exception = raise_exception)