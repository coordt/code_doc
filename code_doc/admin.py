from django.contrib import admin

# Register your models here.

from code_doc.models import Author, Project, ProjectVersion, Artifact

admin.site.register(Author)
admin.site.register(Project)
admin.site.register(ProjectVersion)
admin.site.register(Artifact)

