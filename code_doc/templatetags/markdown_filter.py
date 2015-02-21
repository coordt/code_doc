from django import template
register = template.Library()


import markdown
#from markdown.extensions.wikilinks import WikiLinkExtension

import logging
# logger for this file
logger = logging.getLogger(__name__)

@register.filter(is_safe=False)
def markd(text):
  if text is None:
    return text
  return markdown.markdown(text, 
                           extensions = ['codehilite', 'toc', 'fenced_code', 'admonition'], 
                           safe_mode=False)

class MkNode(template.Node):
  def __init__(self, nodelist):
    self.nodelist = nodelist
  def render(self, context):
    output = self.nodelist.render(context)
    return markdown.markdown(output, 
                             extensions = ['codehilite', 'toc', 'fenced_code', 'admonition'],
                             safe_mode=False)

@register.tag
def markdown_tag(parser, token):
  nodelist = parser.parse(('endmarkdown_tag',))
  parser.delete_first_token()
  return MkNode(nodelist)

