# gravatar.py ###############
# place inside a 'templatetags' directory inside the top level of a
# Django app (not project, must be inside an app)
# at the top of your page template include this:
# {% load gravatar %}
# and to use the url do this:
# <img src="{% gravatar_url 'someone@somewhere.com' %}">
# or
# <img src="{% gravatar_url sometemplatevariable %}">
# just make sure to update the "default" image path below


from django import template
import urllib
import hashlib

register = template.Library()


class GravatarUrlNode(template.Node):

    def __init__(self, email):
        self.email = template.Variable(email)

    def render(self, context):
        try:
            email = self.email.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        default = "retro"
        size = 40

        gravatar_url = "https://www.gravatar.com/avatar/" + \
                       hashlib.md5(email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'d': default, 's': str(size)})

        return gravatar_url


@register.tag
def gravatar_url(parser, token):
    try:
        _, email = token.split_contents()

    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a single argument %r" % (token.contents.split()[0],
                                                      token.contents.split())

    return GravatarUrlNode(email)
