
from django.http import HttpResponse

from django.views.generic.detail import SingleObjectMixin

import logging

from ..permissions.decorators import permission_required_on_object


class PermissionOnObjectViewMixin(SingleObjectMixin):
    """Manages the permissions for the object given by model"""

    # the required permissions on the object
    permissions_on_object = None
    # the method returning an object on which the permissions will be tested
    permissions_object_getter = None
    # permission overriding function (not implemented)
    permissions_manager = None

    def handle_access_error(self, obj):
        """Default access error handler. This one returns a 401 error instead of the 403 error"""
        logging.warn('** access error for object %s **', obj)
        return HttpResponse('Unauthorized', status=401)

    def dispatch(self, request, *args, **kwargs):

        # we read the field "permissions_on_object" on the instance, which indicates the
        # permissions for accessing the view
        object_permissions = getattr(self, 'permissions_on_object', None)

        # we read the field "permissions_object_getter" on the instance, which tells us
        # how to get the instance of the object on which the permissions will be tested
        object_permissions_getter = getattr(self, 'permissions_object_getter', None)
        if(object_permissions_getter is None):
            object_permissions_getter = self.get_object
        else:
            object_permissions_getter = getattr(self, object_permissions_getter, None)

        # this modifies the dispatch of the parent through the decorator, and calls it with the same parameters
        dispatch_to_wrap = super(PermissionOnObjectViewMixin, self).dispatch
        decorator = permission_required_on_object(object_permissions,
                                                  object_permissions_getter,
                                                  handle_access_error=self.handle_access_error)

        return decorator(dispatch_to_wrap)(request, *args, **kwargs)

    # we do not need to reimplement this behaviour as it is properly done in the decorator
