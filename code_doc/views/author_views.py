
from django.shortcuts import render
from django.http import Http404

from django.views.generic.edit import UpdateView
from django.views.generic import ListView, View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator


import logging

from ..models import Project, Author
from ..forms.forms import AuthorForm
from .permission_helpers import PermissionOnObjectViewMixin

# logger for this file
logger = logging.getLogger(__name__)


class AuthorListView(ListView):
    """A generic view of the authors in a list"""
    paginate_by = 10
    template_name = "code_doc/authors/author_list.html"
    context_object_name = "authors"
    model = Author


def detail_author(request, author_id):
    try:
        author = Author.objects.get(pk=author_id)
    except Author.DoesNotExist:
        raise Http404

    project_list = Project.objects.filter(authors=author)
    coauthor_list = Author.objects.filter(project__in=project_list).distinct().exclude(pk=author_id)

    return render(request,
                  'code_doc/authors/author_details.html',
                  {'project_list': project_list,
                   'author': author,
                   'user': request.user,
                   'coauthor_list': coauthor_list})


class AuthorUpdateView(PermissionOnObjectViewMixin, UpdateView):
    """View for editing information about an Author

      .. note:: in order to be able to edit an Author, the user should have the
                'code_doc.author_edit' permission on the Author object.
    """

    form_class = AuthorForm
    model = Author

    permissions_on_object = ('code_doc.author_edit',)
    permissions_object_getter = 'get_author_from_request'

    template_name = "code_doc/authors/author_edit.html"

    pk_url_kwarg = 'author_id'

    def get_author_from_request(self, request, *args, **kwargs):
        # TODO check if needed
        try:
            return Author.objects.get(pk=kwargs['author_id'])
        except Author.DoesNotExist:
            logger.warning('[AuthorUpdateView] non existent Author with id %s',
                           kwargs['author_id'])
            return None


class MaintainerProfileView(View):
    """Manages the views associated to the maintainers"""

    @method_decorator(login_required)
    def get(self, request, maintainer_id):
        try:
            maintainer = User.objects.get(pk=maintainer_id)
        except Project.DoesNotExist:
            raise Http404

        projects = Project.objects.filter(administrators=maintainer)
        return render(request,
                      'code_doc/maintainer_details.html',
                      {'projects': projects,
                       'maintainer': maintainer})

    @method_decorator(login_required)
    def post(self, request):
        pass
