from django import template
from ..models.authors import Author

import hashlib

register = template.Library()


@register.inclusion_tag("code_doc/tags/author_image_tag.html")
def author_image(author_id, size=None):
    author = Author.objects.get(pk=author_id)
    return {
        "uploaded_image": author.image if author.image is not None else None,
        "gravatar_email": author.gravatar_email
        if author.gravatar_email != ""
        else None,
        "author_initial": (
            author.firstname[0] if author.firstname != "" else author.email[0]
        ).upper(),
        "background_color": _hash_string_to_color_hex(
            author.firstname + author.lastname, 200
        ),
        "size": size if size is not None else 64,
    }


def _hash_string_to_color_hex(str_author, brightness_limit):
    hashed = hashlib.md5(str_author.encode("utf-8")).hexdigest()[:6]
    r = int(hashed[0:2], 16)
    g = int(hashed[2:4], 16)
    b = int(hashed[4:6], 16)

    r = min(r, brightness_limit)
    g = min(g, brightness_limit)
    b = min(b, brightness_limit)

    result = "#%02x%02x%02x" % (r, g, b)
    return result
