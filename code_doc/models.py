from django.db import models
import datetime

# Create your models here.

class Author(models.Model):
  """An author, may appear in several projects"""
  lastname        = models.CharField(max_length=50)
  firstname       = models.CharField(max_length=50)
  gravatar_email  = models.CharField(max_length=50)
  email           = models.EmailField(max_length=50)
  home_page_url   = models.CharField(max_length=250)
  def __unicode__(self):
    return "%s %s" %(self.firstname, self.lastname)
  
class CopyrightHolder(models.Model):
  name            = models.CharField(max_length=50)
  year            = models.IntegerField(default=datetime.datetime.now().year)
  def __unicode__(self):
    return "%s (%d)" %(self.name, self.year)



class Copyright(models.Model):
  name            = models.CharField(max_length=50)
  content         = models.CharField(max_length=2500)
  url             = models.CharField(max_length=50)
  
  def __unicode__(self):
    return "%s @ %s" %(self.name, self.url)

class Project(models.Model):
  """A project, may contain several authors"""
  name            = models.CharField(max_length=50)
  description     = models.CharField(max_length=2500)
  authors         = models.ManyToManyField(Author)
  home_page_url   = models.CharField(max_length=250, null=True)
  code_source_url = models.CharField(max_length=250, null=True)
  copyright       = models.ForeignKey(Copyright, null=True)
  copyright_holder= models.ManyToManyField(CopyrightHolder, null=True)

  def __unicode__(self):
    return "%s" %(self.name)
  

class ProjectVersion(models.Model):
  """A version of a project comes with several artifacts"""
  project         = models.ForeignKey(Project)
  version         = models.CharField(max_length=500) # can be a hash
  release_date    = models.DateTimeField('version release date')
  is_public       = models.BooleanField(default=False) 


class Artifact(models.Model):
  """An artifact is a downloadable file"""
  project_version = models.ForeignKey(ProjectVersion)
  filename        = models.CharField(max_length=1024)
