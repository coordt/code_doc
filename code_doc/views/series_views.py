
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse

from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView

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

    # for the form that is displayed
    form_class = SeriesEditionForm

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(SeriesEditViewBase, self).get_context_data(**kwargs)
        self.form_class.set_context_for_template(context, self.kwargs['project_id'])

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
    permissions_on_object = ('code_doc.series_edit',)

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(SeriesUpdateView, self).get_context_data(**kwargs)
        series_object = self.object

        assert(Project.objects.get(pk=self.kwargs['project_id']).id == series_object.project.id)

        # We need this to distinguish between Adding and Editing a Series
        context['series'] = series_object

        return context


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

        # We need this to distinguish between Adding and Editing a Series
        context['series'] = series_object
        context['project'] = series_object.project
        context['project_id'] = series_object.project.id
        context['artifacts'] = series_object.artifacts.all()
        context['revisions'] = set([art.revision for art in context['artifacts'] if art.revision is not None])

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
        l = {}
        for art in artifacts:
            l[art.id] = {'file': art.artifactfile.name,
                         'md5': art.md5hash}
        data = json.dumps({'artifacts': l})
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)
