from django.views.generic.detail import DetailView

import logging

from ..models.revisions import Revision

logger = logging.getLogger(__name__)


class RevisionDetailView(DetailView):
    """Detailed view of a specific Revision. The view contains all artifacts. """

    model = Revision
    pk_url_kwarg = 'revision_id'
    template_name = 'code_doc/revision/revision_details.html'

    # We need to get all the series from a revision

    def get_context_data(self, **kwargs):
        context = super(RevisionDetailView, self).get_context_data(**kwargs)
        revision_object = self.object
        project = revision_object.project

        context['project'] = project
        context['artifacts'] = revision_object.artifacts.all()
        context['series'] = [v for v in revision_object.get_all_referencing_series() if self.request.user.has_perm('code_doc.series_view', v)]

        last_update = {}
        for v in context['series']:
            assert self.request.user.has_perm('code_doc.series_view', v)
            last_update[v] = {}
            current_update = v.artifacts.order_by('upload_date').last()
            if(current_update is not None):
                last_update[v]['last_update'] = current_update.upload_date

            last_doc = v.artifacts.filter(project_series=v, is_documentation=True).order_by('upload_date')
            if last_doc.exists():
                last_update[v]['last_doc'] = last_doc.last()

        context['last_update'] = last_update
        return context
