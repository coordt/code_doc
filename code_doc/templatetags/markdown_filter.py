from django import template
register = template.Library()


import markdown

 
@register.filter
def markd(text):
  if text is None:
    return text
  return markdown.markdown(text, extensions = ['codehilite'], safe_mode='escape')