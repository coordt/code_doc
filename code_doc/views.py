
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from django.http import Http404 
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse, reverse_lazy

from django.db import transaction

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


from django.views.generic.base import RedirectView
from django.views.generic.base import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import ListView

from django.core.exceptions import PermissionDenied

from django.views.decorators.csrf import csrf_exempt

from django.core.files import File


from django.contrib.auth.models import User


import hashlib
import tempfile
import logging
import json
from functools import partial

# logger for this file
logger = logging.getLogger(__name__)

from django.conf import settings


from code_doc.models import Project, Author, Topic, ProjectVersion, Artifact, ProjectVersion
from code_doc.forms import ProjectVersionForm
from code_doc.permissions.decorators import permission_required_on_object


def index(request):
  projects_list = Project.objects.order_by('name')
  topics_list = Topic.objects.order_by('name')
  return render(
          request, 
          'code_doc/index.html', 
          {'projects_list': projects_list, 
           'topics_list': topics_list})
  


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
               'maintainer':maintainer})
  
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
  def get(self, request, project_name, version_number):
    
    logger.debug('[GetProjectRevisionIds.get]')
    project = get_object_or_404(Project, name=project_name)
    version = get_object_or_404(ProjectVersion, version=version_number, project=project)
    return self.render_to_json_response({'project_id': project.id, 'version_id': version.id})




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
        
    object_permissions = getattr(self, 'permissions_on_object', None)
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
            The versions associated to a project might have limited visibility 
  
  """
  
  model         = Project
  pk_url_kwarg  = 'project_id'
  template_name = 'code_doc/project_revision/project_details.html'
  
  def get_context_data(self, **kwargs):
    context = super(ProjectView, self).get_context_data(**kwargs)
    project = self.object
    
    context['authors']  = project.authors.all()
    context['topics']   = project.topics.all()
    context['versions'] = [v for v in project.versions.all() if self.request.user.has_perm('code_doc.version_view', v)]
    
    last_update = {}
    for v in context['versions']:
      assert(self.request.user.has_perm('code_doc.version_view', v))
      #if not self.request.user.has_perm('code_doc.version_view', v):
      #  continue
      current_update = Artifact.objects.filter(project_version=v).order_by('upload_date').last()
      if(not current_update is None):
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
# Versions/series related
################################################################################################
  

class ProjectVersionAddView(PermissionOnObjectViewMixin, CreateView):
  """Generic view for adding a version into a specific project.
  
  .. note:: in order to be able to add a version, the user should have the 'code_doc.project_version_add' permission
            on the project object.
  
  """
  model = ProjectVersion
  template_name = "code_doc/project_revision/project_revision_add.html"
  fields = ['version', 'description', 'release_date', 'is_public', 'view_users', 'view_groups']
  

  # user should have the appropriate privileges on the object in order to be able to add anything  
  permissions_on_object = ('code_doc.project_version_add',)
  permissions_object_getter = 'get_project_from_request'
  
  def get_project_from_request(self, request, *args, **kwargs):
    
    try:
      return Project.objects.get(pk=kwargs['project_id'])  
    except Project.DoesNotExist:
      logger.warning('[ProjectVersionAddView] non existent project with id %s', kwargs['project_id'])
      return None    
    
      
  
  
  def get_context_data(self, **kwargs):
    """Method used for populating the template context"""
    context = super(ProjectVersionAddView, self).get_context_data(**kwargs)
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])  
    except Project.DoesNotExist:
      # this should not occur here
      raise 
    
    context['project'] = current_project
    context['project_id'] = current_project.id       
    return context

  def get(self, request, project_id, **kwargs):
    """Returning the form"""
    try:
      current_project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    if not self.request.user.is_superuser and not current_project.has_user_project_version_add_permission(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    return super(ProjectVersionAddView, self).get(request, project_id, **kwargs)

  def form_valid(self, form):    
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])
    except Project.DoesNotExist:
      raise Http404
    
    if not self.request.user.is_superuser and not current_project.has_user_project_version_add_permission(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    form.instance.project =current_project 
    return super(ProjectVersionAddView, self).form_valid(form)
  
  def get_success_url(self):
    return self.object.get_absolute_url()  
  


class ProjectVersionDetailsView(PermissionOnObjectViewMixin, DetailView):
  """Details the content of a specific version. Contains all the artifacts
  
  .. note:: the user should have the 'version_view' and the 'version_artifact_view' permissions on the version object
  
  """
  
  # detail view on a version
  model = ProjectVersion
  # part of the url giving the proper object
  pk_url_kwarg  = 'version_id'
  
  template_name = 'code_doc/project_revision/project_revision_details.html'
  
  # we should have admin priviledges on the object in order to be able to add anything  
  permissions_on_object = ('code_doc.version_view','code_doc.version_artifact_view')
  permissions_object_getter = 'get_version_from_request'
  
  def get_version_from_request(self, request, *args, **kwargs):
    
    # this already checks the coherence of the url:
    # if the version does not belong to the project, an PermissionDenied is raised
    try:
      project = Project.objects.get(pk=kwargs['project_id'])  
    except Project.DoesNotExist:
      logger.warning('[ProjectVersionDetailsView] non existent project with id %d', kwargs['project_id'])
      return None    
  
    try:
      version = project.versions.get(pk=kwargs['version_id'])
    except ProjectVersion.DoesNotExist:
      logger.warning('[ProjectVersionDetailsView] non existent version with id %d', kwargs['version_id'])
      return None
  
    return version
  
  def get_context_data(self, **kwargs):
    """Method used for populating the template context"""
    context = super(ProjectVersionDetailsView, self).get_context_data(**kwargs)
    
    version_object = self.object
    
    assert(Project.objects.get(pk=self.kwargs['project_id']).id == version_object.project.id)
    
    context['version'] = version_object 
    context['project'] = version_object.project
    context['project_id'] = version_object.project.id
    context['artifacts'] = version_object.artifacts.all()
    return context  
  
  
#   def get(self, request, project_id, version_id):
#     
#     try:
#       project = Project.objects.get(pk=project_id)
#     except Project.DoesNotExist:
#       raise Http404
#     
#     try:
#       version = project.versions.get(pk=version_id)
#     except ProjectVersion.DoesNotExist:
#       raise Http404
#     
#     artifacts = version.artifacts.all()
#     return render(
#               request, 
#               'code_doc/project_revision/project_revision_details.html',
#               {'project': project,
#                'version': version,
#                'artifacts': artifacts})


class ProjectVersionDetailsShortcutView(RedirectView):
  """A shortcut for being able to reach a project and a version with only their respective name"""
  permanent = False
  query_string = True
  pattern_name = 'project_revision'

  def get_redirect_url(self, *args, **kwargs):
    logger.debug('[project_version_redirection] %s', kwargs)
    project = get_object_or_404(Project, name=kwargs['project_name'])
    version = get_object_or_404(ProjectVersion, version=kwargs['version_number'], project=project)
    return reverse('project_revision', args=[project.id, version.id])













################################################################################################
# 
# Artifacts related
################################################################################################


class ProjectVersionArtifactEditionFormsView(PermissionOnObjectViewMixin):
  """A generic class for grouping the several views for the artifacts"""
  
  model = Artifact
  
  permissions_on_object = ('code_doc.project_artifact_add',)
  permissions_object_getter = 'get_project_from_request'
  
  def get_project_from_request(self, request, *args, **kwargs):
    
    try:
      return Project.objects.get(pk=kwargs['project_id'])  
    except Project.DoesNotExist:
      logger.warning('[ProjectVersionArtifactEditionFormsView] non existent project with id %d', project_id)
      return None    
  
  def get_context_data(self, **kwargs):
    """Method used for populating the template context"""
    context = super(ProjectVersionArtifactEditionFormsView, self).get_context_data(**kwargs)
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])  
    except Project.DoesNotExist:
      raise Http404
    try:
      current_version = current_project.versions.get(pk=self.kwargs['version_id'])  
    except ProjectVersion.DoesNotExist:
      raise Http404

    context['project'] = current_project
    context['version'] = current_version
    context['artifacts'] = current_version.artifacts.all()
    context['uploaded_by'] = self.request.user
    return context
  
  #def dispatch(self, request, *args, **kwargs):
  #  print "Dispatching"
  #  return super(ProjectVersionArtifactEditionFormsView, self).dispatch(request, *args, **kwargs)
  
  #@permission_required_on_object(('code_doc.project_administrate',), self.project_getter)
  #@method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def get(self, request, project_id, version_id, *args, **kwargs):
    """Returning the form"""
    logger.warning('[fileupload] get %s, %s, %s', project_id, version_id, kwargs)
    
    try:
      current_project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    if not self.request.user.is_superuser and not current_project.has_user_project_artifact_add_permission(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    try:
      current_version = current_project.versions.get(pk=version_id)
    except ProjectVersion.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    return super(ProjectVersionArtifactEditionFormsView, self).get(request, project_id, version_id, *args, **kwargs)  
  

  def get_success_url(self):
    return reverse('project_revision', 
                   kwargs={'project_id' : self.object.project_version.project.pk, 'version_id': self.object.project_version.pk})


class ProjectVersionArtifactAddView(ProjectVersionArtifactEditionFormsView, CreateView):
  """Generic view for adding a version into a specific project"""
    
  template_name = "code_doc/project_artifacts/project_artifact_add.html"
  fields = ['description', 'artifactfile', 'is_documentation', 'documentation_entry_file', 'upload_date']
  

  #@method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def form_valid(self, form):    
    
    logger.warning('[fileupload] form valid')
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])
    except Project.DoesNotExist:
      logger.warning('[fileupload] formvalid project does not exist')
      raise Http404
    
    if not self.request.user.is_superuser and not current_project.has_user_project_artifact_add_permission(self.request.user):
      return HttpResponse('Unauthorized', status=401) 

    logger.debug('[fileupload] version')
    try:
      current_version = current_project.versions.get(pk=self.kwargs['version_id'])
    except ProjectVersion.DoesNotExist:
      logger.warning('[fileupload] formvalid version does not exist')
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    form.instance.project_version = current_version 
    
    try:
      with transaction.atomic():
        return super(ProjectVersionArtifactAddView, self).form_valid(form)
    except Exception, e:
      logging.error("[fileupload] error during the save %s", e)
    
    return HttpResponse('Conflict %s' % form.instance.md5hash.upper(), status=409)
    
    


class ProjectVersionArtifactRemoveView(ProjectVersionArtifactEditionFormsView, DeleteView):
  """Removes an artifact"""
  
  template_name = "code_doc/project_artifacts/project_artifact_remove.html"
  pk_url_kwarg  = "artifact_id"



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
  coauthor_list= Author.objects.filter(project__in=project_list).distinct().exclude(pk=author_id)
  return render(
            request, 
            'code_doc/author_details.html', 
            {'project_list': project_list, 
             'author': author, 
             'coauthor_list': coauthor_list})


