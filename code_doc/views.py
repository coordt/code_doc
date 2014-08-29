from django.shortcuts import render

# Create your views here.

from django.http import Http404
from django.http import HttpResponse
from django.template import RequestContext, loader

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from django.core.files import File


from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.views import APIView


from django.core.urlresolvers import reverse, reverse_lazy

import hashlib
import tempfile
import logging
# logger for this file
logger = logging.getLogger(__name__)

from django.conf import settings


from code_doc.models import Project, Author, Topic, ProjectVersion, Artifact
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





class ProjectView(View):
  
  def get(self, request, project_id):
    try:
      project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      raise Http404
    
    author_list = project.authors.all()
    topic_list  = project.topics.all()
    return render(
              request, 
              'code_doc/project_details.html', 
              {'project': project, 
               'authors': author_list, 
               'topics': topic_list})
  
  @login_required(login_url='/accounts/login/')
  def post(self):
    pass
  
class ProjectVersionView(View):
  def get(self, request, project_id):
    try:
      project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      raise Http404
    
    versions_list = project.versions.all()
    return render(
              request, 
              'code_doc/project_details.html', 
              {'project': project,
               'versions': versions_list})
  
  @login_required(login_url='/accounts/login/')
  def post(self):
    pass


class ProjectVersionArtifactView(View):
  
  def get_project_version(self, project_id, version_number):
    try:
      project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
      raise Http404

    versions_list = project.versions.all()
    try:
      project_version = project.versions.get(version=version_number)
    except ProjectVersion.DoesNotExist:
      raise Http404
    
    return project, versions_list, project_version
      
  def get(self, request, project_id, version_number):

    project, versions_list, project_version = self.get_project_version(project_id, version_number)
    artifact_list = project_version.artifacts.all()
    return render(
              request, 
              'code_doc/project_details.html', 
              {'project': project,
               'versions': versions_list,
               'current_version':project_version,
               'artifacts' : artifact_list})
  
  @method_decorator(lambda x: login_required(x, login_url=reverse_lazy('login')))
  def post(self, request, project_id, version_number):
    project, versions_list, project_version = self.get_project_version(project_id, version_number)
    
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
        current_artifact.artifactfile.save(filename, File(f), True)
        
        logger.debug('[fileupload] artifact %s - digest is %s', "created" if created else "not created", m.hexdigest())
        if created:
          logger.debug('[fileupload] \tlocation %s', current_artifact.artifactfile.name)
          logger.debug('[fileupload] \turl %s', current_artifact.artifactfile.url)
        logger.debug('[fileupload] object %s', current_artifact)
        
        current_artifact.save()
        
        assert hashlib.md5(current_artifact.artifactfile.read()).hexdigest() == m.hexdigest()

    return HttpResponse(m.hexdigest(), status=200)

class TopicView(View):
  
  def get(self, request, topic_id):
    try:
      topic = Topic.objects.get(pk=topic_id)
    except Project.DoesNotExist:
      raise Http404
    
    #author_list = project.authors.all()
    #topic_list  = project.topics.all()
    return render(
              request, 
              'code_doc/topics.html', 
              {'topic': topic})
  
  @login_required(login_url=reverse_lazy('login'))
  def post(self):
    pass



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



class FileUploadView(APIView):
  # works with 
  # curl -X PUT --data-binary @manage.py http://localhost:8000/code_doc/api/artifact/1/titi.html
  parser_classes = (FileUploadParser,)

  def put(self, request, project_id, project_version_id, filename, format=None):
    import hashlib
    file_obj = request.FILES['file']
    # ...
    # do some staff with uploaded file
    # ...
    
    
    
    filecontent = file_obj.read()#self.parse(file_obj)#request.read()#
    with file('/Users/raffi/tmp/toto.py', 'wb') as f:
      f.write(filecontent)

    m = hashlib.md5(filecontent).hexdigest()

    
    return HttpResponse("Created file %s with the following content\n<br>MD5: %s<br><br>%s" % (filename, m, filecontent.replace('\r', '<br>')))
    return Response(status=204)
  
  # works with 
  # curl -X POST --data filename=toto.yoyo --data-urlencode filecontent@manage.py  http://localhost:8000/code_doc/api/artifact/1/ 
  def post(self, request, project_id, project_version_id, format=None):
    import hashlib
    filename = request.DATA['filename']
    filecontent = request.DATA['filecontent']
    # ...
    # do some staff with uploaded file
    # ...
    
    
    
    #filecontent = file_obj.read()#self.parse(file_obj)#request.read()#
    with file('/Users/raffi/tmp/toto.py', 'wb') as f:
      f.write(filecontent)

    m = hashlib.md5(filecontent).hexdigest()

    
    return HttpResponse("Created file %s with the following content\n<br>MD5: %s<br><br>%s" % (filename, m, filecontent.replace('\r', '<br>')))
    return Response(status=204)

