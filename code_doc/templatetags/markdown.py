from django import template
import markdown
 
register = template.Library()
 
@register.filter
def markd(text):
  return markdown.markdown(text, safe_mode='escape')