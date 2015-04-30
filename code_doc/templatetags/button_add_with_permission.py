
from django import template
from code_doc.models import Project
from django.core.urlresolvers import reverse, reverse_lazy

register = template.Library()

import logging
# logger for this file
logger = logging.getLogger(__name__)


@register.inclusion_tag('code_doc/tags/button_add_with_permission_tag.html')
def button_add_series_with_permission(user, project):
  #project = Project.objects.get(pk=project_id)
  logger.debug('[templatetag|button series] User %s ', user)
  return {'permission_ok': project.has_user_project_series_add_permission(user),
          'user': user,
          'next': reverse_lazy('project_revision_add', args=[project.id])}


@register.inclusion_tag('code_doc/tags/button_add_with_permission_tag.html')
def button_add_artifact_with_permission(user, revision):
  project = revision.project
  logger.debug('[templatetag|button artifact] User %s ', user)
  return {'permission_ok': project.has_user_project_artifact_add_permission(user),
          'user': user,
          'text' : 'Add',
          'next' : reverse_lazy('project_artifacts_add', args=[project.id, revision.id])}

@register.inclusion_tag('code_doc/tags/button_add_with_permission_tag.html')
def button_remove_artifact_with_permission(user, revision):
  project = revision.project
  logger.debug('[templatetag|button artifact] User %s ', user)
  return {'permission_ok': project.has_user_project_artifact_add_permission(user),
          'user': user,
          'text' : 'Remove',
          'next' : reverse_lazy('project_artifacts_add', args=[project.id, revision.id])}


@register.inclusion_tag('code_doc/tags/button_edit_with_permission_tag.html')
def button_edit_series_with_permission(user, revision):
  project = revision.project
  logger.debug('[templatetag|button artifact] User %s ', user)
  return {'permission_ok': project.has_user_project_series_add_permission(user),
          'user': user,
          'next' : reverse_lazy('project_revision_edit', args=[project.id, revision.id])}

@register.inclusion_tag('code_doc/tags/button_edit_with_permission_tag.html')
def button_edit_author_with_permission(user, author):
    logger.debug('[templatetag|button artifact] User %s ', user)

    return {'permission_ok': author.has_user_author_edit_permission(user),
            'user': user,
            'next': reverse_lazy('author_edit', args=[author.id])}
