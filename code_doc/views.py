from django.shortcuts import render

# Create your views here.

from django.http import Http404
from django.http import HttpResponse
from django.template import RequestContext, loader

from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from code_doc.models import Project
#from code_doc.serializers import ProjectSerializer



def index(request):
  projects_list = Project.objects.order_by('name')
  return render(request, 'code_doc/index.html', {'projects_list': projects_list})
  
  
def detail_project(request, project_id):
  try:
    project = User.objects.get(pk=project_id)
  except User.DoesNotExist:
    raise Http404
  return render(request, 'code_doc/project_details.html', {'project': project})