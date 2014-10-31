
from django import template
from code_doc.models import Project
register = template.Library()
 

@register.inclusion_tag('code_doc/tags/project_image_tag.html')
def project_image(project_id, size = None):
  project = Project.objects.get(pk=project_id)
  
  im = project.icon
  if(im.width > im.height):
    size_x = size
    size_y = im.height * size_x / im.width
  else:
    size_y = size
    size_x = im.width * size_y / im.height
  
  return {'image': project.icon,
          'size_x' : size_x,
          'size_y' : size_y}