from django import template
register = template.Library()


import markdown

 
@register.filter
def markd(text):
  return markdown.markdown(text, safe_mode='escape')