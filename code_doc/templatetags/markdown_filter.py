from django import template
register = template.Library()


import markdown

import logging
# logger for this file
logger = logging.getLogger(__name__)

@register.filter(is_safe=True)
def markd(text):
  if text is None:
    return text
  return markdown.markdown(text, extensions = ['codehilite'], safe_mode='escape')

class MkNode(template.Node):
  def __init__(self, nodelist):
    self.nodelist = nodelist
  def render(self, context):
    #logger.debug("toto is also here")
    output = self.nodelist.render(context)
    
    return markdown.markdown(output, extensions = ['codehilite'], safe_mode='escape')

@register.tag
def markdown_tag(parser, token):
  nodelist = parser.parse(('endmarkdown_tag',))
  parser.delete_first_token()
  return MkNode(nodelist)

  
  #if text is None:
  #  return text
  #return markdown.markdown(text, extensions = ['codehilite'], safe_mode='escape')



