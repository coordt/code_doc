from django.db import models
import datetime
import os

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.urlresolvers import reverse

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
  description     = models.TextField(max_length=200, blank=True, null=True)
  description_mk  = models.TextField('Description in Markdown format', max_length=200, blank=True, null=True)
  
  def __unicode__(self):
    return "%s" %(self.name)

  def save(self, *args, **kwargs):
    import markdown
    if self.description_mk is None:
      self.description_mk = ''
    self.description = markdown.markdown(self.description_mk)
    super(Topic, self).save() # Call the "real" save() method.

class Project(models.Model):
  """A project, may contain several authors"""
  name            = models.CharField(max_length=50, unique=True)
  description     = models.TextField('hidden', max_length=2500, blank=True, null=True)
  short_description = models.TextField('short description of the project (200 chars)', max_length = 200, blank = True, null = True)
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
  
  
  def save(self, *args, **kwargs):
    if self.description_mk is None:
      self.description_mk = ''
    import markdown
    self.description = markdown.markdown(self.description_mk)
    super(Project, self).save(*args, **kwargs) # Call the "real" save() method.

  

class ProjectVersion(models.Model):
  """A version of a project comes with several artifacts"""
  project         = models.ForeignKey(Project, related_name = "versions")
  version         = models.CharField(max_length=500) # can be a hash
  release_date    = models.DateField('version release date')
  is_public       = models.BooleanField(default=False)
  description     = models.TextField('description of the release', max_length=500) # the description of the content
  description_mk  = models.TextField('Description in Markdown format', max_length=200, blank=True, null=True)

  class Meta:
    unique_together = (("project", "version"), ) 

  def __unicode__(self):
    return "[%s @ %s] [%s]" %(self.project.name, self.version, self.release_date)

  def get_absolute_url(self):
    return reverse('project_version', kwargs={'project_id' : self.project.pk})

  def save(self, *args, **kwargs):
    import markdown
    if self.description_mk is None:
      self.description_mk = ''
    self.description = markdown.markdown(self.description_mk)
    super(ProjectVersion, self).save() # Call the "real" save() method.


def get_artifact_location(instance, filename):
  """An helper function to specify the storage location of an uploaded file"""
  return os.path.join("artifacts", instance.project_version.project.name, instance.project_version.version, filename)
  


class Artifact(models.Model):
  """An artifact is a downloadable file"""
  project_version = models.ForeignKey(ProjectVersion, related_name = "artifacts")
  md5hash         = models.CharField(max_length=1024) # md5 hash 
  description     = models.TextField('description of the artifact', max_length=1024)
  artifactfile    = models.FileField(upload_to=get_artifact_location)

  def __unicode__(self):
    return "%s | %s | %s" %(self.project_version, self.artifactfile.name, self.md5hash)

  class Meta:
    # we allow only one version per project version (we can however have the same file in several versions)
    unique_together = (("project_version", "md5hash"), )
  
  def filename(self):
    return os.path.basename(self.artifactfile.name) 