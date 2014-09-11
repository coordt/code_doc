
from functools import wraps, partial

from django.conf import settings
from django.core.exceptions import PermissionDenied, DoesNotExist
from django.utils.decorators import available_attrs

from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.utils.six.moves.urllib.parse import urlparse


def _user_passes_test_with_object_getter(test_func, object_getter, login_url=None, raise_exception = False, redirect_field_name=REDIRECT_FIELD_NAME):
  """
  Decorator for views that checks that the user passes the given test,
  redirecting to the log-in page if necessary. The test should be a callable
  that takes the user object and returns True if the user passes.
  """
  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      
      obj = object_getter(**kwargs)
      
      if obj is None and raise_exception:
        raise DoesNotExist
      
      if not obj is None:
        if test_func(request.user, obj):
          return view_func(request, *args, **kwargs)
      
      
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



def permission_required_on_object(perm, object_getter, login_url=None, raise_exception=False):
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
      return True
  
    # In case the 403 handler should be called raise the exception
    if raise_exception:
      raise PermissionDenied
    # As the last resort, show the login form
    return False
  
  return _user_passes_test_with_object_getter(check_perms, object_getter, raise_exception)