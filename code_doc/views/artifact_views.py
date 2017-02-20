
from django.http import HttpResponse
from django.db import transaction, IntegrityError
from django.views.generic.edit import CreateView, DeleteView
from django.core.urlresolvers import reverse

import logging

from .permission_helpers import PermissionOnObjectViewMixin
from ..models import Project, Artifact, ProjectSeries, Branch, Revision
from ..forms.forms import ArtifactEditionForm

# logger for this file
logger = logging.getLogger(__name__)


class ArtifactAccessViewBase(PermissionOnObjectViewMixin):
    """A generic class for grouping the several views for the artifacts"""

    model = Artifact

    permissions_object_getter = 'get_permission_object_from_request'

    def get_permission_object_from_request(self, request, *args, **kwargs):
        return self.get_serie_from_url(request)

    def get_serie_from_url(self, request):
        try:
            current_project = Project.objects.get(pk=self.kwargs['project_id'])
        except Project.DoesNotExist:
            logger.warning('[ArtifactAccessViewBase] non existent project with id %d',
                           self.kwargs['project_id'])
            return None

        try:
            current_series = current_project.series.get(pk=self.kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[ArtifactAccessViewBase] non existent series for project "%s",id=%d with series.id "%s"',
                           current_project, current_project.id, self.kwargs['series_id'])
            return None

        return current_series


class ArtifactEditFormView(ArtifactAccessViewBase):

    template_name = "code_doc/project_artifacts/project_artifact_add.html"

    # for the form that is displayed
    form_class = ArtifactEditionForm

    def get_success_url(self):
        return reverse('project_series',
                       kwargs={'project_id': self.object.project.pk,
                               'series_id': self.get_serie_from_url(self.request).id})

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ArtifactAccessViewBase, self).get_context_data(**kwargs)
        self.form_class.set_context_for_template(context, self.kwargs['series_id'])

        return context


class ArtifactAddView(ArtifactEditFormView, CreateView):
    """Generic view for adding a series into a specific project"""

    template_name = "code_doc/artifacts/artifact_add.html"

    permissions_on_object = ('code_doc.series_artifact_add',)

    def form_valid(self, form):

        # after the form validation occured

        current_series = self.get_serie_from_url(self.request)
        current_project = current_series.project
        assert(str(current_project.id) == self.kwargs['project_id'])

        # Get the raw data that was sent as the request
        # form_data_query_dict = self.request.POST
        try:

            with transaction.atomic():

                # checking if branches need to be created
                # if the save fails, the state is restored
                if 'branch' in form.cleaned_data and form.cleaned_data['branch']:
                    branch_name = form.cleaned_data['branch']
                    branch, branch_created = Branch.objects.get_or_create(name=branch_name)
                else:
                    branch = None
                    branch_created = False

                if 'revision' in form.cleaned_data and form.cleaned_data['revision']:
                    revision_name = form.cleaned_data['revision']

                    # Try to get already saved models from the database
                    revision, revision_created = Revision.objects.get_or_create(revision=revision_name,
                                                                                project=current_project)
                else:
                    revision = None
                    revision_created = False

                if branch is not None and revision is not None:
                    branch.revisions.add(revision)

                form.instance.project = current_project

                if revision is not None:
                    form.instance.revision = revision

                # automatic filling of the user and date
                form.instance.uploaded_by = self.request.user

                from django.utils import timezone
                form.instance.upload_date = timezone.now()

                # we save, otherwise we got the following error:
                # needs to have a value for field "artifact" before this many-to-many relationship can be used
                form.instance.save()

                form.instance.project_series.add(current_series)
                # form.instance.save()

                return super(ArtifactAddView, self).form_valid(form)

        except IntegrityError, e:
            logging.error("[fileupload] error during the save %s", e)
            return HttpResponse('Conflict %s' % form.instance.md5hash.upper(), status=409)

        return HttpResponse('Error saving the artifact' % form.instance.md5hash.upper(), status=404)


class ArtifactRemoveView(ArtifactAccessViewBase, DeleteView):
    """Removes an artifact"""

    permissions_on_object = ('code_doc.series_artifact_remove',)
    template_name = "code_doc/artifacts/artifact_remove.html"
    pk_url_kwarg = "artifact_id"
