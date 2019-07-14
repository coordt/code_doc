from django import template
from django.core.urlresolvers import reverse_lazy
import logging

register = template.Library()
logger = logging.getLogger(__name__)


@register.inclusion_tag("code_doc/tags/button_add_with_permission_tag.html")
def button_add_series_with_permission(user, project):
    logger.debug("[templatetag|button series] User %s ", user)
    return {
        "permission_ok": project.has_user_project_series_add_permission(user),
        "user": user,
        "next": reverse_lazy("project_series_add", args=[project.id]),
    }


@register.inclusion_tag("code_doc/tags/button_add_with_permission_tag.html")
def button_add_artifact_with_permission(user, series):
    project = series.project
    logger.debug("[templatetag|button artifact] User %s ", user)
    return {
        "permission_ok": series.has_user_series_artifact_add_permission(user),
        "user": user,
        "text": "Add",
        "next": reverse_lazy("project_artifacts_add", args=[project.id, series.id]),
    }


@register.inclusion_tag("code_doc/tags/button_add_with_permission_tag.html")
def button_remove_artifact_with_permission(user, series):
    project = series.project
    logger.debug("[templatetag|button artifact] User %s ", user)
    return {
        "permission_ok": series.has_user_series_artifact_delete_permission(user),
        "user": user,
        "text": "Remove",
        "next": reverse_lazy("project_artifacts_add", args=[project.id, series.id]),
    }


@register.inclusion_tag("code_doc/tags/button_edit_with_permission_tag.html")
def button_edit_series_with_permission(user, series):
    project = series.project
    logger.debug("[templatetag|button series] User %s ", user)
    return {
        "permission_ok": series.has_user_series_edit_permission(user),
        "user": user,
        "next": reverse_lazy("project_series_edit", args=[project.id, series.id]),
    }


@register.inclusion_tag("code_doc/tags/button_edit_with_permission_tag.html")
def button_edit_author_with_permission(user, author):
    logger.debug("[templatetag|button author] User %s editing Author %s", user, author)
    return {
        "permission_ok": author.has_user_author_edit_permission(user),
        "user": user,
        "next": reverse_lazy("author_edit", args=[author.id]),
    }
