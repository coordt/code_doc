from django.db import models
import datetime

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.

class Author(models.Model):
  """An author, may appear in several projects"""
  lastname        = models.CharField(max_length=50)
  firstname       = models.CharField(max_length=50)
  gravatar_email  = models.CharField(max_length=50)
  email           = models.EmailField(max_length=50, unique=True, db_index=True)
  home_page_url   = models.CharField(max_length=250)
  
  def __unicode__(self):
    return "%s %s ? %s" %(self.firstname, self.lastname, self.email)
  
class CopyrightHolder(models.Model):
  name            = models.CharField(max_length=50)
  year            = models.IntegerField(default=datetime.datetime.now().year)
  def __unicode__(self):
    return "%s (%d)" %(self.name, self.year)

class Copyright(models.Model):
  name            = models.CharField(max_length=50)
  content         = models.TextField(max_length=2500)
  url             = models.CharField(max_length=50)
  
  def __unicode__(self):
    return "%s @ %s" %(self.name, self.url)

class Topic(models.Model):
  name            = models.CharField(max_length=20)
  description     = models.TextField(max_length=200)
  description_mk  = models.TextField(max_length=200)
  
  def __unicode__(self):
    return "%s" %(self.name)

  def save(self):
    import markdown
    self.description = markdown.markdown(self.description_mk)
    super(Topic, self).save() # Call the "real" save() method.

class Project(models.Model):
  """A project, may contain several authors"""
  name            = models.CharField(max_length=50, unique=True)
  description     = models.TextField('hidden', max_length=2500, blank=True, null=True)
  description_mk  = models.TextField('text in Markdown', max_length=2500, blank=True, null=True)
  icon            = models.ImageField(blank=True, null=True, upload_to='project_icons/')
  
  authors         = models.ManyToManyField(Author)
  
  # the administrators of the project
  administrators  = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, null=True)
  
  home_page_url   = models.CharField(max_length=250, null=True, blank=True)
  code_source_url = models.CharField(max_length=250, null=True, blank=True)
  copyright       = models.ForeignKey(Copyright, null=True, blank=True)
  copyright_holder= models.ManyToManyField(CopyrightHolder, null=True, blank=True)

  topics          = models.ManyToManyField(Topic, null=True, blank=True)

  def __unicode__(self):
    return "%s" %(self.name)
  
  
  def save(self):
    import markdown
    self.description = markdown.markdown(self.description_mk)
    super(Project, self).save() # Call the "real" save() method.

  

class ProjectVersion(models.Model):
  """A version of a project comes with several artifacts"""
  project         = models.ForeignKey(Project)
  version         = models.CharField(max_length=500) # can be a hash
  release_date    = models.DateField('version release date')
  is_public       = models.BooleanField(default=False)
  description     = models.TextField('description of the release', max_length=500) # the description of the content

  class Meta:
    unique_together = (("project", "version"), ) 

  def __unicode__(self):
    return "%s - version %s / %s" %(self.project.name, self.version, self.release_date)


class Artifact(models.Model):
  """An artifact is a downloadable file"""
  project_version = models.ForeignKey(ProjectVersion)
  filename        = models.CharField(max_length=1024)
  md5hash         = models.CharField(max_length=1024) # md5 hash 
  description     = models.TextField('description of the artifact', max_length=1024)

  def __unicode__(self):
    return "%s - version %s / %s" %(self.project_version.project.name, self.project_version.version, self.filename)
