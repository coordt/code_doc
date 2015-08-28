
from django.shortcuts import render, get_object_or_404

from django.http import Http404, HttpResponse

from django.db import transaction, IntegrityError

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator

from django.views.generic.base import RedirectView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt

# for sending files specific to the server
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse, reverse_lazy

import os
import logging
import json

from .models import Project, Author, Topic, Artifact, ProjectSeries, Branch, Revision
from .forms import SeriesEditionForm, AuthorForm, ArtifactEditionForm
from .permissions.decorators import permission_required_on_object

# logger for this file
logger = logging.getLogger(__name__)


def index(request):
    """Front page"""
    projects_list = Project.objects.order_by('name')
    topics_list = Topic.objects.order_by('name')
    return render(request,
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
        return render(request,
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
        dispatch_to_wrap = super(PermissionOnObjectViewMixin, self).dispatch
        decorator = permission_required_on_object(object_permissions,
                                                  object_permissions_getter,
                                                  handle_access_error=self.handle_access_error)

        return decorator(dispatch_to_wrap)(request, *args, **kwargs)

    # we do not need to reimplement this behaviour as it is properly done in the decorator


class ProjectView(DetailView):
    """Detailed view of a specific project. The view contains all revisions.

    .. note:: no specific permission is associated to a project. All project can be seen from anyone.
              The series associated to a project might have limited visibility

    """

    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'code_doc/project_series/project_details.html'

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
            current_update = v.artifacts.order_by('upload_date').last()
            if(current_update is not None):
                last_update[v] = current_update.upload_date
            else:
                last_update[v] = None

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


################################################################################################
#
# Series related
################################################################################################

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
            logger.warning('[SeriesAddView] non existent project with id %s',
                           kwargs['project_id'])
            return None

    def get_serie_from_request(self, request, *args, **kwargs):
        project = self.get_project_from_request(request, *args, **kwargs)

        try:
            serie = project.series.get(pk=kwargs['series_id'])
        except ProjectSeries.DoesNotExist:
            logger.warning('[ProjectVersionDetailsView] non existent serie with id %d',
                           kwargs['series_id'])
            return None

        return serie

    def get_permission_object_from_request(self, request, *args, **kwargs):
        # this already checks the coherence of the url:
        # if the serie does not belong to the project, an PermissionDenied is raised

        return self.get_serie_from_request(request, *args, **kwargs)


class SeriesEditViewBase(SerieAccessViewBase):
    """Manages the edition views of the project series"""

    template_name = "code_doc/project_series/project_series_add_or_edit.html"

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

    # we should have the following priviledges on the serie in order to be able to edit anything
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

    template_name = 'code_doc/project_series/project_series_details.html'

    # we should have admin priviledges on the object in order to be able to add anything
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


class APIGetArtifacts(SeriesDetailsView, DetailView):
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

    def get_context_data(self, **kwargs):
        """Method used for populating the template context"""
        context = super(ArtifactAccessViewBase, self).get_context_data(**kwargs)

        # already project/series matching by the permission check above
        current_series = ProjectSeries.objects.get(pk=self.kwargs['series_id'])
        current_project = current_series.project

        context['project'] = current_project
        context['series'] = current_series
        context['artifacts'] = current_series.artifacts.all()
        context['uploaded_by'] = self.request.user  # @todo: FIX

        return context

    def get_success_url(self):
        return reverse('project_series',
                       kwargs={'project_id': self.object.project.pk,
                               'series_id': self.get_serie_from_url(self.request).id})


class ArtifactEditFormView(ArtifactAccessViewBase):

    template_name = "code_doc/project_artifacts/project_artifact_add.html"

    # for the form that is displayed
    form_class = ArtifactEditionForm


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
        form_data_query_dict = self.request.POST

        try:
            with transaction.atomic():

                # checking if branches need to be created
                # if the save fails, the state is restored
                if 'branch' in form_data_query_dict and form_data_query_dict['branch']:
                    branch_name = form_data_query_dict['branch']
                    branch, branch_created = Branch.objects.get_or_create(name=branch_name)
                else:
                    branch = None
                    branch_created = False

                if 'revision' in form_data_query_dict and form_data_query_dict['revision']:
                    revision_name = form_data_query_dict['revision']
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

                form.instance.save()
                form.instance.project_series = [current_series]

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

        return render(request,
                      'code_doc/topics/topics.html',
                      {'topic': topic})


class TopicListView(ListView):
    paginate_by = 10
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
    paginate_by = 10
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
