
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse

from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse

import logging
import json

from ..models.projects import Project, ProjectSeries
from ..forms.forms import SeriesEditionForm
from .permission_helpers import PermissionOnObjectViewMixin

logger = logging.getLogger(__name__)


class SerieAccessViewBase(PermissionOnObjectViewMixin):
    """Manages the access to the object related to the series (project or serie)"""

    model = ProjectSeries

    # the object on which permission applies
    permissions_object_getter = 'get_permission_object_from_request'

    def get_project_from_request(self, request, *args, **kwargs):
        # default: returns the project
        try:
            return Project.objects.get(pk=kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[SerieAccessViewBase] non existent project with id %s',
                           kwargs['project_id'])
            return None

    def get_serie_from_request(self, request, *args, **kwargs):
        project = self.get_project_from_request(request, *args, **kwargs)

        try:
            serie = project.series.get(pk=kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[SerieAccessViewBase] non existent serie with id %d',
                           kwargs['series_id'])
            return None

        return serie

    def get_permission_object_from_request(self, request, *args, **kwargs):
        # this already checks the coherence of the url:
        # if the series does not belong to the project, an PermissionDenied is raised

        return self.get_serie_from_request(request, *args, **kwargs)


class SeriesEditViewBase(SerieAccessViewBase):
    """Manages the edition views of the project series"""

    template_name = "code_doc/series/series_add_or_edit.html"
    permissions_on_object = ('code_doc.series_edit',)

    # for the form that is displayed
    form_class = SeriesEditionForm

    context_object_name = 'series'

    def get_context_data(self, **kwargs):
        context = super(SeriesEditViewBase, self).get_context_data(**kwargs)

        try:
            current_project = Project.objects.get(id=self.kwargs['project_id'])
        except Project.DoesNotExist:
            # this should not occur here
            raise

        context['project'] = current_project

        form = context['form']
        context['automatic_fields'] = (form[i] for i in ('project', 'series', 'release_date',
                                                         'description_mk', 'is_public',
                                                         'nb_revisions_to_keep'))

        context['permission_headers'] = ['View and download', 'Adding artifacts', 'Removing artifacts']

        # filter out users that are not in the queryset
        context['active_users'] = form['view_users'].field.queryset

        context['user_permissions'] = zip(context['active_users'],
                                          form['view_users'],
                                          form['perms_users_artifacts_add'],
                                          form['perms_users_artifacts_del'])
        context['user_permissions'] = [(perms[0], tuple(perms[1:])) for perms in context['user_permissions']]

        # filter out groups that are not in the queryset
        context['active_groups'] = form['view_groups'].field.queryset
        context['group_permissions'] = zip(context['active_groups'],
                                           form['view_groups'],
                                           form['perms_groups_artifacts_add'],
                                           form['perms_groups_artifacts_del'])
        context['group_permissions'] = [(perms[0], tuple(perms[1:])) for perms in context['group_permissions']]

        return context

    def get_success_url(self):
        return self.object.get_absolute_url()


class SeriesAddView(SeriesEditViewBase, CreateView):
    """Generic view for adding a series into a specific project.

    .. note:: in order to be able to add a series, the user should have the
              'code_doc.project_series_add' permission
              on the project object.

    """

    # user should have the appropriate privileges on the object in order to be able to add anything
    permissions_on_object = ('code_doc.project_series_add',)

    def get_permission_object_from_request(self, request, *args, **kwargs):
        # specific case since we are adding to the project
        return self.get_project_from_request(request, *args, **kwargs)

    def get_initial(self, *args, **kwargs):

        initial = super(SeriesAddView, self).get_initial()

        # Only the current user
        for perm in ('view_users', 'perms_users_artifacts_add', 'perms_users_artifacts_del'):
            initial[perm] = [User.objects.get(username=self.request.user)]

        # No group
        for perm in ('view_groups', 'perms_groups_artifacts_add', 'perms_groups_artifacts_del'):
            initial[perm] = []

        if 'project' not in initial:
            initial['project'] = self.get_project_from_request(self.request, *self.args, **self.kwargs)

        return initial

    def form_valid(self, form):
        # in this case we need to set the project of the object otherwise the association
        # of the created object does not work.

        try:
            current_project = Project.objects.get(pk=self.kwargs['project_id'])
        except Project.DoesNotExist:
            raise Http404

        form.instance.project = current_project
        return super(SeriesAddView, self).form_valid(form)


class SeriesUpdateView(SeriesEditViewBase, UpdateView):
    """Update the content of a specific series.

    .. note:: the user should have the 'series_edit' permission on the series object

    """

    # part of the url giving the proper object
    pk_url_kwarg = 'series_id'

    # we should have the following privileges on the series in order to be able to edit anything
    # warning: this is an AND on all permissions, not an OR, so series_edit should be true for series_artifact_add
    permissions_on_object = ('code_doc.series_edit',)


class SeriesDetailsView(SerieAccessViewBase, DetailView):
    """Details the content of a specific series. Contains all the artifacts

    .. note:: the user should have the 'series_view' permission on the series object

    """

    # part of the url giving the proper object
    pk_url_kwarg = 'series_id'

    template_name = 'code_doc/series/series_details.html'

    # we should have admin privileges on the object in order to be able to add anything
    permissions_on_object = ('code_doc.series_view',)

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""

        context = super(SeriesDetailsView, self).get_context_data(**kwargs)
        series_object = self.object

        assert(Project.objects.get(pk=self.kwargs['project_id']).id == series_object.project.id)

        # We need this to distinguish between adding and editing a series
        context['series'] = series_object
        context['project'] = series_object.project
        context['artifacts'] = series_object.artifacts.all()
        context['revisions'] = list(set([art.revision for art in context['artifacts']]))
        return context


class SeriesDetailsViewShortcut(RedirectView):
    """A shortcut for being able to reach a project and a series with only their respective name"""
    permanent = False
    query_string = True
    pattern_name = 'project_series'

    def get_redirect_url(self, *args, **kwargs):
        logger.debug('[project_series_redirection] %s', kwargs)
        project = get_object_or_404(Project, name=kwargs['project_name'])
        series = get_object_or_404(ProjectSeries, series=kwargs['series_number'], project=project)
        return reverse('project_series', args=[project.id, series.id])


class APIGetSeriesArtifacts(SeriesDetailsView, DetailView):
    """An API view returning a json dictionary containing all artifacts of a specific series"""

    def render_to_response(self, context, **response_kwargs):
        artifacts = context['artifacts']
        ldict = {}
        for art in artifacts:
            ldict[art.id] = {'file': art.artifactfile.name,
                             'md5': art.md5hash}
        data = json.dumps({'artifacts': ldict})
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)
