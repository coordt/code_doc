from django.shortcuts import render

# Create your views here.

from django.http import Http404
from django.http import HttpResponse
from django.template import RequestContext, loader

from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.views import APIView

from code_doc.models import Project, Author, Topic
#from code_doc.serializers import ProjectSerializer





def index(request):
  projects_list = Project.objects.order_by('name')
  topics_list = Topic.objects.order_by('name')
  return render(request, 'code_doc/index.html', {'projects_list': projects_list, 'topics_list': topics_list})
  
  
def detail_project(request, project_id):
  try:
    project = Project.objects.get(pk=project_id)
  except Project.DoesNotExist:
    raise Http404
  
  author_list = project.authors.all()
  topic_list  = project.topics.all()
  return render(
            request, 
            'code_doc/project_details.html', 
            {'project': project, 'authors': author_list, 'topics': topic_list})

def detail_author(request, author_id):
  try:
    author = Author.objects.get(pk=author_id)
  except Author.DoesNotExist:
    raise Http404
  
  project_list = Project.objects.filter(authors=author)
  coauthor_list= Author.objects.filter(project__in=project_list).distinct().exclude(pk=author_id)
  #if author in coauthor_list:
  #  coauthor_list.remove(author)
  return render(request, 'code_doc/author_details.html', {'project_list': project_list, 'author': author, 'coauthor_list': coauthor_list})



class FileUploadView(APIView):
  # works with 
  # curl -X PUT --data-binary @manage.py http://localhost:8000/code_doc/api/artifact/1/titi.html
  parser_classes = (FileUploadParser,)

  def put(self, request, project_version_id, filename, format=None):
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
  def post(self, request, project_version_id, format=None):
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