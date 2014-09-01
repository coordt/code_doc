
from django import template
from code_doc.models import Project
register = template.Library()
 

@register.inclusion_tag('code_doc/tags/project_image_tag.html')
def project_image(project_id, size = None):
  project = Project.objects.get(pk=project_id)
  return {'image': project.icon,
          'size' : size}