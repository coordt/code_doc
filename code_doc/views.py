
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from django.http import Http404 
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse, reverse_lazy


from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


from django.views.generic.base import RedirectView
from django.views.generic.base import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import ListView


from django.views.decorators.csrf import csrf_exempt


from django.core.files import File


from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.views import APIView


from code_doc.permissions.decorators import permission_required_on_object



import hashlib
import tempfile
import logging
import json

# logger for this file
logger = logging.getLogger(__name__)

from django.conf import settings


from code_doc.models import Project, Author, Topic, ProjectVersion, Artifact, ProjectVersion
from code_doc.forms import ProjectVersionForm
#from code_doc.serializers import ProjectSerializer


def index(request):
  projects_list = Project.objects.order_by('name')
  topics_list = Topic.objects.order_by('name')
  return render(
          request, 
          'code_doc/index.html', 
          {'projects_list': projects_list, 
           'topics_list': topics_list})
  


class MaintainerProfileView(View):
  
  @method_decorator(login_required(login_url='/accounts/login/'))
  def get(self, request):
    try:
      user = request.user #User.objects.get(pk=user_id)
    except Project.DoesNotExist:
      raise Http404
    
    projects = Project.objects.filter(administrators=user)
    return render(
              request, 
              'code_doc/maintainer_details.html', 
              {'projects': projects})
  
  @login_required(login_url='/accounts/login/')
  def post(self, request):
    pass

class GetProjectRevisionIds(View):
  """A view returning a json definition of the project"""
  def render_to_json_response(self, context, **response_kwargs):
    data = json.dumps(context)
    response_kwargs['content_type'] = 'application/json'
    return HttpResponse(data, **response_kwargs)

  @method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def get(self, request, project_name, version_number):
    
    logger.debug('[GetProjectRevisionIds.get]')
    project = get_object_or_404(Project, name=project_name)
    version = get_object_or_404(ProjectVersion, version=version_number, project=project)
    return self.render_to_json_response({'project_id': project.id, 'version_id': version.id})



# just an attempt to do something 
class PermissionOnObjectViewMixin(object):
  @classmethod
  def as_view(cls, **initkwargs):
    view = super(PermissionOnObjectViewMixin, cls).as_view(**initkwargs)
    return permission_required_on_object(view)


class ProjectView(DetailView):
  """Detailed view of a specific project. The view contains all revisions."""
  
  model         = Project
  pk_url_kwarg  = 'project_id'
  template_name = 'code_doc/project_revision/project_details.html'
  
  def get_context_data(self, **kwargs):
    context = super(ProjectView, self).get_context_data(**kwargs)
    
    project = self.object
    
    context['authors']  = project.authors.all()
    context['topics']   = project.topics.all()
    context['versions'] = [v for v in project.versions.all() if v.has_user_view_permission(self.request.user)]
    
    return context  
  
#   def get(self, request, project_id):
#     try:
#       project = Project.objects.get(pk=project_id)
#     except Project.DoesNotExist:
#       raise Http404
#     
#     author_list = project.authors.all()
#     topic_list  = project.topics.all()
#     version_list  = project.versions.all()
#     return render(
#               request, 
#               'code_doc/project_revision/project_details.html', 
#               {'project': project, 
#                'authors': author_list, 
#                'topics': topic_list,
#                'versions' : version_list})

  
class ProjectListView(ListView):
  """List all available projects"""
  paginate_by = 1
  template_name = "code_doc/project/project_list.html"
  context_object_name = "projects"

  def get_queryset(self):
    # @todo should be narrowed to unrestricted ones?
    return Project.objects.all()
  
  

class ProjectVersionAddView(PermissionOnObjectViewMixin, CreateView):
  """Generic view for adding a version into a specific project"""
  model = ProjectVersion
  template_name = "code_doc/project_revision/project_revision_add.html"
  fields = ['version', 'description', 'release_date']
  
  def get_context_data(self, **kwargs):
    """Method used for populating the template context"""
    context = super(ProjectVersionAddView, self).get_context_data(**kwargs)
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])  
    except Project.DoesNotExist:
      raise Http404
    context['project'] = current_project
    context['project_id'] = current_project.id       
    return context

  def get(self, request, project_id, **kwargs):
    """Returning the form"""
    try:
      current_project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    if not self.request.user.is_superuser and not current_project.has_version_add_permissions(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    return super(ProjectVersionAddView, self).get(request, project_id, **kwargs)

  def form_valid(self, form):    
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])
    except Project.DoesNotExist:
      raise Http404
    
    if not self.request.user.is_superuser and not current_project.has_version_add_permissions(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    form.instance.project =current_project 
    return super(ProjectVersionAddView, self).form_valid(form)
  
  def get_success_url(self):
    return self.object.get_absolute_url()  
  


class ProjectVersionDetailsView(View):
  """Details the content of a specific version. Contains all the artifacts"""
  def get(self, request, project_id, version_id):
    
    try:
      project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      raise Http404
    
    try:
      version = project.versions.get(pk=version_id)
    except ProjectVersion.DoesNotExist:
      raise Http404
    
    artifacts = version.artifacts.all()
    return render(
              request, 
              'code_doc/project_revision/project_revision_details.html',
              {'project': project,
               'version': version,
               'artifacts': artifacts})


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


class ProjectVersionArtifactView(View):
  """Adds an artifact.
  deprecated, to be removed"""
  
      
  def get(self, request, project_id, version_number):

    try:
      project_version = ProjectVersion.objects.get(version=version_number)
    except ProjectVersion.DoesNotExist:
      raise Http404

    project = project_version.project

    artifact_list = project_version.artifacts.all()
    return render(
              request, 
              'code_doc/project_artifacts/project_artifact_add.html',
              {'project': project,
               'current_version':project_version,
               'artifacts' : artifact_list})
  
  @method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def post(self, request, project_id, version_number):
    try:
      project_version = ProjectVersion.objects.get(version=version_number)
    except ProjectVersion.DoesNotExist:
      raise Http404

    project = project_version.project
    if request.FILES.has_key('attachment'):
      fileattached = request.FILES['attachment']
      filename = fileattached.name
      m = hashlib.md5()
      
      logger.debug('[fileupload] temporary location %s', settings.USER_UPLOAD_TEMPORARY_STORAGE)
      with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE) as f:
        for chunk in fileattached.chunks():
          f.write(chunk)
          m.update(chunk)
        
        f.seek(0)

        current_artifact, created = Artifact.objects.get_or_create(project_version=project_version, md5hash=m.hexdigest())
        
        logger.debug('[fileupload] artifact %s - digest is %s', "created" if created else "not created", m.hexdigest())
        if created:
          current_artifact.artifactfile.save(filename, File(f), True)
          current_artifact.save()
          assert hashlib.md5(current_artifact.artifactfile.read()).hexdigest() == m.hexdigest()
          
          logger.debug('[fileupload] \tlocation %s', current_artifact.artifactfile.name)
          logger.debug('[fileupload] \turl %s', current_artifact.artifactfile.url)
        logger.debug('[fileupload] object %s', current_artifact)
        
        

    return HttpResponse(m.hexdigest(), status=200)


class ProjectVersionArtifactAddView(CreateView):
  """Generic view for adding a version into a specific project"""
  model = Artifact
  template_name = "code_doc/project_artifacts/project_artifact_add.html"
  fields = ['description', 'artifactfile']
  
  def get_context_data(self, **kwargs):
    """Method used for populating the template context"""
    context = super(ProjectVersionArtifactAddView, self).get_context_data(**kwargs)
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
    return context

  @method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def get(self, request, project_id, version_id, *args, **kwargs):
    """Returning the form"""
    logger.warning('[fileupload] dispatch %s, %s, %s', project_id, version_id, kwargs)
    
    try:
      current_project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    if not self.request.user.is_superuser and not current_project.has_artifact_add_permissions(self.request.user):
      return HttpResponse('Unauthorized', status=401) 
    
    try:
      current_version = current_project.versions.get(pk=version_id)
    except ProjectVersion.DoesNotExist:
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    return super(ProjectVersionArtifactAddView, self).get(request, project_id, version_id, *args, **kwargs)

  
  #@method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def form_valid(self, form):    
    logger.warning('[fileupload] form valid')
    try:
      current_project = Project.objects.get(pk=self.kwargs['project_id'])
    except Project.DoesNotExist:
      logger.warning('[fileupload] formvalid project does not exist')
      raise Http404
    
    if not self.request.user.is_superuser and not current_project.has_artifact_add_permissions(self.request.user):
      return HttpResponse('Unauthorized', status=401) 

    logger.debug('[fileupload] version')
    try:
      current_version = current_project.versions.get(pk=self.kwargs['version_id'])
    except ProjectVersion.DoesNotExist:
      logger.warning('[fileupload] formvalid version does not exist')
      return HttpResponse('Unauthorized', status=401) # we can return 404 but it is better to return the same as unauthorized

    form.instance.project_version =current_version 
    
    try:
      return super(ProjectVersionArtifactAddView, self).form_valid(form)
    except Exception, e:
      logging.error("[fileupload] error during the save %s", e)
    
    return HttpResponse('Conflict %s' % form.instance.md5hash, status=409)
    
    
  def get_success_url(self):
    return self.object.get_absolute_url()  





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



# class FileUploadView(APIView):
#   # works with 
#   # curl -X PUT --data-binary @manage.py http://localhost:8000/code_doc/api/artifact/1/titi.html
#   parser_classes = (FileUploadParser,)
# 
#   def put(self, request, project_id, project_version_id, filename, format=None):
#     import hashlib
#     file_obj = request.FILES['file']
#     # ...
#     # do some staff with uploaded file
#     # ...
#     
#     
#     
#     filecontent = file_obj.read()#self.parse(file_obj)#request.read()#
#     with file('/Users/raffi/tmp/toto.py', 'wb') as f:
#       f.write(filecontent)
# 
#     m = hashlib.md5(filecontent).hexdigest()
# 
#     
#     return HttpResponse("Created file %s with the following content\n<br>MD5: %s<br><br>%s" % (filename, m, filecontent.replace('\r', '<br>')))
#     return Response(status=204)
#   
#   # works with 
#   # curl -X POST --data filename=toto.yoyo --data-urlencode filecontent@manage.py  http://localhost:8000/code_doc/api/artifact/1/ 
#   def post(self, request, project_id, project_version_id, format=None):
#     import hashlib
#     filename = request.DATA['filename']
#     filecontent = request.DATA['filecontent']
#     # ...
#     # do some staff with uploaded file
#     # ...
#     
#     
#     
#     #filecontent = file_obj.read()#self.parse(file_obj)#request.read()#
#     with file('/Users/raffi/tmp/toto.py', 'wb') as f:
#       f.write(filecontent)
# 
#     m = hashlib.md5(filecontent).hexdigest()
# 
#     
#     return HttpResponse("Created file %s with the following content\n<br>MD5: %s<br><br>%s" % (filename, m, filecontent.replace('\r', '<br>')))
#     return Response(status=204)

