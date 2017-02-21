
from django.shortcuts import get_object_or_404

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.views.generic.detail import DetailView
from django.views.generic import ListView, View

import logging
import json

from ..models.projects import Project, ProjectSeries
from ..models.artifacts import Artifact

logger = logging.getLogger(__name__)


class ProjectView(DetailView):
    """Detailed view of a specific project. The view contains all revisions.

    .. note:: no specific permission is associated to a project. All project can be seen from anyone.
              The series associated to a project might have limited visibility

    """

    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'code_doc/project/project_details.html'

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
            last_update[v] = {}
            current_update = v.artifacts.order_by('upload_date').last()
            if(current_update is not None):
                last_update[v]['last_update'] = current_update.upload_date

            last_doc = Artifact.objects.filter(project_series=v, is_documentation=True).order_by('upload_date')
            if last_doc.exists():
                last_update[v]['last_doc'] = last_doc.last()

        context['last_update'] = last_update
        return context


class ProjectListView(ListView):
    """List all available projects"""
    paginate_by = 10
    template_name = "code_doc/project/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        # @todo should be narrowed to unrestricted ones?
        return Project.objects.all()


class GetProjectRevisionIds(View):
    """A view returning a json definition of the project and its associated series"""
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

    @method_decorator(login_required)
    def get(self, request, project_name, series_number):
        logger.debug('[GetProjectRevisionIds.get]')
        project = get_object_or_404(Project, name=project_name)
        series = get_object_or_404(ProjectSeries, series=series_number, project=project)
        return self.render_to_json_response({'project_id': project.id,
                                             'series_id': series.id})
