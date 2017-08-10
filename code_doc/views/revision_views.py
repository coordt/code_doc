from django.views.generic.detail import DetailView
from django.shortcuts import get_object_or_404

import logging

from ..models.projects import Project
from ..models.revisions import Revision
from ..models.artifacts import Artifact

from .permission_helpers import PermissionOnObjectViewMixin

logger = logging.getLogger(__name__)


class RevisionAccessViewBase(PermissionOnObjectViewMixin):
    """Manages the access to the object related to the revision."""

    model = Revision

    # the object on which permission applies
    permissions_object_getter = 'get_permission_object_from_request'

    def get_project_from_request(self, request, *args, **kwargs):
        # default: returns the project
        try:
            return Project.objects.get(pk=kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[RevisionAccessViewBase] non existent project with id %s',
                           kwargs['project_id'])
            return None

    def get_revision_from_request(self, request, *args, **kwargs):
        project = self.get_project_from_request(request, *args, **kwargs)
        if project is None:
            return None

        try:
            revision = project.revisions.get(pk=kwargs['revision_id'])
        except Revision.DoesNotExist:
            logger.warning('[RevisionAccessViewBase] non existent revision with id %s',
                           kwargs['revision_id'])
            return None

        return revision

    def get_permission_object_from_request(self, request, *args, **kwargs):
        # this already checks the coherence of the url:
        # if the revision does not belong to the project, an PermissionDenied is raised
        return self.get_revision_from_request(request, *args, **kwargs)


class RevisionDetailsView(RevisionAccessViewBase, DetailView):
    """Detailed view of a specific Revision. The view contains all artifacts. """

    model = Revision
    pk_url_kwarg = 'revision_id'
    template_name = 'code_doc/revision/revision_details.html'

    # We should have admin privileges on the object in order to be able to see anything
    permissions_on_object = ('code_doc.revision_view',)

    def get_context_data(self, **kwargs):
        context = super(RevisionDetailsView, self).get_context_data(**kwargs)

        revision_object = self.object

        # Check that we are passing the correct project_id
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        assert(project.id == revision_object.project.id)

        context['project'] = revision_object.project
        context['series'] = [v for v in revision_object.get_all_referencing_series()
                             if self.request.user.has_perm('code_doc.series_view', v)]

        # We have access to the artifact only if we have permissions to see at least one of its series
        context['artifacts'] = []
        for art in revision_object.artifacts.all():
            all_series = Artifact.get_project_series(art)
            if not set(all_series).isdisjoint(context['series']):
                context['artifacts'].append(art)

        last_update = {}
        for v in context['series']:
            assert self.request.user.has_perm('code_doc.series_view', v)
            last_update[v] = {}
            current_update = v.artifacts.order_by('upload_date').last()
            if(current_update is not None):
                last_update[v]['last_update'] = current_update.upload_date

            last_doc = v.artifacts.filter(is_documentation=True).order_by('upload_date')
            if last_doc.exists():
                last_update[v]['last_doc'] = last_doc.last()

        context['last_update'] = last_update
        return context
