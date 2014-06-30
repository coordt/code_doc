from django.db import models

# Create your models here.

class Author(models.Model):
  """An author, may appear in several projects"""
  lastname        = models.CharField(max_length=50)
  firstname       = models.CharField(max_length=50)
  gravatar_email  = models.CharField(max_length=50)
  email           = models.EmailField(max_length=50)
  home_page_url   = models.CharField(max_length=250)

class Project(models.Model):
  """A project, may contain several authors"""
  name            = models.CharField(max_length=50)
  description     = models.CharField(max_length=2500)
  authors         = models.ManyToManyField(Author)
  home_page_url   = models.CharField(max_length=250)
  code_source_url = models.CharField(max_length=250)


class ProjectVersion(models.Model):
  """A version of a project comes with several artifacts"""
  project         = models.ForeignKey(Project)
  version         = models.CharField(max_length=500) # can be a hash
  release_date    = models.DateTimeField('version release date')
  is_public       = models.BooleanField() 


class Artifact(models.Model):
  """An artifact is a downloadable file"""
  project_version = models.ForeignKey(ProjectVersion)
  filename        = models.CharField(max_length=1024)
