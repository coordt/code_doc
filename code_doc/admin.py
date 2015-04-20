from django.contrib import admin
import logging
# logger for this file
logger = logging.getLogger(__name__)

# Register your models here.

from code_doc.models import Author, Project, ProjectSeries, Artifact, Copyright, CopyrightHolder, Topic

admin.site.register(Author)
admin.site.register(Artifact)
admin.site.register(Copyright)
admin.site.register(CopyrightHolder)

class ProjectAdmin(admin.ModelAdmin):
  list_display = ('name', 'home_page_url', 'description_mk')
  list_filter  = ['name']

  def get_queryset(self, request):
    """Filters the project to which the current user has access to"""
    qs = super(ProjectAdmin, self).get_queryset(request)
    if request.user.is_superuser:
      return qs
    filtered_qs = qs.filter(administrators__id__contains=request.user.id)
    logger.debug('[admin|project] User %s has the right to edit the following projects %s', request.user, [i.name for i in filtered_qs.all()])
    return filtered_qs


admin.site.register(Project, ProjectAdmin)

class ProjectVersionAdmin(admin.ModelAdmin):
  list_display = ('version', 'release_date', 'is_public', 'description_mk')
  list_filter  = ['version', 'release_date']

admin.site.register(ProjectSeries, ProjectVersionAdmin)


class TopicAdmin(admin.ModelAdmin):
  pass

admin.site.register(Topic, TopicAdmin)
