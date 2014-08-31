
from django import template
from code_doc.models import Author
register = template.Library()
 

@register.inclusion_tag('code_doc/tags/author_image_tag.html')
def author_image(author_id, size = None):
  author = Author.objects.get(pk=author_id)
  return {'image': None, #author.image,
          'email': author.gravatar_email, 
          'size' : size}