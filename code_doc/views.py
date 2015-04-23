
from django.shortcuts import render, get_object_or_404

from django.http import Http404, HttpResponse
from django.template import RequestContext, loader

from django.db import transaction, IntegrityError

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.forms import ModelForm, Textarea, DateInput, CheckboxSelectMultiple
from django.forms.widgets import Widget, MultiWidget
from django.forms import ModelForm, Textarea, DateInput, CheckboxSelectMultiple
from django.utils.decorators import method_decorator

from django.views.generic.base import RedirectView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt

# for sending files specific to the server
from django.core.servers.basehttp import FileWrapper
from django.core.files import File
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import PermissionDenied

import os
import hashlib
import tempfile
import logging
import json
from functools import partial

from django.conf import settings

from code_doc.models import Project, Author, Topic, Artifact, ProjectSeries
from code_doc.forms import ProjectSeriesForm
from code_doc.permissions.decorators import permission_required_on_object

# logger for this file
logger = logging.getLogger(__name__)


def index(request):
    """Front page"""
    projects_list = Project.objects.order_by('name')
    topics_list = Topic.objects.order_by('name')
    return render(
            request,
            'code_doc/index.html',
            {'projects_list': projects_list,
             'topics_list': topics_list})


def about(request):
    """About page"""
    return render(request, 'code_doc/about.html', {})


def script(request):
    """Returns the script used for uploading stuff"""
    filename = 'code_doc_upload.py'
    file_content = open(os.path.join(os.path.dirname(__file__),
                                     'utils',
                                     'send_new_artifact.py'),
                        'rb')  # binary is important here
    response = HttpResponse(FileWrapper(file_content), content_type='application/text')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    response['Content-Length'] = file_content.tell()
    return response


class MaintainerProfileView(View):
    """Manages the views associated to the maintainers"""

    @method_decorator(login_required)
    def get(self, request, maintainer_id):
        try:
            maintainer = User.objects.get(pk=maintainer_id)
        except Project.DoesNotExist:
            raise Http404

        projects = Project.objects.filter(administrators=maintainer)
        return render(
                  request,
                  'code_doc/maintainer_details.html',
                  {'projects': projects,
                   'maintainer': maintainer})

    @method_decorator(login_required)
    def post(self, request):
        pass


class GetProjectRevisionIds(View):
    """A view returning a json definition of the project"""
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    @method_decorator(login_required)
    def get(self, request, project_name, series_number):
        logger.debug('[GetProjectRevisionIds.get]')
        project = get_object_or_404(Project, name=project_name)
        series = get_object_or_404(ProjectSeries, series=series_number, project=project)
        return self.render_to_json_response({'project_id': project.id, 'series_id': series.id})


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
        return permission_required_on_object(object_permissions, object_permissions_getter, handle_access_error=self.handle_access_error)\
                  (super(PermissionOnObjectViewMixin, self).dispatch)\
                      (request, *args, **kwargs)

    # we do not need to reimplement this behaviour as it is properly done in the decorator


class ProjectView(DetailView):
    """Detailed view of a specific project. The view contains all revisions.

    .. note:: no specific permission is associated to a project. All project can be seen from anyone.
              The series associated to a project might have limited visibility

    """

    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'code_doc/project_revision/project_details.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectView, self).get_context_data(**kwargs)
        project = self.object

        context['authors'] = project.authors.all()
        context['topics'] = project.topics.all()
        context['series'] = [v for v in project.series.all() if self.request.user.has_perm('code_doc.series_view', v)]

        last_update = {}
        for v in context['series']:
            assert(self.request.user.has_perm('code_doc.series_view', v))
            # if not self.request.user.has_perm('code_doc.series_view', v):
            #  continue
            current_update = Artifact.objects.filter(project_series=v).order_by('upload_date').last()
            if(current_update is not None):
                last_update[v] = current_update.upload_date
            else:
                last_update[v] = None

        context['last_update'] = last_update
        return context


class ProjectListView(ListView):
    """List all available projects"""
    paginate_by = 1
    template_name = "code_doc/project/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        # @todo should be narrowed to unrestricted ones?
        return Project.objects.all()


################################################################################################
#
# Series related
################################################################################################
class ProjectSeriesForm(ModelForm):
    """Form definition that is used when adding and editing a ProjectVersion"""
    class Meta:
        model = ProjectSeries
        fields = (
            'series', 'release_date', 'description_mk', 'view_users', 'view_groups',
            'view_artifacts_users', 'view_artifacts_groups'
        )
        labels = {
            'series': 'Series name',
            'description_mk': 'Description'
        }
        help_texts = {
            'description_mk': 'Description/content of the series in MarkDown format'
        }
        widgets = {
            'series': Textarea(attrs={
                                'cols': 120,
                                'rows': 2,
                                'style': "resize:none"
                                }),
            'description_mk': Textarea(attrs={
                                        'cols': 120,
                                        'rows': 10,
                                        'style': "resize:vertical"
                                        }),
            'release_date': DateInput(attrs={
                                        'class': 'datepicker',
                                        'data-date-format': "dd/mm/yyyy",
                                        'data-provide': 'datepicker'
                                        },
                                      format='%d/%m/%Y'),
            'view_users': CheckboxSelectMultiple,
            'view_groups': CheckboxSelectMultiple,
            'view_artifacts_users': CheckboxSelectMultiple,
            'view_artifacts_groups': CheckboxSelectMultiple
        }


# @todo: remove overlap with ProjectSeriesUpdateView
class ProjectSeriesAddView(PermissionOnObjectViewMixin, CreateView):
    """Generic view for adding a series into a specific project.

    .. note:: in order to be able to add a series, the user should have the
              'code_doc.project_series_add' permission
              on the project object.

    """
    form_class = ProjectSeriesForm

    model = ProjectSeries
    template_name = "code_doc/project_revision/project_revision_add_or_edit.html"

    # user should have the appropriate privileges on the object in order to be able to add anything
    permissions_on_object = ('code_doc.project_series_add',)
    permissions_object_getter = 'get_project_from_request'

    def get_project_from_request(self, request, *args, **kwargs):
        try:
            return Project.objects.get(pk=kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[ProjectSeriesAddView] non existent project with id %s',
                           kwargs['project_id'])
            return None

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ProjectSeriesAddView, self).get_context_data(**kwargs)
        try:
            current_project = Project.objects.get(pk=self.kwargs['project_id'])
        except Project.DoesNotExist:
            # this should not occur here
            raise
        form = context['form']

        context['project'] = current_project
        context['project_id'] = current_project.id

        context['automatic_fields'] = (form[i] for i in ('series', 'release_date', 'description_mk'))

        context['active_users'] = User.objects.all()

        context['permission_headers'] = ['View', 'Artifact view']
        context['user_permissions'] = zip(xrange(len(context['active_users'])),
                                          context['active_users'],
                                          form['view_users'],
                                          form['view_artifacts_users'])

        context['active_groups'] = Group.objects.all()
        context['group_permissions'] = zip(xrange(len(context['active_groups'])),
                                           context['active_groups'],
                                           form['view_groups'],
                                           form['view_artifacts_groups'])
        return context

    def form_valid(self, form):
        try:
            current_project = Project.objects.get(pk=self.kwargs['project_id'])
        except Project.DoesNotExist:
            raise Http404

        form.instance.project = current_project
        return super(ProjectSeriesAddView, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProjectSeriesDetailsView(PermissionOnObjectViewMixin, DetailView):
    """Details the content of a specific series. Contains all the artifacts

    .. note:: the user should have the 'series_view' and the
              'series_artifact_view' permissions on the series object

    """

    # detail view on a series
    model = ProjectSeries
    # part of the url giving the proper object
    pk_url_kwarg = 'series_id'

    template_name = 'code_doc/project_revision/project_revision_details.html'

    # we should have admin priviledges on the object in order to be able to add anything
    permissions_on_object = ('code_doc.series_view', 'code_doc.series_artifact_view')
    permissions_object_getter = 'get_series_from_request'

    def get_series_from_request(self, request, *args, **kwargs):

        # this already checks the coherence of the url:
        # if the series does not belong to the project, an PermissionDenied is raised
        try:
            project = Project.objects.get(pk=kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[ProjectSeriesDetailsView] non existent project with id %d',
                           kwargs['project_id'])
            return None

        try:
            series = project.series.get(pk=kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[ProjectSeriesDetailsView] non existent series with id %d',
                           kwargs['series_id'])
            return None

        return series

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ProjectSeriesDetailsView, self).get_context_data(**kwargs)

        series_object = self.object

        assert(Project.objects.get(pk=self.kwargs['project_id']).id == series_object.project.id)

        context['series'] = series_object
        context['project'] = series_object.project
        context['project_id'] = series_object.project.id
        context['artifacts'] = series_object.artifacts.all()
        return context


class CredentialsWidget(MultiWidget):
    """

    """
    def __init__(self, fields, name_mapping, attrs=None):
        widgets = [forms.CheckboxSelectMultiple()]
        super(MultiWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class EmptyWidget(CheckboxSelectMultiple):
    """

    """
    def __init__(self, attrs=None):
        super(EmptyWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        return ''


# @todo: remove overlap with ProjectSeriesAddView
class ProjectSeriesUpdateView(PermissionOnObjectViewMixin, UpdateView):
    """Update the content of a specific series.

    .. note:: the user should have the 'series_view' and the 'series_artifact_view'
              permissions on the series object

    """

    # detail view on a series
    model = ProjectSeries
    # part of the url giving the proper object
    pk_url_kwarg = 'series_id'

    template_name = 'code_doc/project_revision/project_revision_add_or_edit.html'

    # we should have admin priviledges on the object in order to be able to add anything
    permissions_on_object = ('code_doc.series_edit',)
    permissions_object_getter = 'get_series_from_request'

    # for the form that is displayed
    form_class = ProjectSeriesForm

    def get_series_from_request(self, request, *args, **kwargs):
        # this already checks the coherence of the url:
        # if the version does not belong to the project, an PermissionDenied is raised
        try:
            project = Project.objects.get(pk=kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[ProjectVersionDetailsView] non existent project with id %d',
                           kwargs['project_id'])
            return None

        try:
            version = project.series.get(pk=kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[ProjectVersionDetailsView] non existent version with id %d',
                           kwargs['series_id'])
            return None

        return version

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ProjectSeriesUpdateView, self).get_context_data(**kwargs)

        series_object = self.object

        assert(Project.objects.get(pk=self.kwargs['project_id']).id == series_object.project.id)

        form = context['form']

        context['series'] = series_object
        context['project'] = series_object.project
        context['project_id'] = series_object.project.id
        context['artifacts'] = series_object.artifacts.all()
        context['permission_headers'] = ['View', 'Artifact view']

        context['automatic_fields'] = (form[i] for i in ('series', 'release_date', 'description_mk'))

        context['active_users'] = User.objects.all()  # set(series_object.view_users.all()) | set(series_object.view_artifacts_users.all())
        context['user_permissions'] = zip(xrange(len(context['active_users'])),
                                          context['active_users'],
                                          form['view_users'],
                                          form['view_artifacts_users'])

        # context['active_groups'] = set(series_object.view_groups.all()) | set(series_object.view_artifacts_groups.all())
        context['active_groups'] = Group.objects.all()
        context['group_permissions'] = zip(xrange(len(context['active_groups'])),
                                           context['active_groups'],
                                           form['view_groups'],
                                           form['view_artifacts_groups'])

        # context['form']['view_groups'].is_hidden = True

        print form.visible_fields()
        return context


class ProjectSeriesDetailsShortcutView(RedirectView):
    """A shortcut for being able to reach a project and a series with only their respective name"""
    permanent = False
    query_string = True
    pattern_name = 'project_revision'

    def get_redirect_url(self, *args, **kwargs):
        logger.debug('[project_series_redirection] %s', kwargs)
        project = get_object_or_404(Project, name=kwargs['project_name'])
        series = get_object_or_404(ProjectSeries, series=kwargs['series_number'], project=project)
        return reverse('project_revision', args=[project.id, series.id])


class APIGetArtifacts(ProjectSeriesDetailsView, DetailView):
    """An API view returning a json dictionary containing all artifacts of a specific revision"""

    def render_to_response(self, context, **response_kwargs):
        artifacts = context['artifacts']
        l = {}
        for art in artifacts:
            l[art.id] = {'file': art.artifactfile.name,
                         'md5': art.md5hash}
        data = json.dumps({'artifacts': l})
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)


################################################################################################
#
# Artifacts related
################################################################################################


class ProjectSeriesArtifactEditionFormsView(PermissionOnObjectViewMixin):
    """A generic class for grouping the several views for the artifacts"""

    model = Artifact

    permissions_on_object = ('code_doc.project_artifact_add',)
    permissions_object_getter = 'get_project_from_request'

    def get_project_from_request(self, request, *args, **kwargs):

        try:
            current_project = Project.objects.get(pk=self.kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[ProjectSeriesArtifactEditionFormsView] non existent project with id %d',
                           self.kwargs['project_id'])
            return None

        try:
            current_series = current_project.series.get(pk=self.kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[ProjectSeriesArtifactEditionFormsView] non existent series for project "%s" with series.id "%s"',
                           current_project, self.kwargs['series_id'])
            return None

        return current_project

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ProjectSeriesArtifactEditionFormsView, self).get_context_data(**kwargs)

        current_series = ProjectSeries.objects.get(pk=self.kwargs['series_id'])
        current_project = current_series.project

        context['project'] = current_project
        context['series'] = current_series
        context['artifacts'] = current_series.artifacts.all()
        context['uploaded_by'] = self.request.user  # @todo: FIX
        return context

    def get_success_url(self):
        return reverse('project_revision',
                       kwargs={'project_id': self.object.project_series.project.pk,
                               'series_id': self.object.project_series.pk})


class ProjectSeriesArtifactAddView(ProjectSeriesArtifactEditionFormsView, CreateView):
    """Generic view for adding a series into a specific project"""

    template_name = "code_doc/project_artifacts/project_artifact_add.html"
    fields = ['description', 'artifactfile', 'is_documentation', 'documentation_entry_file', 'upload_date']

    def form_valid(self, form):

        current_series = ProjectSeries.objects.get(pk=self.kwargs['series_id'])
        current_project = current_series.project
        assert(str(current_project.id) == self.kwargs['project_id'])

        form.instance.project_series = current_series

        try:
            with transaction.atomic():
                return super(ProjectSeriesArtifactAddView, self).form_valid(form)
        except IntegrityError, e:
            logging.error("[fileupload] error during the save %s", e)

        return HttpResponse('Conflict %s' % form.instance.md5hash.upper(), status=409)


class ProjectSeriesArtifactRemoveView(ProjectSeriesArtifactEditionFormsView, DeleteView):
    """Removes an artifact"""

    template_name = "code_doc/project_artifacts/project_artifact_remove.html"
    pk_url_kwarg = "artifact_id"


################################################################################################
#
# Topics related
################################################################################################

class TopicView(View):
    def get(self, request, topic_id):
        try:
            topic = Topic.objects.get(pk=topic_id)
        except Project.DoesNotExist:
            raise Http404

        return render(
                  request,
                  'code_doc/topics/topics.html',
                  {'topic': topic})


class TopicListView(ListView):
    paginate_by = 2
    template_name = "code_doc/topics/topic_list.html"
    context_object_name = "topics"

    def get_queryset(self):
        return Topic.objects.all()


################################################################################################
#
# Authors related
################################################################################################

class AuthorListView(ListView):
    """A generic view of the authors in a list"""
    paginate_by = 2
    template_name = "code_doc/author_list.html"
    context_object_name = "authors"

    def get_queryset(self):
        return Author.objects.all()


def detail_author(request, author_id):
    try:
        author = Author.objects.get(pk=author_id)
    except Author.DoesNotExist:
        raise Http404

    project_list = Project.objects.filter(authors=author)
    coauthor_list = Author.objects.filter(project__in=project_list).distinct().exclude(pk=author_id)
    return render(request,
                  'code_doc/author_details.html',
                  {'project_list': project_list,
                   'author': author,
                   'coauthor_list': coauthor_list})
