
from django import template
from code_doc.models import Author

import hashlib

register = template.Library()

@register.inclusion_tag('code_doc/tags/author_image_tag.html')
def author_image(author_id, size = None):
    author = Author.objects.get(pk=author_id)
    return {'uploaded_image': None, #author.image,
            'gravatar_email': None if author.gravatar_email == "" else author.gravatar_email,
            'author_initial': author.firstname[0],
            'background_color': _hash_string_to_color_hex(author.firstname + author.lastname, 200),
            'size' : size}


def _hash_string_to_color_hex(str_author, brightness_limit):
    hashed = hashlib.md5(str_author.encode('utf-8')).hexdigest()[:6]
    r = int(hashed[0:2], 16)
    g = int(hashed[2:4], 16)
    b = int(hashed[4:6], 16)
  
    r = min(r, brightness_limit)
    g = min(g, brightness_limit)
    b = min(b, brightness_limit)
  
    result = '#%02x%02x%02x' % (r, g, b)
    return result
