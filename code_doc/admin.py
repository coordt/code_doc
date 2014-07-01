from django.contrib import admin

# Register your models here.

from code_doc.models import Author, Project, ProjectVersion, Artifact, Copyright, CopyrightHolder

admin.site.register(Author)
admin.site.register(ProjectVersion)
admin.site.register(Artifact)
admin.site.register(Copyright)
admin.site.register(CopyrightHolder)

class ProjectAdmin(admin.ModelAdmin):
  list_display = ('name', 'home_page_url', 'description')
  list_filter = ['name']
  
admin.site.register(Project, ProjectAdmin)

