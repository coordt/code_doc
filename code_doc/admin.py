from django.contrib import admin

# Register your models here.

from code_doc.models import Author, Project, ProjectVersion, Artifact, Copyright, CopyrightHolder, Topic

admin.site.register(Author)
admin.site.register(Artifact)
admin.site.register(Copyright)
admin.site.register(CopyrightHolder)

class ProjectAdmin(admin.ModelAdmin):
  list_display = ('name', 'home_page_url', 'description_mk')
  list_filter  = ['name']
  exclude      = ('description',)
  
admin.site.register(Project, ProjectAdmin)

class ProjectVersionAdmin(admin.ModelAdmin):
  list_display = ('version', 'release_date', 'is_public', 'description_mk')
  list_filter  = ['version', 'release_date']
  exclude      = ('description',)
  
admin.site.register(ProjectVersion, ProjectVersionAdmin)


class TopicAdmin(admin.ModelAdmin):
  exclude      = ('description',)

admin.site.register(Topic, TopicAdmin)